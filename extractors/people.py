"""Find explicitly named people in structured website data."""
import json
from bs4 import BeautifulSoup

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
    return list({(p['name'],p['title']):p for p in found}.values())
