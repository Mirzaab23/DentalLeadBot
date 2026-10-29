"""Apollo role search. Search results do not imply an email is available."""
import httpx

def search_people(api_key, domain='', titles=None, location='', industry='', seniority='', page=1, email_status=''):
    if not api_key.strip():
        raise ValueError('Connect an Apollo API key first.')
    titles = titles or []
    if not any((domain.strip(), titles, location.strip(), industry.strip(), seniority.strip())):
        raise ValueError('Add at least one people-search filter.')
    params = {'page': page, 'per_page': 25}
    if domain.strip(): params['q_organization_domains_list'] = [domain.strip().removeprefix('www.')]
    if titles: params['person_titles'] = titles
    if location.strip(): params['person_locations'] = [location.strip()]
    if industry.strip(): params['organization_industries'] = [industry.strip().lower()]
    if seniority.strip(): params['person_seniorities'] = [seniority.strip()]
    if email_status.strip(): params['contact_email_status'] = [email_status.strip()]
    with httpx.Client(timeout=30) as client:
        response = client.post('https://api.apollo.io/api/v1/mixed_people/api_search', headers={'x-api-key': api_key, 'Content-Type':'application/json'}, json=params)
        if response.status_code in (401,403):
            raise ValueError('Apollo denied access. Verify the API key and account eligibility.')
        if response.status_code==429:
            raise ValueError('Apollo rate limit reached. Try again after the account limit resets.')
        response.raise_for_status()
        return response.json().get('people', [])

def search_companies(api_key, keyword='', location='', domain='', page=1):
    if not api_key.strip(): raise ValueError('Connect an Apollo API key first.')
    if not any((keyword.strip(),location.strip(),domain.strip())): raise ValueError('Add a company keyword, location or domain.')
    params={'page':page,'per_page':25}
    if keyword.strip(): params['q_organization_keyword_tags']=[keyword.strip()]
    if location.strip(): params['organization_locations']=[location.strip()]
    if domain.strip(): params['q_organization_domains_list']=[domain.strip().removeprefix('www.')]
    with httpx.Client(timeout=30) as client:
        response=client.post('https://api.apollo.io/api/v1/mixed_companies/search',headers={'x-api-key':api_key,'Content-Type':'application/json'},json=params)
        if response.status_code in (401,403): raise ValueError('Apollo denied company search. Check account eligibility and API key access.')
        if response.status_code==429: raise ValueError('Apollo rate limit reached.')
        response.raise_for_status()
        return response.json().get('organizations',[])
