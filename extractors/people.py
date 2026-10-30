"""Find explicitly named people in structured website data."""
import json
from bs4 import BeautifulSoup

def _contact_link(card, scheme):
    link = card.select_one(f'a[href^="{scheme}:"]')
    return link['href'].split(':', 1)[1].split('?', 1)[0].strip() if link else ''

def _card_person(card):
    name_tag = card.select_one('[itemprop="name"], .name, h2, h3, h4')
    title_tag = card.select_one('[itemprop="jobTitle"], .title, .role, .position')
    if not name_tag or not title_tag: return None
    name, title = name_tag.get_text(' ', strip=True), title_tag.get_text(' ', strip=True)
    if not name or not title or len(name.split()) < 2 or len(name) > 90: return None
    linkedin = next((a['href'] for a in card.select('a[href]') if 'linkedin.com/in/' in a['href']), '')
    return {'name': name, 'title': title, 'email': _contact_link(card, 'mailto'), 'phone': _contact_link(card, 'tel'), 'linkedin': linkedin}

def extract_people(html):
    soup=BeautifulSoup(html,'lxml')
    found=[]
    def visit(node):
        if isinstance(node,list):
            for item in node: visit(item)
        elif isinstance(node,dict):
            kinds=node.get('@type',[])
            if isinstance(kinds,str): kinds=[kinds]
            if 'Person' in kinds and node.get('name'):
                found.append({'name':str(node['name']).strip(),'title':str(node.get('jobTitle') or '').strip(),'email':str(node.get('email') or '').removeprefix('mailto:').strip(),'phone':str(node.get('telephone') or '').strip(),'linkedin':next((url for url in node.get('sameAs',[]) if 'linkedin.com/in/' in url), '') if isinstance(node.get('sameAs'),list) else ''})
            for value in node.values():
                if isinstance(value,(dict,list)): visit(value)
    for script in soup.select('script[type="application/ld+json"]'):
        try: visit(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError): continue
    for card in soup.select('[itemtype*="schema.org/Person"], .team-member, .staff-member, .person-card, .profile-card'):
        person = _card_person(card)
        if person: found.append(person)
    return list({(p['name'],p['title']):p for p in found}.values())
