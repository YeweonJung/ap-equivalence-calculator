import pytest
from services.upload_aliases import parse_upload_frames


@pytest.mark.parametrize('source,drug,dose', [
    ('pariperidone 6mg(MED;경구)', 'paliperidone', 6),
    ('aripiprazold 2mg', 'aripiprazole', 2),
    ('queiapine 100mg', 'quetiapine', 100),
])
def test_confirmed_spelling_keeps_dose_and_original(source, drug, dose):
    item = parse_upload_frames(source)[0]
    assert item['drug'] == drug and item['dose_mg'] == dose
    assert item['original'] == source
    assert item['status'] == 'ready'
    assert item['match_type'] == 'user_confirmed_alias'


def test_multiple_medications_keep_original_spans():
    text = 'risperidone 2mg, haloperidol 10mg, queiapine 100mg'
    items = parse_upload_frames(text)
    assert [i['drug'] for i in items] == ['risperidone', 'haloperidol', 'quetiapine']
    assert all(text[i['source_start']:i['source_end']] == i['original'] for i in items)


def test_nearby_unconfirmed_spelling_is_not_accepted():
    assert parse_upload_frames('pariperidon 6mg')[0]['drug'] is None


def test_shared_lai_route_survives_confirmed_spelling():
    items = parse_upload_frames('pariperidone 150mg PP1M, aripiprazole 400mg (LAI둘다)')
    assert items[0]['route'] == 'injection' and items[0]['interval_days'] == 30
    assert items[1]['status'] == 'unsupported_formulation'
