"""Research-only name assistance; dose calculations keep the existing rules."""
import hashlib
import json
import os
import time
from urllib.request import Request, build_opener
from services import llm_candidates as llm
from services.name_dictionary import name_and_suffix
from services.parser import alias_map

MODELS = {'gpt': 'openai/gpt-5.4', 'claude': 'anthropic/claude-sonnet-4.6',
          'gemini': 'google/gemini-3.1-pro-preview', 'deepseek': 'deepseek/deepseek-v3.2'}
MODES = {'off', 'qwen', *MODELS}
PROMPT_VERSION = 'name-candidate-controlled-v1'


def capabilities():
    backend = os.getenv('NAME_LLM_BACKEND', 'ollama')
    available = llm.enabled()
    if backend == 'worker':
        from services import llm_jobs
        available = llm_jobs.online()
    return dict(qwen=dict(available=available, backend=backend,
        model=os.getenv('NAME_LLM_MODEL', 'qwen2.5:7b')),
        cloud_models=MODELS, cloud_credential='researcher_request_only')


def _cloud(messages, model, key):
    # A fixed HTTPS destination and request-scoped credential, never a public server key.
    payload = dict(model=model, messages=messages, temperature=0,
        max_tokens=1000, stream=False, response_format={'type': 'json_object'},
        provider={'allow_fallbacks': False, 'require_parameters': True})
    req = Request('https://openrouter.ai/api/v1/chat/completions',
        data=json.dumps(payload).encode(), headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer '+key})
    with build_opener(llm._NoRedirect()).open(req, timeout=60) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('response_size')
    result = json.loads(raw)
    return result['choices'][0]['message']['content'], {
        'returned_model': result.get('model'), 'provider': result.get('provider'),
        'usage': result.get('usage'), 'response_id': result.get('id')}


def _qwen(messages):
    backend = os.getenv('NAME_LLM_BACKEND', 'ollama')
    if backend == 'worker':
        from services import llm_jobs
        job = llm_jobs.submit(messages)
        if not job:
            raise ConnectionError('worker_unavailable')
        try:
            deadline = time.monotonic()+85
            while time.monotonic() < deadline:
                result = llm_jobs.take(job)
                if result is not None:
                    return result, {'returned_model': None, 'model_identity_source': 'worker_configuration'}
                time.sleep(.25)
            raise TimeoutError('worker_timeout')
        finally:
            llm_jobs.discard(job)
    if backend not in {'ollama', 'mlx'}:
        raise ValueError('unsupported_backend')
    return (llm._mlx(messages) if backend == 'mlx' else llm._ollama(messages)), {
        'returned_model': None, 'model_identity_source': 'server_configuration'}


def annotate(items, mode, key=None):
    if mode not in MODES:
        raise ValueError('invalid_mode')
    key = key if isinstance(key, str) and 10 <= len(key) <= 500 and '\n' not in key and '\r' not in key else None
    config = capabilities() if mode == 'qwen' else None
    available = mode == 'off' or (config['qwen']['available'] if config else bool(key))
    requested = MODELS.get(mode) or (config['qwen']['model'] if config else None)
    calls = []
    for item in items:
        if item.get('status') != 'unknown_drug':
            continue
        _, item['correction_suffix'] = name_and_suffix(item['original'])
        item['learned_suggestions'] = []
        item['suggestion_label'] = 'AI 미확인 후보'
        context = llm._context(item['original'])
        if mode == 'off' or context is None:
            continue
        if not available:
            calls.append(dict(status='unavailable', invoked=False, elapsed_seconds=0))
            continue
        messages = llm._messages(context[0], context[2], sorted(set(alias_map.values())))
        prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        started = time.perf_counter()
        call = dict(status='error', invoked=True, prompt_hash=prompt_hash, requested_model=requested)
        try:
            output, meta = _qwen(messages) if mode == 'qwen' else _cloud(messages, requested, key)
            call.update(meta)
            parsed = json.loads(output)
            if not isinstance(parsed, dict) or parsed.get('status') not in {'candidate_found', 'unknown'} or not isinstance(parsed.get('candidates'), list):
                raise ValueError('invalid_response')
            candidates = llm.validate_response(output, item['original'])
            if parsed['status'] == 'candidate_found' and not candidates:
                raise ValueError('invalid_candidates')
            item['learned_suggestions'] = candidates
            call.update(status='success', candidate_count=len(candidates), candidate_names=[c['drug'] for c in candidates])
        except Exception as exc:
            # Exception text could contain request data; do not log or return it.
            call['error_type'] = type(exc).__name__
        call['elapsed_seconds'] = round(time.perf_counter()-started, 3)
        calls.append(call)
    return dict(protocol='ap-study-2', mode=mode, ai_feature='llm_name_candidates',
        ai_available=available, ai_invocation_count=sum(c['invoked'] for c in calls),
        ai_candidate_count=sum(len(i.get('learned_suggestions', [])) for i in items),
        ai_success_count=sum(c['status'] == 'success' for c in calls),
        ai_elapsed_seconds=round(sum(c['elapsed_seconds'] for c in calls), 3),
        requested_model=requested, prompt_version=PROMPT_VERSION, calls=calls,
        app_commit=os.getenv('RENDER_GIT_COMMIT', 'local'))
