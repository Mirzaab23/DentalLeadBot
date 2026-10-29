"""Public Yelp search adapter with explicit challenge detection."""
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from playwright.sync_api import sync_playwright


def discover(niche, city, state, limit):
    results = []
    seen = set()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale='en-US')
        try:
            for offset in range(0, limit, 10):
                url = f'https://www.yelp.com/search?find_desc={quote(niche)}&find_loc={quote(city + ", " + state)}&start={offset}'
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(1500)
                if not page.locator('body').inner_text().strip():
                    raise RuntimeError('Yelp returned an empty or blocked public search page')
                links = page.locator('a[href*="/biz/"]')
                found = 0
                for index in range(links.count()):
                    anchor = links.nth(index)
                    name = anchor.inner_text().strip()
                    href = anchor.get_attribute('href') or ''
                    parsed = urlsplit(urljoin('https://www.yelp.com', href))
                    listing = urlunsplit(('https', 'www.yelp.com', parsed.path.rstrip('/'), '', ''))
                    if not name or not parsed.path.startswith('/biz/') or listing in seen:
                        continue
                    seen.add(listing); found += 1
                    results.append(dict(name=name, niche=niche, category='', address='', city=city, state=state, phone='', website='', source='Yelp', source_url=listing))
                    if len(results) >= limit: return results
                if not found: break
            if not results:
                raise RuntimeError('No accessible Yelp business listings; source may be blocked or its layout changed')
        finally:
            browser.close()
    return results
