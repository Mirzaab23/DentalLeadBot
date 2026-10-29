"""Bounded, robots-aware public website crawler."""
import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

AGENT = 'DentalLeadBot/0.1'
PRIORITY = ('contact', 'about', 'appointment', 'location', 'team')


def public_url(value):
    if not value:
        return None
    if '://' not in value:
        value = 'https://' + value
    parsed = urlsplit(value)
    host = parsed.hostname
    if parsed.scheme not in ('http', 'https') or not host or parsed.username or parsed.password:
        return None
    if host.lower() in ('localhost', 'localhost.localdomain') or host.lower().endswith('.local'):
        return None
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == 'https' else 80))
        if not addresses or any(not ipaddress.ip_address(info[4][0]).is_global for info in addresses):
            return None
    except (OSError, ValueError):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or '/', parsed.query, ''))


def crawl(website, max_pages=5, timeout=20):
    start = public_url(website)
    if not start:
        return []
    root = urlsplit(start)
    parser = RobotFileParser()
    robots_url = f'{root.scheme}://{root.netloc}/robots.txt'
    pages = []
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False, headers={'User-Agent': AGENT}) as client:
        try:
            robots = client.get(robots_url)
            if robots.status_code == 200:
                parser.parse(robots.text.splitlines())
            elif robots.status_code in (401, 403):
                return []
            else:
                parser.parse([])
        except httpx.HTTPError:
            return []
        queue = [start]
        seen = set()
        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if urlsplit(url).hostname != root.hostname or not public_url(url) or not parser.can_fetch(AGENT, url):
                continue
            try:
                response = client.get(url)
            except httpx.HTTPError:
                continue
            if response.status_code != 200 or 'text/html' not in response.headers.get('content-type', '').lower():
                continue
            if len(response.content) > 2_000_000:
                continue
            pages.append((url, response.text, response.status_code))
            soup = BeautifulSoup(response.text, 'lxml')
            links = []
            for tag in soup.select('a[href]'):
                link = urljoin(url, tag['href'])
                target = urlsplit(link)
                if target.hostname == root.hostname and target.scheme in ('http', 'https'):
                    clean = urlunsplit((target.scheme, target.netloc, target.path or '/', '', ''))
                    if clean not in seen:
                        links.append(clean)
            links.sort(key=lambda link: (not any(term in link.lower() for term in PRIORITY), link))
            queue.extend(link for link in links if link not in queue)
            time.sleep(0.3)
    return pages
