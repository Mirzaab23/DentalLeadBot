"""Public Google Maps listings; stop when Maps presents a limited view."""
from urllib.parse import quote
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout


def discover(niche, city, state, limit, search_url=''):
    records = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale='en-US')
        try:
            base='https://www.google.com/maps/search/'
            page.goto(base + quote(f'{niche} in {city} {state}'), wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3500)
            if 'consent' in page.url or 'captcha' in page.url.lower():
                raise RuntimeError('Google Maps requested consent or a challenge')
            links = page.locator('a[href*="/maps/place/"]')
            candidates = []
            heading = page.locator('h1')
            if heading.count() and page.locator('[data-item-id="address"]').count():
                candidates.append((heading.first.inner_text().strip(), page.url))
            for index in range(min(links.count(), limit)):
                link = links.nth(index)
                name, url = link.get_attribute('aria-label'), link.get_attribute('href')
                if name and url and (name, url) not in candidates:
                    candidates.append((name, url))
            if not candidates:
                raise RuntimeError('No public Google Maps listings were available')
            for name, url in candidates:
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(1200)
                    def item(selector, attribute='aria-label'):
                        found = page.locator(selector)
                        return found.first.get_attribute(attribute) or '' if found.count() else ''
                    address = item('[data-item-id="address"]')
                    phone = item('[data-item-id^="phone:"]')
                    website = item('a[data-item-id="authority"]', 'href')
                    rating_text = item('[role="img"][aria-label*="star"]')
                    try: rating = float(rating_text.split()[0])
                    except (ValueError, IndexError): rating = None
                    records.append(dict(name=name, niche=niche, category='', address=address.removeprefix('Address: '), city=city, state=state, phone=phone.removeprefix('Phone: '), website=website, source='Google Maps', source_url=url, rating=rating))
                except BrowserTimeout:
                    continue
        finally:
            browser.close()
    return records
