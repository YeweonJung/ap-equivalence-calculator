"""Public reproducibility metadata; contains no prescription data or credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '2026.09.28-injection-aliases'


def metadata():
    from services.feedback_store import configured
    root = Path(__file__).resolve().parents[1]
    return {'version': VERSION, 'commit': os.getenv('RENDER_GIT_COMMIT', ''),
            'name_llm_enabled': False,
            'name_llm_backend': None,
            'name_llm_worker_online': False,
            'name_retrieval': 'disabled',
            'name_retrieval_channels': [],
            'name_ranker_enabled': False, 'automatic_confirmation_enabled': False,
            'feedback_configured': configured(), 'automatic_training_enabled': False,
            'name_retrieval_fallback_channels': [],
            'lookup_sha256': hashlib.sha256((root / 'lookup/master_lookup.csv').read_bytes()).hexdigest(),
            'anchors_sha256': hashlib.sha256((root / 'lookup/equivalence_anchors.csv').read_bytes()).hexdigest()}
