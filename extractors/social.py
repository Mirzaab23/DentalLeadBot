"""Extract actual social profiles while excluding share links."""
from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup

HOSTS = {'facebook.com': 'facebook', 'instagram.com': 'instagram', 'linkedin.com': 'linkedin', 'tiktok.com': 'tiktok', 'youtube.com': 'youtube', 'x.com': 'x', 'twitter.com': 'x', 'pinterest.com': 'pinterest'}

def extract_social(html):
    soup = BeautifulSoup(html, 'lxml')
    found = set()
    for a in soup.select('a[href]'):
        url = a['href'].strip()
        p = urlsplit(url)
        host = (p.hostname or '').lower().removeprefix('www.')
        platform = HOSTS.get(host)
        path = p.path.rstrip('/')
        if p.scheme not in ('https', 'http') or not platform or not path or any(x in path.lower().split('/') for x in ('share', 'sharer', 'intent', 'login', 'signup')):
            continue
        found.add((platform, urlunsplit(('https', host, path, '', ''))))
    return sorted(found)
