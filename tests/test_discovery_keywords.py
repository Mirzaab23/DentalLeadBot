from discovery.osm import KNOWN_TAGS

def test_unrelated_niches_have_distinct_osm_categories():
    assert KNOWN_TAGS['dentists']==('amenity','dentist')
    assert KNOWN_TAGS['coffee shops']==('amenity','cafe')
    assert KNOWN_TAGS['lawyers']==('office','lawyer')
