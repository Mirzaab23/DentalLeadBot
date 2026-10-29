"""Revisit stored listings with incomplete published contact data."""
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Email, Person, SocialProfile, VisitedPage
from discovery.google_maps import discover
from crawlers.website import crawl
from extractors.emails import extract_emails
from extractors.social import extract_social
from extractors.people import extract_people
from services.validator import validate_business_email

def normalized(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())

def repair_business(engine, business_id):
    with Session(engine) as db:
        business = db.get(Business, business_id)
        if not business.website:
            candidates = discover(business.name, business.city, business.state, 3)
            match = next((r for r in candidates if normalized(r['name']) == normalized(business.name) and business.city.casefold() in r['address'].casefold() and len(business.name.split()) >= 3), None)
            if match:
                for field in ('website', 'phone', 'address'):
                    if match.get(field): setattr(business, field, match[field].strip())
                if not db.scalar(select(VisitedPage).where(VisitedPage.business_id==business_id, VisitedPage.url==match['source_url'])):
                    db.add(VisitedPage(business_id=business_id,url=match['source_url'],status_code=200,crawl_status='matched_listing'))
        website = business.website
        business.status = 'enrichment_pending' if website else 'website_not_found'
        db.commit()
    if not website: return 'website_not_found'
    pages = crawl(website)
    with Session(engine) as db:
        for url, html, code in pages:
            if not db.scalar(select(VisitedPage).where(VisitedPage.business_id==business_id,VisitedPage.url==url)):
                db.add(VisitedPage(business_id=business_id,url=url,status_code=code,crawl_status='ok'))
            for value in extract_emails(html):
                email,syntax,mx,status=validate_business_email(value)
                if not db.scalar(select(Email).where(Email.business_id==business_id,Email.email==email,Email.source_url==url)):
                    db.add(Email(business_id=business_id,email=email,source_url=url,syntax_valid=syntax,mx_valid=mx,validation_status=status))
            for platform,profile in extract_social(html):
                if not db.scalar(select(SocialProfile).where(SocialProfile.business_id==business_id,SocialProfile.profile_url==profile)):
                    db.add(SocialProfile(business_id=business_id,platform=platform,profile_url=profile,source_url=url))
            for found in extract_people(html):
                if not db.scalar(select(Person).where(Person.business_id==business_id,Person.name==found['name'],Person.source_url==url)):
                    db.add(Person(business_id=business_id,name=found['name'],title=found['title'],email=found['email'],email_status='published_unverified' if found['email'] else 'unavailable',phone=found['phone'],linkedin=found['linkedin'],city=db.get(Business,business_id).city,state=db.get(Business,business_id).state,source='Company website',source_url=url))
        status='enriched' if pages else 'no_accessible_pages'
        db.get(Business,business_id).status=status
        db.commit()
    return status

if __name__ == '__main__':
    from services.pipeline import engine
    with Session(engine) as db:
        ids=list(db.scalars(select(Business.id).where(Business.status!='enriched')))
    for business_id in ids:
        try: print(business_id, repair_business(engine,business_id),flush=True)
        except Exception as exc:
            with Session(engine) as db:
                db.get(Business,business_id).status='lookup_failed'; db.commit()
            print(business_id, str(exc),flush=True)
