"""Consent-only instance learning for review suggestions, never drug resolution."""
import os
import threading
import time
from collections import defaultdict, Counter

from services import feedback_store
from services.name_dictionary import normalize_name, name_and_suffix, dictionary_version, registry, formulation_conflict
from services.parser import alias_map

MODEL_VERSION = 'confirmed-correction-memory-v1'
_lock = threading.Lock()
_cache = {}


def enabled():
    return feedback_store.configured() and os.getenv('FEEDBACK_LEARNING_ENABLED', '1') == '1'


def invalidate():
    with _lock:
        _cache.clear()


def train(records):
    """Fit an exact-name empirical model from validated, consented examples."""
    groups = defaultdict(Counter)
    version = dictionary_version()
    for record in records:
        if (record.get('eligible_for_training') is not True or
                record.get('user_confirmed_name_only') is not True or
                record.get('learning_consent') is not True or
                record.get('dictionary_version') != version):
            continue
        name, alias = record.get('name_token'), record.get('selected_alias')
        if not isinstance(name, str) or not isinstance(alias, str):
            continue
        from services.feedback_api import safe_token
        if not safe_token(name) or alias not in alias_map or alias_map[alias] != record.get('selected_drug'):
            continue
        if name.casefold() in alias_map:
            continue  # Corrections cannot replace a registered name.
        groups[normalize_name(name)][alias] += 1
    return dict(groups)


def model():
    key = (os.getenv('FEEDBACK_DATABASE_URL'), os.getenv('FEEDBACK_SQLITE_PATH'), dictionary_version())
    with _lock:
        if _cache.get('key') == key and time.monotonic() < _cache.get('expires', 0):
            return _cache['model']
        fitted = train(feedback_store.training_records())
        _cache.update(key=key, model=fitted, expires=time.monotonic() + 60)
        return fitted


def suggestions(original):
    if not enabled():
        return []
    name, _ = name_and_suffix(original)
    from services.feedback_api import safe_token
    if not safe_token(name):
        return []
    try:
        votes = model().get(normalize_name(name), {})
        registered = registry()
        targets = {registered[a]['target_key'] if a in registered else alias_map[a] for a in votes}
        if len(targets) != 1:
            return []  # Any conflicting ingredient/product remains unresolved.
        alias = max(votes, key=lambda a: (votes[a], a))
        record = registered.get(alias, {'drug': alias_map[alias], 'route': 'unknown', 'profile': ''})
        if formulation_conflict(original, record):
            return []
        return [dict(alias=alias, drug=alias_map[alias], evidence_count=sum(votes.values()),
                     model_version=MODEL_VERSION, auto_accepted=False, confirmed_drug=None,
                     needs_review=True, prediction_source='confirmed_correction_memory')]
    except Exception:
        # Optional learner/storage failure never prevents parsing or exposes input.
        return []
