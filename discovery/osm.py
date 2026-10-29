"""Discover US dental practices from OpenStreetMap Nominatim and Overpass."""
import time
import httpx

HEADERS = {'User-Agent': 'DentalLeadBot/0.1 (local research tool; contact administrator)'}

def discover(niche, city, state, limit):
    with httpx.Client(timeout=45, headers=HEADERS, follow_redirects=False) as client:
        r = client.get('https://nominatim.openstreetmap.org/search', params={'city': city, 'state': state, 'country': 'United States', 'format': 'jsonv2', 'limit': 1})
        r.raise_for_status()
        places = r.json()
        if not places:
            raise ValueError('Location not found by OpenStreetMap')
        s, n, w, e = map(float, places[0]['boundingbox'])
        if not (-90 <= s <= n <= 90 and -180 <= w <= e <= 180):
            raise ValueError('Invalid location bounds')
        query = f'[out:json][timeout:60];(nwr["amenity"="dentist"]({s},{w},{n},{e});nwr["healthcare"="dentist"]({s},{w},{n},{e}););out center tags;'
        try:
            response = client.post('https://overpass-api.de/api/interpreter', data={'data': query}, timeout=12)
        except httpx.HTTPError:
            response = None
        if response is None or response.is_error:
            # Nominatim provides a smaller, best-effort fallback when Overpass is down.
            time.sleep(1)
            fallback = client.get('https://nominatim.openstreetmap.org/search', params={'q': f'dentist {city} {state} United States', 'format': 'jsonv2', 'addressdetails': 1, 'extratags': 1, 'limit': min(limit, 40)})
            fallback.raise_for_status()
            elements = []
            for place in fallback.json():
                if place.get('type') != 'dentist' or not place.get('name'):
                    continue
                tags = dict(place.get('extratags') or {}); address = place.get('address') or {}
                tags.update({'name': place['name'], 'addr:housenumber': address.get('house_number', ''), 'addr:street': address.get('road', ''), 'addr:city': address.get('city', city), 'addr:state': state})
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
            result.append({'name': name, 'niche': niche, 'category': tags.get('healthcare:speciality', 'dentist'), 'address': ' '.join(x for x in (number, street) if x), 'city': tags.get('addr:city', city), 'state': tags.get('addr:state', state), 'phone': tags.get('contact:phone', tags.get('phone', '')), 'website': tags.get('contact:website', tags.get('website', '')), 'source': 'OpenStreetMap', 'source_url': f"https://www.openstreetmap.org/{item['type']}/{item['id']}"})
            if len(result) >= limit:
                break
        return result


