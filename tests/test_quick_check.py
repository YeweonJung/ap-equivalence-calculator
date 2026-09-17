import pytest
from app import app
from services.drug_suggestions import suggest_drugs


@pytest.mark.parametrize('text,drug', [
    ('리스페딜 2mg BID', 'risperidone'),
    ('자이프렉서 5mg QD', 'olanzapine'),
    ('쎄로겔 25mg QD', 'quetiapine'),
])
def test_unknown_korean_name_has_candidate_without_auto_conversion(text, drug):
    client = app.test_client()
    response = client.post('/api/parse', json={'text': text})
    assert response.status_code == 200
    item = response.json['items'][0]
    assert not item['ok']
    assert item['conversions'] == []
    suggestion = next(s for s in item['suggestions'] if s['drug'] == drug)
    confirmed = client.post('/api/parse', json={'text': suggestion['replacement']}).json['items'][0]
    assert confirmed['drug'] == drug
    assert confirmed['ok']


def test_candidates_preserve_dose_frequency_and_other_medications():
    text = 'olanzapine 5mg QD; 리스페딜 2mg PRN'
    items = app.test_client().post('/api/parse', json={'text': text}).json['items']
    unknown = items[1]
    replacement = next(s['replacement'] for s in unknown['suggestions'] if s['drug'] == 'risperidone')
    assert replacement.endswith('2mg PRN')
    corrected = text[:unknown['source_start']] + replacement + text[unknown['source_end']:]
    result = app.test_client().post('/api/parse', json={'text': corrected}).json['items']
    assert result[0]['drug'] == 'olanzapine'
    assert result[1]['status'] == 'review'
    assert result[1]['conversions'] == []


def test_short_unknown_name_does_not_get_a_guess():
    assert suggest_drugs('아리 5mg QD') == []
    assert suggest_drugs('zzzzzzzzzz 5mg QD') == []


def test_page_links_script_and_api():
    client = app.test_client()
    page = client.get('/').get_data(as_text=True)
    assert 'data-api-url="/api/parse"' in page
    assert '/static/quick_check.js' in page
    assert client.get('/static/quick_check.js').status_code == 200
