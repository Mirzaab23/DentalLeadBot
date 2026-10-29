# DentalLeadBot

A local Python application for discovering US dental businesses, enriching public business contact information, and managing leads. It uses SQLite, SQLAlchemy, HTTPX, Playwright and Streamlit. Development and data remain on the local computer; no paid API is required.

## Current development status

This is an incomplete discovery-only development build. OpenStreetMap search can return dental listings and the local dashboard can display and export them. When Overpass is unavailable, Nominatim fallback returns at most 40 results and may return fewer. OpenStreetMap data is contributed by volunteers and may be incomplete; see https://www.openstreetmap.org/copyright.

Yelp, full filtering, robust interrupted-worker recovery, and the full acceptance tests are not yet implemented. Website enrichment is implemented for records with a usable official website URL. Search currently always requests dentist listings even if a different niche is entered. Stop requests take effect between records, not while a remote request is in flight.

Run `.\setup.ps1`, then `.\start.ps1`, and open http://localhost:8501. Or use `.\.venv\Scripts\python.exe main.py --city Houston --state TX --limit 3`. The dashboard starts workers in the background.

## Enrichment update

Listings with an official website are now crawled for up to five same-domain pages when robots.txt allows it. Published email addresses and social profile links are saved with page source URLs. DNS MX checks are recorded as domain evidence, not mailbox delivery claims. The dashboard displays those fields. OpenStreetMap listings frequently omit websites, so contact coverage depends on the source data. The Houston 20-result test discovered 14 listings, with only 3 websites across all 17 stored records and no published email found in that run.


## Google Maps and Yelp

Google Maps is now the default source. Its public, unauthenticated results may display a limited view; the scraper records the listings it can actually access and does not claim to reach the requested maximum when fewer are visible. Each accessible place page is inspected for address, phone and official website, then the website crawler extracts published emails and social profiles. A one-listing live Houston job discovered one practice, visited five website pages and saved two published email records. Yelp is selectable but its public search page returned empty content in the current environment, so that source fails with a clear error instead of fabricating results.

## Lead workspace

The dashboard now has Overview, New search, Jobs, Lead database and Exports views. Lead filters cover text, city, state, source, email, website, Instagram, Facebook and LinkedIn. Exports use the active filters and support CSV and Excel. Jobs show counts and progress, plus a notice when a public source provides fewer listings than requested. Completed business checkpoints are stored separately so a resumed job can continue processing unfinished records.
