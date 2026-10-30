from extractors.people import extract_people
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from database.models import Base, Person
from services.people_repository import save_apollo_people

def test_named_person_with_provenance_fields():
    html='<script type="application/ld+json">{"@context":"https://schema.org","@type":"Dentist","employee":{"@type":"Person","name":"Ada Rivera","jobTitle":"Practice Owner","email":"ada@clinic.test","telephone":"555-0100"}}</script>'
    people=extract_people(html)
    assert len(people)==1
    assert people[0]['name']=='Ada Rivera'
    assert people[0]['title']=='Practice Owner'

def test_generic_office_mailbox_does_not_create_person():
    assert extract_people('<a href="mailto:office@clinic.test">Office</a>')==[]

def test_team_card_collects_only_published_person_contacts():
    html='<div class="team-member"><h3>Ada Rivera</h3><span class="role">Managing Partner</span><a href="mailto:ada@example.test">Email</a><a href="tel:+15125550100">Call</a></div>'
    assert extract_people(html)==[{'name':'Ada Rivera','title':'Managing Partner','email':'ada@example.test','phone':'+15125550100','linkedin':''}]

def test_apollo_preview_saves_only_named_people(tmp_path):
    engine=create_engine(f'sqlite:///{tmp_path / "people.db"}')
    Base.metadata.create_all(engine)
    results=[{'id':'abc','name':'Jane Doe','title':'Owner'}, {'id':'hidden','name':'J*** D***','title':'CEO'}]
    assert save_apollo_people(engine,results)==1
    assert save_apollo_people(engine,results)==0
    with Session(engine) as db:
        person=db.scalar(select(Person))
        assert person.name=='Jane Doe'
        assert person.email==''
        assert person.email_status=='unavailable'
