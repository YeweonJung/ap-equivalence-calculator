"""Research-only name assistance; dose calculations keep the existing rules."""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.request import Request, build_opener
from urllib.error import HTTPError
from services import llm_candidates as llm
from services.name_dictionary import name_and_suffix
from services.parser import alias_map

MODELS = {
    # gemini-2.5-flash is closed to new API users (HTTP 404, 2026-10-27).
    'google_flash': 'gemini-3.8-flash',
    'google_gemma': 'gemma-4-31b-it',
    'groq_oss120': 'openai/gpt-oss-120b',
    'groq_oss20': 'openai/gpt-oss-20b',
    'groq_qwen': 'qwen/qwen3.8-27b',
}
PROVIDERS = {mode: ('google' if mode.startswith('google_') else 'groq') for mode in MODELS}
ENDPOINTS = {
    'google': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    'groq': 'https://api.groq.com/openai/v1/chat/completions',
}
MODES = {'off', 'qwen', *MODELS}
PROTOCOL = 'ap-study-4-direct-free'
COST_POLICY = 'free_tier_account_required'
PROMPT_VERSION = 'name-candidate-controlled-v1'
AUDIT_VERSION = 'ai-run-audit-v1'


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def repetition_context(index=1, count=1):
    if type(index) is not int or type(count) is not int or not 1 <= index <= count <= 3:
        raise ValueError('반복 회차는 1~3 범위의 정수여야 합니다.')
    return {'repeat_index': index, 'repeat_count': count}


def capabilities():
    backend = os.getenv('NAME_LLM_BACKEND', 'ollama')
    available = llm.enabled()
    if backend == 'worker':
        from services import llm_jobs
        available = llm_jobs.online()
    return dict(qwen=dict(available=available, backend=backend,
        model=os.getenv('NAME_LLM_MODEL', 'qwen2.5:7b')),
        cloud_models=MODELS, cloud_providers=PROVIDERS,
        cloud_credential='researcher_request_only',
        protocol=PROTOCOL, cost_policy=COST_POLICY,
        free_tier_confirmation_required=True, automatic_retry=False,
        paid_fallback=False, preview_ai_calls=False,
        # No provider API field can force a paid account to be billed as free.
        billing_verification='researcher_attestation_not_provider_verified',
        catalog_verified_at='2026-10-26', audit_version=AUDIT_VERSION,
        repetition_policy='separate_stateless_requests_max_3',
        repeat_count_planned=3, prompt_full_text_recorded=True)


def valid_key(provider, key):
    if not isinstance(key, str) or not 30 <= len(key) <= 200:
        return False
    if provider == 'groq':
        return bool(re.fullmatch(r'gsk_[A-Za-z0-9_-]{26,196}', key))
    return bool(re.fullmatch(r'AIza[A-Za-z0-9_-]{26,196}', key))


def _strip_thought(content):
    # Gemma may prepend <thought>...</thought> or wrap JSON in a code fence; keep only the JSON object.
    text = re.sub(r'<thought>.*?</thought>', '', content or '', flags=re.S).strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
    return text


def _cloud(messages, model, key, free_tier_confirmed=False):
    if model not in MODELS.values():
        raise ValueError('selected_model_required')
    mode = next(mode for mode, selected in MODELS.items() if model == selected)
    provider = PROVIDERS[mode]
    if free_tier_confirmed is not True:
        raise ValueError('free_tier_confirmation_required')
    if not valid_key(provider, key):
        raise ValueError('provider_key_required')
    # Caller must use an account with no paid billing enabled. Never infer that
    # from the key/model name, and never report a measured cost of zero.
    # Gemma rejects reasoning_effort ("Thinking budget is not supported").
    effort = 'low' if mode in {'groq_oss120', 'groq_oss20'} else None if mode == 'google_gemma' else 'none'
    payload = dict(model=model, messages=messages, temperature=0,
        max_tokens=1000, stream=False, response_format={'type': 'json_object'})
    if effort is not None:
        payload['reasoning_effort'] = effort
    # Groq's Cloudflare blocks the default Python-urllib User-Agent (HTTP 403, error 1010).
    req = Request(ENDPOINTS[provider], data=json.dumps(payload).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer '+key,
        'User-Agent': 'ap-equivalence-study/1.0'})
    with build_opener(llm._NoRedirect()).open(req, timeout=60) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('response_size')
    result = json.loads(raw)
    if result.get('model') != model:
        raise ValueError('returned_model_mismatch')
    choice = result['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('incomplete_response')
    content = choice['message']['content']
    if mode == 'google_gemma':
        content = _strip_thought(content)
    return content, {
        'returned_model': result['model'], 'provider': provider,
        'usage': result.get('usage'), 'response_id': result.get('id'),
        'reasoning_effort': effort, 'cost_usd': None,
        'system_fingerprint': result.get('system_fingerprint'),
        'provider_created_at': result.get('created'),
        'model_revision': None, 'model_revision_status': 'not_exposed_by_api',
        'temperature_requested': 0,
        'temperature_documented_effective': 1e-8 if provider == 'groq' else None,
        'temperature_observed': None, 'max_output_tokens_requested': 1000,
        'cost_source': 'not_reported_by_provider'}


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


def annotate(items, mode, key=None, free_tier_confirmed=False, preview=False, repeat_index=1, repeat_count=1):
    if mode not in MODES:
        raise ValueError('invalid_mode')
    repetition = repetition_context(repeat_index, repeat_count)
    request_started_at = utc_now()
    cloud = mode in MODELS
    provider = PROVIDERS.get(mode)
    config = capabilities() if mode == 'qwen' else None
    confirmed = free_tier_confirmed is True
    preview = preview is True
    available = mode == 'off' or (not preview and (
        config['qwen']['available'] if config else valid_key(provider, key) and confirmed))
    requested = MODELS.get(mode) or (config['qwen']['model'] if config else None)
    calls = []
    halted = False
    for item_index, item in enumerate(items):
        if item.get('status') != 'unknown_drug':
            continue
        _, item['correction_suffix'] = name_and_suffix(item['original'])
        item['learned_suggestions'] = []
        item['suggestion_label'] = 'AI 미확인 후보'
        context = llm._context(item['original'])
        if mode == 'off' or context is None:
            continue
        if preview or not available or halted:
            reason = ('preview_no_requests' if preview else 'stopped_after_error' if halted
                else 'free_tier_not_confirmed' if cloud and not confirmed
                else 'missing_or_invalid_key' if cloud else 'worker_unavailable')
            calls.append(dict(status='blocked' if preview or halted or not confirmed and cloud else 'unavailable',
                reason=reason, invoked=False, elapsed_seconds=0, item_index=item_index,
                recorded_at_utc=utc_now(), requested_model=requested, **repetition))
            continue
        messages = llm._messages(context[0], context[2], sorted(set(alias_map.values())))
        prompt_hash = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        started = time.perf_counter()
        call = dict(status='error', invoked=True, prompt_hash=prompt_hash, requested_model=requested,
            item_index=item_index, prompt_version=PROMPT_VERSION, prompt_messages=messages,
            started_at_utc=utc_now(), temperature_requested=0 if cloud or config['qwen'].get('backend') != 'mlx' else None,
            max_output_tokens_requested=1000 if cloud else 300,
            model_revision=None, model_revision_status='not_verified',
            fresh_conversation=True, application_response_cache=False, seed_requested=None,
            **repetition)
        try:
            output, meta = _qwen(messages) if mode == 'qwen' else _cloud(messages, requested, key, confirmed)
            call.update(meta)
            call['raw_response'] = output
            parsed = json.loads(output)
            if not isinstance(parsed, dict) or parsed.get('status') not in {'candidate_found', 'unknown'} or not isinstance(parsed.get('candidates'), list):
                raise ValueError('invalid_response')
            candidates = llm.validate_response(output, item['original'])
            if parsed['status'] == 'candidate_found' and not candidates:
                raise ValueError('invalid_candidates')
            item['learned_suggestions'] = candidates
            call.update(status='success', candidate_count=len(candidates), candidate_names=[c['drug'] for c in candidates])
        except Exception as exc:
            # Never retry, fall back, or expose provider error bodies/credentials.
            call['error_type'] = type(exc).__name__
            if isinstance(exc, HTTPError):
                call['http_status'] = exc.code
            halted = True
        call['completed_at_utc'] = utc_now()
        call['elapsed_seconds'] = round(time.perf_counter()-started, 3)
        calls.append(call)
    return dict(protocol=PROTOCOL, audit_version=AUDIT_VERSION,
        request_started_at_utc=request_started_at, request_completed_at_utc=utc_now(),
        repetition=repetition, repetition_policy='separate_stateless_requests_max_3',
        cost_policy=COST_POLICY, mode=mode, ai_feature='llm_name_candidates',
        ai_available=available, preview=preview,
        free_tier_confirmed=confirmed if cloud else None,
        billing_verification='researcher_attestation_not_provider_verified' if cloud else None,
        provider=provider, ai_invocation_count=sum(c['invoked'] for c in calls),
        ai_candidate_count=sum(len(i.get('learned_suggestions', [])) for i in items),
        ai_success_count=sum(c['status'] == 'success' for c in calls),
        ai_elapsed_seconds=round(sum(c['elapsed_seconds'] for c in calls), 3),
        requested_model=requested, prompt_version=PROMPT_VERSION, calls=calls,
        automatic_retry=False, paid_fallback=False, cloud_max_tokens=1000,
        app_commit=os.getenv('RENDER_GIT_COMMIT', 'local'))
