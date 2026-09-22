import json
import threading
from concurrent.futures import ThreadPoolExecutor
import time

import pytest
from app import app
from services import llm_jobs, llm_candidates


@pytest.fixture
def queue(monkeypatch, tmp_path):
    monkeypatch.setenv('NAME_LLM_QUEUE_PATH', str(tmp_path/'jobs.sqlite3'))
    monkeypatch.setenv('NAME_LLM_BACKEND', 'worker')
    monkeypatch.setenv('NAME_LLM_WORKER_KEY', 'test-only-worker-key-'*3)
    return {'Authorization': 'Bearer '+'test-only-worker-key-'*3}


def test_offline_does_not_queue_or_wait(queue):
    assert llm_jobs.submit([]) is None
    assert json.loads(llm_jobs.infer([]))['candidates'] == []


def test_worker_authentication_and_empty_poll(queue):
    client = app.test_client()
    assert client.get('/api/name-llm/jobs/next').status_code == 401
    assert client.get('/api/name-llm/jobs/next', headers=queue).status_code == 204
    assert llm_jobs.online()


def test_queue_roundtrip_and_erasure(queue):
    llm_jobs.heartbeat()
    job_id = llm_jobs.submit([{'role':'user','content':'synthetic name only'}])
    client = app.test_client()
    job = client.get('/api/name-llm/jobs/next', headers=queue).json
    assert job['id'] == job_id
    assert client.get('/api/name-llm/jobs/next', headers=queue).status_code == 204
    assert client.post('/api/name-llm/jobs/'+job_id, json={'result':'{}'}).status_code == 401
    assert client.post('/api/name-llm/jobs/'+job_id, json={'result':'{}'}, headers=queue).status_code == 204
    assert llm_jobs.take(job_id) == '{}'
    assert llm_jobs.take(job_id) is None
    assert client.post('/api/name-llm/jobs/'+job_id, json={'result':'{}'}, headers=queue).status_code == 410


def test_expiration_and_queue_limit(queue):
    llm_jobs.heartbeat()
    expired = llm_jobs.submit([], ttl=-1)
    assert llm_jobs.claim() is None
    assert llm_jobs.take(expired) is None
    ids = [llm_jobs.submit([]) for _ in range(4)]
    assert all(ids) and llm_jobs.submit([]) is None
    for job_id in ids:
        llm_jobs.discard(job_id)


def test_concurrent_workers_claim_each_job_once(queue):
    llm_jobs.heartbeat()
    ids = {llm_jobs.submit([]) for _ in range(4)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        claimed = list(pool.map(lambda _: llm_jobs.claim(), range(4)))
    assert {row['id'] for row in claimed} == ids


def test_public_parse_and_worker_preserve_manual_confirmation(queue, monkeypatch):
    monkeypatch.setenv('NAME_LLM_ENABLED', '1')
    llm_jobs.heartbeat()
    def worker():
        for _ in range(100):
            job = llm_jobs.claim()
            if job:
                serialized = json.dumps(job['messages'])
                assert '2mg' not in serialized and 'BID' not in serialized
                llm_jobs.complete(job['id'], json.dumps(dict(status='candidate_found', candidates=[
                    dict(standard_name='risperidone', confidence='low', reason='synthetic test')])) )
                return
            time.sleep(.02)
        raise AssertionError('No job received')
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        result = app.test_client().post('/api/parse', json={'text':'리쓰페리도오온 2mg BID'}).json
        future.result()
    item = result['items'][0]
    assert item['drug'] is None and item['conversions'] == []
    assert item['suggestions'][0]['replacement'] == 'risperidone 2mg BID'
    assert item['suggestions'][0]['auto_accepted'] is False


def test_callback_rejects_invalid_body(queue):
    client = app.test_client()
    assert client.post('/api/name-llm/jobs/not-a-job', headers=queue, json={}).status_code == 400
    assert client.post('/api/name-llm/jobs/'+'a'*32, headers=queue, json={'result': []}).status_code == 400
