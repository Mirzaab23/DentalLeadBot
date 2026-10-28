# DentalLeadBot

A local Python application for discovering US dental businesses, enriching public business contact information, and managing leads. It uses SQLite, SQLAlchemy, HTTPX, Playwright and Streamlit. Development and data remain on the local computer; no paid API is required.

## Current development status

This is an incomplete discovery-only development build. OpenStreetMap search can return dental listings and the local dashboard can display and export them. When Overpass is unavailable, Nominatim fallback returns at most 40 results and may return fewer. OpenStreetMap data is contributed by volunteers and may be incomplete; see https://www.openstreetmap.org/copyright.

Website crawling, email and social enrichment, Yelp, full filtering, robust interrupted-worker recovery, and the full acceptance tests are not yet implemented. Search currently always requests dentist listings even if a different niche is entered. Stop requests take effect between records, not while a remote request is in flight.

Run `.\setup.ps1`, then `.\start.ps1`, and open http://localhost:8501. Or use `.\.venv\Scripts\python.exe main.py --city Houston --state TX --limit 3`. The dashboard starts workers in the background.
