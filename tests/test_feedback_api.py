import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from app import app
from services import feedback_store
from services.feedback_api import signer


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.delenv('RENDER', raising=False)
    monkeypatch.delenv('FEEDBACK_DATABASE_URL', raising=False)
    monkeypatch.setenv('FEEDBACK_SIGNING_KEY', 'test-only-signing-key-never-production')
    path = tmp_path / 'feedback.sqlite'
    monkeypatch.setenv('FEEDBACK_SQLITE_PATH', str(path))
    return path


def payload(client, original='할리l 2mg BID', **updates):
    item = client.post('/api/parse', json={'text': original}).json['items'][0]
    data = dict(token=item['feedback_token'], selected_alias='할돌', source='candidate', consent=True)
    data.update(updates)
    return data


def submit(client, data, **kwargs):
    return client.post('/api/name-feedback', json=data, headers={'Origin':'http://localhost'}, **kwargs)


def rows(path):
    with sqlite3.connect(path) as db:
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM medication_feedback')]


def test_opt_in_only_and_no_prescription_or_identifiers(configured):
    client = app.test_client()
    data = payload(client)
    assert not configured.exists()  # Parsing alone writes nothing.
    assert submit(client, dict(data, consent=False)).status_code == 400
    assert not configured.exists()
    assert submit(client, data).json['status'] == 'saved'
    assert submit(client, data).json['status'] == 'already_saved'
    records = rows(configured)
    assert len(records) == 1
    record = records[0]
    assert record['name_token'] == '할리l' and record['selected_drug'] == 'haloperidol'
    assert record['review_status'] == 'pending' and record['eligible_for_training'] is False
    assert set(record) == {'schema_version','name_token','selected_alias','selected_drug',
        'presented_aliases','source','retrieval_version','dictionary_version','review_status',
        'eligible_for_training','user_confirmed_name_only'}
    assert '2mg' not in json.dumps(record) and 'BID' not in json.dumps(record)


def test_direct_correction_is_pending_and_requires_registered_name(configured):
    client = app.test_client()
    data = payload(client, selected_alias='리튬', source='manual')
    assert submit(client, dict(data, selected_alias='환자 홍길동 123')).status_code == 400
    assert submit(client, data).status_code == 200
    assert rows(configured)[0]['source'] == 'manual'


def test_tampering_origin_unknown_candidate_and_extra_fields_rejected(configured):
    client = app.test_client()
    data = payload(client)
    assert client.post('/api/name-feedback', json=data).status_code == 403
    assert client.post('/api/name-feedback', json=data, headers={'Origin':'https://evil.test'}).status_code == 403
    for invalid in [dict(data, token='bad'), dict(data, selected_alias='리튬'),
                    dict(data, patient='secret'), dict(data, source='automatic')]:
        assert submit(client, invalid).status_code == 400


def test_expired_token_rejected(configured, monkeypatch):
    client = app.test_client()
    data = payload(client)
    monkeypatch.setattr('itsdangerous.timed.TimestampSigner.get_timestamp', lambda self: 9999999999)
    assert submit(client, data).status_code == 400


def test_db_failure_does_not_break_conversion_or_claim_saved(configured, monkeypatch):
    client = app.test_client()
    data = payload(client)
    def broken(*args):
        raise RuntimeError('private connection secret')
    monkeypatch.setattr(feedback_store, 'save', broken)
    result = submit(client, data)
    assert result.status_code == 503 and 'secret' not in result.text
    assert client.post('/api/parse', json={'text':'할돌 2mg BID'}).json['items'][0]['conversions']


def test_concurrent_replays_write_one_event(configured):
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: feedback_store.save('same-event', {'review_status':'pending'}), range(8)))
    assert outcomes.count('saved') == 1 and len(rows(configured)) == 1


def test_disabled_on_render_without_durable_db(configured, monkeypatch):
    monkeypatch.setenv('RENDER', 'true')
    client = app.test_client()
    item = client.post('/api/parse', json={'text':'할리l 2mg BID'}).json['items'][0]
    assert 'feedback_token' not in item and item['correction_suffix'] == ' 2mg BID'
    assert client.post('/api/name-feedback', json={}).status_code == 503


def test_invalid_name_shape_never_gets_record_token(configured):
    client = app.test_client()
    result = client.post('/api/parse', json={'text':'홍길동@example.com 2mg BID'}).json
    assert all('feedback_token' not in item for item in result['items'])
