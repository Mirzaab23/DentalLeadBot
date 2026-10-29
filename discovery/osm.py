"""Discover businesses in a US city using OpenStreetMap public data."""
import time
import re
import httpx

HEADERS = {'User-Agent': 'ProspectLab/0.1 (local research tool; contact administrator)'}

KNOWN_TAGS = {
    'dentist': ('amenity','dentist'), 'dentists': ('amenity','dentist'),
    'coffee shop': ('amenity','cafe'), 'coffee shops': ('amenity','cafe'),
    'cafe': ('amenity','cafe'), 'cafes': ('amenity','cafe'),
    'restaurant': ('amenity','restaurant'), 'restaurants': ('amenity','restaurant'),
    'pharmacy': ('amenity','pharmacy'), 'pharmacies': ('amenity','pharmacy'),
    'hotel': ('tourism','hotel'), 'hotels': ('tourism','hotel'),
    'lawyer': ('office','lawyer'), 'lawyers': ('office','lawyer'),
    'real estate agent': ('office','estate_agent'), 'real estate agents': ('office','estate_agent'),
    'hair salon': ('shop','hairdresser'), 'hair salons': ('shop','hairdresser'),
}

def discover(niche, city, state, limit):
    keyword=niche.strip().lower()
    if not keyword: raise ValueError('Business keyword is required')
    with httpx.Client(timeout=45, headers=HEADERS, follow_redirects=False) as client:
        r = client.get('https://nominatim.openstreetmap.org/search', params={'city': city, 'state': state, 'country': 'United States', 'format': 'jsonv2', 'limit': 1})
        r.raise_for_status()
        places = r.json()
        if not places:
            raise ValueError('Location not found by OpenStreetMap')
        s, n, w, e = map(float, places[0]['boundingbox'])
        if not (-90 <= s <= n <= 90 and -180 <= w <= e <= 180):
            raise ValueError('Invalid location bounds')
        tag=KNOWN_TAGS.get(keyword)
        if tag:
            key,value=tag
            selector=f'["{key}"="{value}"]'
        else:
            safe=re.escape(keyword).replace('"',r'\"')
            selector=f'["name"~"{safe}",i]'
        query=f'[out:json][timeout:60];nwr{selector}({s},{w},{n},{e});out center tags;'
        try:
            response = client.post('https://overpass-api.de/api/interpreter', data={'data': query}, timeout=12)
        except httpx.HTTPError:
            response = None
        if response is None or response.is_error or not response.json().get('elements'):
            # Nominatim provides a smaller, best-effort fallback when Overpass is down or empty.
            time.sleep(1)
            search_term=tag[1].replace('_',' ') if tag else keyword
            fallback = client.get('https://nominatim.openstreetmap.org/search', params={'q': f'{search_term} {city} {state} United States', 'format': 'jsonv2', 'addressdetails': 1, 'extratags': 1, 'limit': min(max(limit*5,20),40)})
            fallback.raise_for_status()
            elements = []
            for place in fallback.json():
                if not place.get('name') or (place.get('address') or {}).get('country_code','us').lower() != 'us' or (tag and place.get('type') != tag[1]):
                    continue
                tags = dict(place.get('extratags') or {}); address = place.get('address') or {}
                tags.update({'name': place['name'], 'addr:housenumber': address.get('house_number', ''), 'addr:street': address.get('road', ''), 'addr:city': address.get('city', city), 'addr:state': state, '_category':place.get('type',keyword)})
                elements.append({'type': place['osm_type'], 'id': place['osm_id'], 'tags': tags})
        else:
            elements = response.json().get('elements', [])
        result = []
        for item in elements:
            tags = item.get('tags', {})
            name = tags.get('name')
            if not name:
                continue
            number = tags.get('addr:housenumber', '')
            street = tags.get('addr:street', '')
            result.append({'name': name, 'niche': niche, 'category': tags.get('_category') or (tag[1] if tag else keyword), 'address': ' '.join(x for x in (number, street) if x), 'city': tags.get('addr:city', city), 'state': tags.get('addr:state', state), 'phone': tags.get('contact:phone', tags.get('phone', '')), 'website': tags.get('contact:website', tags.get('website', '')), 'source': 'OpenStreetMap', 'source_url': f"https://www.openstreetmap.org/{item['type']}/{item['id']}"})
            if len(result) >= limit:
                break
        return result


