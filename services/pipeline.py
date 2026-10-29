"""Persist discovery jobs; interrupted work can be resumed."""
import os
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Email, JobBusiness, ScrapingJob, SocialProfile, VisitedPage, initialize, now
from discovery.osm import discover
from crawlers.website import crawl
from extractors.emails import extract_emails
from extractors.social import extract_social
from services.validator import validate_business_email

Path('data').mkdir(exist_ok=True)
engine = initialize(os.getenv('DATABASE_URL', 'sqlite:///data/leads.db'))

def create_job(niche, city, state, source, limit):
    if source != 'OpenStreetMap':
        raise ValueError('Only OpenStreetMap discovery is available in this MVP')
    with Session(engine) as db:
        job = ScrapingJob(niche=niche, city=city, state=state, source=source, target_count=limit)
        db.add(job); db.commit(); return job.id

def run_job(job_id):
    with Session(engine) as db:
        job = db.get(ScrapingJob, job_id)
        if not job: raise ValueError('Job not found')
        if job.status == 'completed': return
        job.status = 'running'; job.finished_at = None; job.last_error = ''; db.commit()
        niche, city, state, limit = job.niche, job.city, job.state, job.target_count
    try:
        records = discover(niche, city, state, limit)
        for record in records:
            with Session(engine) as db:
                job = db.get(ScrapingJob, job_id)
                if job.status == 'stop_requested':
                    job.status = 'stopped'; db.commit(); return
                existing = db.scalar(select(Business).where(Business.source == record['source'], Business.source_url == record['source_url']))
                if existing is None:
                    existing = Business(**record); db.add(existing); db.flush()
                seen = db.scalar(select(JobBusiness).where(JobBusiness.job_id == job_id, JobBusiness.business_id == existing.id))
                if seen is not None:
                    continue
                db.add(JobBusiness(job_id=job_id, business_id=existing.id))
                job.discovered_count += 1
                db.commit()
                business_id, website = existing.id, existing.website
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
                        business.status = 'enriched' if pages else 'no_pages'
                        db.commit()
                except Exception as exc:
                    with Session(engine) as db:
                        db.get(ScrapingJob, job_id).last_error = f'{website}: {exc}'
                        db.commit()
            with Session(engine) as db:
                db.get(ScrapingJob, job_id).processed_count += 1
                db.commit()
        with Session(engine) as db:
            job = db.get(ScrapingJob, job_id); job.status = 'completed'; job.finished_at = now(); db.commit()
    except Exception as e:
        with Session(engine) as db:
            job = db.get(ScrapingJob, job_id); job.status = 'failed'; job.last_error = str(e); job.finished_at = now(); db.commit()
        raise

