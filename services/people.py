"""Apollo role search. Search results do not imply an email is available."""
import httpx

def search_people(api_key, domain, titles):
    if not api_key.strip():
        raise ValueError('Connect an Apollo API key first.')
    if not domain.strip() or not titles:
        raise ValueError('Company domain and target roles are required.')
    with httpx.Client(timeout=30) as client:
        response = client.post('https://api.apollo.io/api/v1/mixed_people/api_search', headers={'x-api-key': api_key, 'Content-Type':'application/json'}, json={'q_organization_domains_list':[domain.strip()], 'person_titles':titles, 'page':1, 'per_page':25})
        if response.status_code in (401,403):
            raise ValueError('Apollo denied access. Verify the API key and account eligibility.')
        if response.status_code==429:
            raise ValueError('Apollo rate limit reached. Try again after the account limit resets.')
        response.raise_for_status()
        return response.json().get('people', [])
