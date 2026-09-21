"""Opt-in collection of bounded drug-name corrections, not prescriptions."""
import os
import re
import uuid
from urllib.parse import urlsplit

from flask import Blueprint, jsonify, request
from itsdangerous import URLSafeTimedSerializer, BadSignature
from services import feedback_store
from services.name_dictionary import name_and_suffix, dictionary_version
from services.parser import alias_map
from services.manual_suggestions import SERVING_VERSION

bp = Blueprint('feedback', __name__)


def signer():
    return URLSafeTimedSerializer(os.environ['FEEDBACK_SIGNING_KEY'], salt='medication-feedback-v1')


def safe_token(value):
    # A shape filter cannot prove a token is not a person's name. Consent is required.
    return isinstance(value, str) and bool(re.fullmatch(r'[a-zA-Z가-힣]{2,40}', value))


def attach_feedback(item):
    if item.get('status') != 'unknown_drug':
        return
    name, suffix = name_and_suffix(item['original'])
    item['correction_suffix'] = suffix
    if not feedback_store.configured() or not safe_token(name):
        return
    candidates = [c['alias'] for c in item.get('suggestions', []) if c['alias'] in alias_map]
    item['feedback_token'] = signer().dumps(dict(event_id=str(uuid.uuid4()), name=name,
        candidates=candidates, retrieval_version=SERVING_VERSION, dictionary_version=dictionary_version()))


@bp.post('/api/name-feedback')
def submit_feedback():
    if not feedback_store.configured():
        return jsonify(error='기록 저장소가 연결되지 않았습니다. 계산은 계속 이용할 수 있습니다.'), 503
    origin = request.headers.get('Origin', '')
    if not origin or urlsplit(origin).netloc != request.host or request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return jsonify(error='같은 사이트에서 제출해 주세요.'), 403
    if not request.content_length or request.content_length > 4096:
        return jsonify(error='기록 요청이 너무 큽니다.'), 413
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {'token', 'selected_alias', 'source', 'consent'} or data['consent'] is not True:
        return jsonify(error='약물명만 포함되어 있다는 확인과 기록 제공 동의가 필요합니다.'), 400
    if not isinstance(data['token'], str) or len(data['token']) > 3000:
        return jsonify(error='유효하지 않은 기록입니다.'), 400
    try:
        signed = signer().loads(data['token'], max_age=900)
    except BadSignature:
        return jsonify(error='기록 시간이 만료됐습니다. 다시 계산해 주세요.'), 400
    alias = data['selected_alias']
    if not isinstance(alias, str) or alias not in alias_map or data['source'] not in ('candidate', 'manual'):
        return jsonify(error='등록된 정확한 약물명을 입력해 주세요.'), 400
    if not safe_token(signed.get('name')) or (data['source'] == 'candidate' and alias not in signed['candidates']):
        return jsonify(error='표시된 후보를 확인해 주세요.'), 400
    record = dict(schema_version=1, name_token=signed['name'], selected_alias=alias,
        selected_drug=alias_map[alias], presented_aliases=signed['candidates'], source=data['source'],
        retrieval_version=signed['retrieval_version'], dictionary_version=signed['dictionary_version'],
        review_status='pending', eligible_for_training=False, user_confirmed_name_only=True)
    try:
        status = feedback_store.save(signed['event_id'], record)
    except OverflowError:
        return jsonify(error='현재 기록 요청이 많습니다. 계산은 계속 이용할 수 있습니다.'), 429
    except Exception:
        # No request text, connection URL or exception is written to application logs.
        return jsonify(error='기록을 저장하지 못했습니다. 계산은 계속 이용할 수 있습니다.'), 503
    return jsonify(status=status, message='검토용으로 저장했습니다. 자동 학습에는 사용되지 않습니다.')
