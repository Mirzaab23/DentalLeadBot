"""Extract public contact addresses from HTML without guessing mailboxes."""
import re
from email_validator import EmailNotValidError, validate_email
from bs4 import BeautifulSoup
from urllib.parse import unquote

PATTERN = re.compile(r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+", re.I)
PLACEHOLDERS = {'example.com', 'example.org', 'example.net', 'test.com', 'domain.com'}

def extract_emails(html):
    soup = BeautifulSoup(html, 'lxml')
    parts = [soup.get_text(' ', strip=True)]
    parts.extend(unquote(a.get('href', '')[7:].split('?')[0]) for a in soup.select('a[href^="mailto:"]'))
    parts.extend(s.get_text(' ', strip=True) for s in soup.select('script[type="application/ld+json"]'))
    result = set()
    for text in parts:
        text = re.sub(r'\s*(?:\[at\]|\(at\))\s*', '@', text, flags=re.I)
        text = re.sub(r'\s*(?:\[dot\]|\(dot\))\s*', '.', text, flags=re.I)
        for value in PATTERN.findall(text):
            try:
                email = validate_email(value, check_deliverability=False).normalized.lower()
                if email.rsplit('@', 1)[1] not in PLACEHOLDERS and not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    result.add(email)
            except EmailNotValidError:
                continue
    return sorted(result)
