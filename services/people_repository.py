"""Persist only explicitly returned person identities and source evidence."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Person

def save_apollo_people(engine, results):
    saved=0
    with Session(engine) as db:
        for item in results:
            name=(item.get('name') or '').strip()
            provider_id=item.get('id')
            if not name or not provider_id or '*' in name:
                continue
            source_url=f'https://app.apollo.io/#/people/{provider_id}'
            if db.scalar(select(Person).where(Person.source=='Apollo',Person.source_url==source_url)):
                continue
            organization=item.get('organization') or {}
            domain=(organization.get('primary_domain') or '').lower().removeprefix('www.')
            business=None
            if domain:
                for candidate in db.scalars(select(Business).where(Business.website!='')):
                    from urllib.parse import urlsplit
                    if (urlsplit(candidate.website).hostname or '').lower().removeprefix('www.')==domain:
                        business=candidate
                        break
            db.add(Person(business_id=business.id if business else None,name=name,title=item.get('title') or '',email='',email_status='unavailable',phone='',city=item.get('city') or '',state=item.get('state') or '',linkedin=item.get('linkedin_url') or '',source='Apollo',source_url=source_url))
            saved+=1
        db.commit()
    return saved
