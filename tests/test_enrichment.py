from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Base, Business, Email, ScrapingJob, SocialProfile, VisitedPage
from services import pipeline


def test_job_persists_published_contacts_and_resumes(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    engine = create_engine(f'sqlite:///{tmp_path / "leads.db"}')
    Base.metadata.create_all(engine)
    monkeypatch.setattr(pipeline, 'engine', engine)
    record = dict(name='Fictional Dental', niche='dentists', category='dentist', address='1 Main St', city='Houston', state='TX', phone='', website='https://fictional-dental.com', source='OpenStreetMap', source_url='https://www.openstreetmap.org/node/1')
    monkeypatch.setattr(pipeline, 'discover', lambda *args: [record])
    monkeypatch.setattr(pipeline, 'crawl', lambda *args: [('https://fictional-dental.com/contact', '<a href="mailto:office@fictional-dental.com">Email</a><a href="https://instagram.com/fictionaldental">Instagram</a>', 200)])
    monkeypatch.setattr(pipeline, 'validate_business_email', lambda value: (value, True, True, 'unverified_mailbox'))
    job_id = pipeline.create_job('dentists', 'Houston', 'TX', 'OpenStreetMap', 1)
    pipeline.run_job(job_id)
    with Session(engine) as db:
        job = db.get(ScrapingJob, job_id)
        assert (job.status, job.discovered_count, job.processed_count, job.email_found_count) == ('completed', 1, 1, 1)
        assert len(db.scalars(select(Business)).all()) == 1
        assert len(db.scalars(select(Email)).all()) == 1
        assert len(db.scalars(select(SocialProfile)).all()) == 1
        assert len(db.scalars(select(VisitedPage)).all()) == 1
        job.status = 'stopped'; db.commit()
    pipeline.run_job(job_id)
    with Session(engine) as db:
        job = db.get(ScrapingJob, job_id)
        assert (job.discovered_count, job.processed_count, job.email_found_count) == (1, 1, 1)
