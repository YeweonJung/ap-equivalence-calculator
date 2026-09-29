import json
import sqlite3
import time

from app import app
from services import feedback_learning, feedback_store
from tests.test_feedback_api import configured, payload, submit


def test_saved_correction_trains_then_suggests_without_converting(configured):
    client = app.test_client()
    response = submit(client, payload(client))
    assert response.json['model_updated'] is True
    feedback_learning.invalidate()  # Simulate another worker/restart.
    item = client.post('/api/parse', json={'text': '할리l 8mg QD'}).json['items'][0]
    assert item['drug'] is None and item['conversions'] == []
    assert item['learned_suggestions'][0]['alias'] == '할돌'
    assert item['learned_suggestions'][0]['auto_accepted'] is False
    assert item['correction_suffix'] == ' 8mg QD'
    assert client.post('/api/parse', json={'text': '할돌 8mg QD'}).json['items'][0]['drug'] == 'haloperidol'


def test_conflicting_corrections_abstain_and_replay_is_not_extra_training(configured):
    client = app.test_client()
    first = payload(client)
    submit(client, first)
    submit(client, first)
    assert feedback_learning.suggestions('할리l 2mg')[0]['evidence_count'] == 1
    response = submit(client, payload(client, selected_alias='리튬'))
    assert response.json['model_updated'] is False
    assert feedback_learning.suggestions('할리l 2mg') == []


def test_old_consent_and_expired_records_never_train(configured):
    client = app.test_client()
    data = payload(client)
    data.pop('learning_consent')
    assert submit(client, data).status_code == 200
    assert feedback_learning.suggestions('할리l 2mg') == []
    submit(client, payload(client))
    with sqlite3.connect(configured) as db:
        db.execute('UPDATE medication_feedback SET created_at = ?', (int(time.time()) - 181*86400,))
    feedback_learning.invalidate()
    assert feedback_learning.suggestions('할리l 2mg') == []


def test_learning_rollback_and_storage_failure_preserve_calculation(configured, monkeypatch):
    client = app.test_client()
    submit(client, payload(client))
    monkeypatch.setenv('FEEDBACK_LEARNING_ENABLED', '0')
    assert feedback_learning.suggestions('할리l 2mg') == []
    monkeypatch.setenv('FEEDBACK_LEARNING_ENABLED', '1')
    feedback_learning.invalidate()
    def broken():
        raise RuntimeError('private')
    monkeypatch.setattr(feedback_store, 'training_records', broken)
    item = client.post('/api/parse', json={'text': '할리l 2mg'}).json['items'][0]
    assert item['learned_suggestions'] == []
    assert 'private' not in json.dumps(item)
    assert client.post('/api/parse', json={'text': 'haloperidol 2mg'}).status_code == 200


def test_training_rejects_dictionary_mismatch_and_tampered_targets(configured):
    client = app.test_client()
    submit(client, payload(client))
    record = feedback_store.training_records()[0]
    for changed in [dict(record, selected_drug='risperidone'),
                    dict(record, dictionary_version='old'),
                    dict(record, name_token='haloperidol'),
                    dict(record, learning_consent=False)]:
        assert feedback_learning.train([changed]) == {}
