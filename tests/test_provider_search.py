import httpx
import pytest
from services import people
from services import pipeline

def test_people_filter_payload(monkeypatch):
    captured={}
    def post(self,url,headers,json):
        captured.update(json)
        return httpx.Response(200,json={'people':[]},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.Client,'post',post)
    people.search_people('key',titles=['CEO'],location='Texas',industry='hospital & health care')
    assert captured['person_titles']==['CEO']
    assert captured['person_locations']==['Texas']
    assert 'q_organization_domains_list' not in captured

def test_directory_url_rejects_unsupported_platform():
    with pytest.raises(ValueError,match='Supported platform URLs'):
        pipeline.create_job('dentists','Houston','TX','All sources',10,'https://www.linkedin.com/search/results/people/')

def test_yelp_home_url_selects_source_and_stores_country(tmp_path,monkeypatch):
    from sqlalchemy import create_engine,select
    from sqlalchemy.orm import Session
    from database.models import Base,JobLocation,ScrapingJob
    engine=create_engine(f'sqlite:///{tmp_path / "jobs.db"}')
    Base.metadata.create_all(engine)
    monkeypatch.setattr(pipeline,'engine',engine)
    job_id=pipeline.create_job('coffee shops','Lahore','Punjab','All sources',3,'https://www.yelp.com/','Pakistan')
    with Session(engine) as db:
        assert db.get(ScrapingJob,job_id).source=='Yelp'
        assert db.scalar(select(JobLocation).where(JobLocation.job_id==job_id)).country=='Pakistan'
