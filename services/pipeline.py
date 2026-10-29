"""Persist discovery jobs; interrupted work can be resumed."""
import os
from urllib.parse import urlsplit
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Email, JobBusiness, ProcessedBusiness, JobSeed, Person, ScrapingJob, SocialProfile, VisitedPage, initialize, now
from discovery.osm import discover
from discovery.google_maps import discover as discover_google
from discovery.yelp import discover as discover_yelp
from crawlers.website import crawl
from extractors.emails import extract_emails
from extractors.social import extract_social
from extractors.people import extract_people
from services.validator import validate_business_email
from services.repair import repair_business

Path('data').mkdir(exist_ok=True)
engine = initialize(os.getenv('DATABASE_URL', 'sqlite:///data/leads.db'))

def create_job(niche, city, state, source, limit, directory_url=''):
    if directory_url:
        parsed=urlsplit(directory_url)
        host=(parsed.hostname or '').lower()
        if parsed.scheme!='https' or parsed.username or parsed.password:
            raise ValueError('Use a public HTTPS directory URL.')
        if host in ('www.yelp.com','yelp.com') and parsed.path.startswith('/search'):
            source='Yelp'
        elif host in ('www.google.com','google.com') and parsed.path.startswith('/maps/search'):
            source='Google Maps'
        else:
            raise ValueError('Supported search URLs: Yelp /search and Google Maps /maps/search. LinkedIn requires approved API access.')
    if source not in ('All sources', 'OpenStreetMap', 'Google Maps', 'Yelp'):
        raise ValueError('Unsupported discovery source')
    with Session(engine) as db:
        job = ScrapingJob(niche=niche, city=city, state=state, source=source, target_count=limit)
        db.add(job); db.flush()
        if directory_url: db.add(JobSeed(job_id=job.id,url=directory_url))
        db.commit(); return job.id

def run_job(job_id):
    with Session(engine) as db:
        job = db.get(ScrapingJob, job_id)
        if not job: raise ValueError('Job not found')
        if job.status == 'completed': return
        job.status = 'running'; job.finished_at = None; job.last_error = ''; db.commit()
        niche, city, state, limit, source = job.niche, job.city, job.state, job.target_count, job.source
        seed=db.scalar(select(JobSeed).where(JobSeed.job_id==job_id))
        directory_url=seed.url if seed else ''
    try:
        adapters = {'Google Maps': discover_google, 'OpenStreetMap': discover, 'Yelp': discover_yelp}
        records, errors = [], []
        for source_name in (adapters if source == 'All sources' else (source,)):
            with Session(engine) as db:
                if db.get(ScrapingJob, job_id).status == 'stop_requested':
                    db.get(ScrapingJob, job_id).status = 'stopped'; db.commit(); return
            try:
                if directory_url and source_name in ('Yelp','Google Maps'):
                    records.extend(adapters[source_name](niche, city, state, limit, directory_url))
                else:
                    records.extend(adapters[source_name](niche, city, state, limit))
            except Exception as exc:
                errors.append(f'{source_name}: {exc}')
        if errors:
            with Session(engine) as db:
                db.get(ScrapingJob, job_id).last_error = ' | '.join(errors)
                db.commit()
        if not records:
            raise RuntimeError('No source returned accessible listings. ' + ' | '.join(errors))
        for record in records:
            with Session(engine) as db:
                job = db.get(ScrapingJob, job_id)
                if job.status == 'stop_requested':
                    job.status = 'stopped'; db.commit(); return
                if job.discovered_count >= job.target_count:
                    break
                existing = db.scalar(select(Business).where(Business.source == record['source'], Business.source_url == record['source_url']))
                if existing is None:
                    candidates = db.scalars(select(Business).where(Business.name == record['name'], Business.city == record['city'], Business.state == record['state'])).all()
                    existing = next((candidate for candidate in candidates if (record.get('phone') and candidate.phone == record['phone']) or (record.get('address') and candidate.address == record['address'])), None)
                if existing is None:
                    existing = Business(**record); db.add(existing); db.flush()
                else:
                    for field in ('website', 'phone', 'address', 'category'):
                        if not getattr(existing, field) and record.get(field):
                            setattr(existing, field, record[field])
                seen = db.scalar(select(JobBusiness).where(JobBusiness.job_id == job_id, JobBusiness.business_id == existing.id))
                if seen is None:
                    db.add(JobBusiness(job_id=job_id, business_id=existing.id))
                    job.discovered_count += 1
                db.commit()
                business_id, website = existing.id, existing.website
                if db.scalar(select(ProcessedBusiness).where(ProcessedBusiness.job_id == job_id, ProcessedBusiness.business_id == business_id)):
                    continue
            if not website:
                try:
                    repair_business(engine, business_id)
                    with Session(engine) as db:
                        website = db.get(Business,business_id).website
                except Exception as exc:
                    with Session(engine) as db:
                        db.get(Business,business_id).status = 'lookup_failed'
                        db.get(ScrapingJob,job_id).last_error = str(exc)
                        db.commit()
            if website:
                try:
                    pages = crawl(website)
                    with Session(engine) as db:
                        job = db.get(ScrapingJob, job_id)
                        business = db.get(Business, business_id)
                        for url, html, code in pages:
                            if not db.scalar(select(VisitedPage).where(VisitedPage.business_id == business_id, VisitedPage.url == url)):
                                db.add(VisitedPage(business_id=business_id, url=url, status_code=code, crawl_status='ok'))
                            for value in extract_emails(html):
                                normalized, syntax, mx, status = validate_business_email(value)
                                if not db.scalar(select(Email).where(Email.business_id == business_id, Email.email == normalized, Email.source_url == url)):
                                    db.add(Email(business_id=business_id, email=normalized, source_url=url, syntax_valid=syntax, mx_valid=mx, validation_status=status))
                                    job.email_found_count += 1
                            for platform, profile in extract_social(html):
                                if not db.scalar(select(SocialProfile).where(SocialProfile.business_id == business_id, SocialProfile.platform == platform, SocialProfile.profile_url == profile)):
                                    db.add(SocialProfile(business_id=business_id, platform=platform, profile_url=profile, source_url=url))
                            for found in extract_people(html):
                                if not db.scalar(select(Person).where(Person.business_id==business_id,Person.name==found['name'],Person.source_url==url)):
                                    email=found['email']
                                    db.add(Person(business_id=business_id,name=found['name'],title=found['title'],email=email,email_status='published_unverified' if email else 'unavailable',phone=found['phone'],linkedin=found['linkedin'],city=business.city,state=business.state,source='Company website',source_url=url))
                        business.status = 'enriched' if pages else 'no_pages'
                        db.commit()
                except Exception as exc:
                    with Session(engine) as db:
                        db.get(ScrapingJob, job_id).last_error = f'{website}: {exc}'
                        db.commit()
            with Session(engine) as db:
                db.add(ProcessedBusiness(job_id=job_id, business_id=business_id))
                db.get(ScrapingJob, job_id).processed_count += 1
                db.commit()
        with Session(engine) as db:
            job = db.get(ScrapingJob, job_id); job.status = 'completed'; job.finished_at = now(); db.commit()
    except Exception as e:
        with Session(engine) as db:
            job = db.get(ScrapingJob, job_id); job.status = 'failed'; job.last_error = str(e); job.finished_at = now(); db.commit()
        raise

