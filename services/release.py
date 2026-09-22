"""Public reproducibility metadata; contains no prescription data or credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '2026.09.23-longitudinal-v1'


def metadata():
    from services.llm_candidates import enabled
    llm_enabled = enabled()
    worker_online = False
    if llm_enabled and os.getenv('NAME_LLM_BACKEND') == 'worker':
        try:
            from services.llm_jobs import online
            worker_online = online()
        except Exception:
            pass
    from services.feedback_store import configured
    from services.manual_suggestions import SERVING_CHANNELS, SERVING_VERSION
    root = Path(__file__).resolve().parents[1]
    return {'version': VERSION, 'commit': os.getenv('RENDER_GIT_COMMIT', ''),
            'name_llm_enabled': llm_enabled,
            'name_llm_backend': os.getenv('NAME_LLM_BACKEND', 'ollama') if llm_enabled else None,
            'name_llm_worker_online': worker_online,
            'name_retrieval': SERVING_VERSION if os.getenv('NAME_RETRIEVAL_ENABLED', '1') != '0' else 'legacy-baseline',
            'name_retrieval_channels': list(SERVING_CHANNELS) if os.getenv('NAME_RETRIEVAL_ENABLED', '1') != '0' else ['osa'],
            'name_ranker_enabled': False, 'automatic_confirmation_enabled': False,
            'feedback_configured': configured(), 'automatic_training_enabled': False,
            'name_retrieval_fallback_channels': ['short_registered_alias'] if os.getenv('NAME_RETRIEVAL_ENABLED', '1') != '0' else [],
            'lookup_sha256': hashlib.sha256((root / 'lookup/master_lookup.csv').read_bytes()).hexdigest(),
            'anchors_sha256': hashlib.sha256((root / 'lookup/equivalence_anchors.csv').read_bytes()).hexdigest()}
