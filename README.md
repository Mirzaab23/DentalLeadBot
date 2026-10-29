# ProspectLab (DentalLeadBot repository)

A local Python application for discovering US businesses, enriching public business contact information, and managing leads. It uses SQLite, SQLAlchemy, HTTPX, Playwright and Streamlit. Development and data remain on the local computer; no paid API is required.

## Current development status

This is an incomplete discovery-only development build. OpenStreetMap search can return dental listings and the local dashboard can display and export them. When Overpass is unavailable, Nominatim fallback returns at most 40 results and may return fewer. OpenStreetMap data is contributed by volunteers and may be incomplete; see https://www.openstreetmap.org/copyright.

Yelp, full filtering, robust interrupted-worker recovery, and the full acceptance tests are not yet implemented. Website enrichment is implemented for records with a usable official website URL. Search uses the entered keyword across sources; OpenStreetMap maps common niches to categories and uses a text search for other keywords. Stop requests take effect between records, not while a remote request is in flight.

Run `.\setup.ps1`, then `.\start.ps1`, and open http://localhost:8501. Or use `.\.venv\Scripts\python.exe main.py --city Houston --state TX --limit 3`. The dashboard starts workers in the background.

## Enrichment update

Listings with an official website are now crawled for up to five same-domain pages when robots.txt allows it. Published email addresses and social profile links are saved with page source URLs. DNS MX checks are recorded as domain evidence, not mailbox delivery claims. The dashboard displays those fields. OpenStreetMap listings frequently omit websites, so contact coverage depends on the source data. The Houston 20-result test discovered 14 listings, with only 3 websites across all 17 stored records and no published email found in that run.


## Google Maps and Yelp

Google Maps is now the default source. Its public, unauthenticated results may display a limited view; the scraper records the listings it can actually access and does not claim to reach the requested maximum when fewer are visible. Each accessible place page is inspected for address, phone and official website, then the website crawler extracts published emails and social profiles. A one-listing live Houston job discovered one practice, visited five website pages and saved two published email records. Yelp is selectable but its public search page returned empty content in the current environment, so that source fails with a clear error instead of fabricating results.

## Lead workspace

The dashboard now has Overview, New search, Jobs, Lead database and Exports views. Lead filters cover text, city, state, source, email, website, Instagram, Facebook and LinkedIn. Exports use the active filters and support CSV and Excel. Jobs show counts and progress, plus a notice when a public source provides fewer listings than requested. Completed business checkpoints are stored separately so a resumed job can continue processing unfinished records.

## All-source search

The default search tries Google Maps, OpenStreetMap and Yelp for the same query. Accessible listings are combined, matching businesses are merged when they share a name and city plus a matching phone or address, and the requested lead cap applies to the combined job. A blocked source is reported in the job error field while other sources continue. Search results still depend on the public pages each platform exposes.

## Prospecting searches

Prospecting now has separate Find people, Find companies and Directory search pages. Apollo people search accepts job titles, seniority, person location, industry, employer domain and provider email-status filters. It returns only the fields Apollo exposes in search; email reveal requires a separate credit-consuming enrichment action and is not represented as verified here. Apollo company search requires a one-credit acknowledgement before each results page. An eligible Apollo account and API key are needed for live use.

Directory search accepts a Yelp /search or Google Maps /maps/search HTTPS URL to select that public directory, then searches it using the keyword, city and state entered in the form. Unsupported URLs, including LinkedIn search pages, are rejected with a clear error. Public directory access may be limited by the source.

## Local people and companies

Companies discovered from Google Maps, OpenStreetMap and accessible Yelp pages are stored locally. Website crawling adds named people only from explicit structured Person data, preserving the source page. A company email or office phone is never assigned to a person without a source that makes that association. The People page searches the local person table by name, title, location and linked company. Apollo search results can add explicitly named people to the local table when an eligible account is connected; hidden identities and unreturned email addresses are not invented. Email status distinguishes published but unverified from unavailable and provider-verified fields. On the existing local data, a website revisit found seven named people from four stored websites.


## General business search

ProspectLab supports arbitrary business keywords. The dashboard has no dental default, and the CLI requires `--niche`. Google Maps and Yelp use the keyword in their public searches. OpenStreetMap maps common niches to standard tags (for example, coffee shops to `amenity=cafe`, lawyers to `office=lawyer`) and falls back to a name query for other keywords. The Companies view can filter by keyword. Older dental data remains in the local database and can be separated with that filter.

A live smoke test with `--niche "coffee shops" --city Houston --state TX --limit 3 --source OpenStreetMap` completed and stored three café listings. The source supplied one website, which returned no usable pages; no email was fabricated. Public-source coverage depends on available listing fields and site access.

## International locations and platform URLs

Directory search accepts a city, optional region and required country. A recognized Yelp or Google Maps home/search URL selects that platform, then the entered keyword and location build the actual search. For example, `https://www.yelp.com/` is accepted as a Yelp source selector. Apollo company search is disabled until a key is connected, so an unconnected user is not asked to approve spending a credit.

A live `coffee shops` search in Lahore, Punjab, Pakistan via Google Maps completed with three real companies, including public phone numbers and websites. OpenStreetMap returned no matching café records for that query; source coverage varies by region.
