"""Authenticated outbound-worker transport, separate from the public calculator."""
import hmac
import os
import re
from flask import Blueprint, jsonify, request
from services import llm_jobs

bp = Blueprint('llm_worker', __name__)


@bp.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@bp.before_request
def authorize():
    key = os.getenv('NAME_LLM_WORKER_KEY', '')
    if len(key) < 32 or os.getenv('NAME_LLM_BACKEND') != 'worker':
        return jsonify(error='Unavailable'), 503
    expected = 'Bearer '+key
    if not hmac.compare_digest(request.headers.get('Authorization', '').encode(), expected.encode()):
        return jsonify(error='Unauthorized'), 401


@bp.get('/api/name-llm/jobs/next')
def next_job():
    job = llm_jobs.claim()
    response = jsonify(job) if job else ('', 204)
    return response


@bp.post('/api/name-llm/heartbeat')
def heartbeat():
    llm_jobs.heartbeat()
    return '', 204


@bp.post('/api/name-llm/jobs/<job_id>')
def finish_job(job_id):
    if not re.fullmatch('[a-f0-9]{32}', job_id):
        return jsonify(error='Invalid job'), 400
    if not request.content_length or request.content_length > 32768:
        return jsonify(error='Invalid size'), 413
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {'result'} or not isinstance(data['result'], str):
        return jsonify(error='Invalid result'), 400
    if len(data['result']) > 16000:
        return jsonify(error='Invalid result'), 400
    return ('', 204) if llm_jobs.complete(job_id, data['result']) else (jsonify(error='Expired job'), 410)
