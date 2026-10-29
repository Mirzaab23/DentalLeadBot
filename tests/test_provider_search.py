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
    with pytest.raises(ValueError,match='Supported search URLs'):
        pipeline.create_job('dentists','Houston','TX','All sources',10,'https://www.linkedin.com/search/results/people/')
