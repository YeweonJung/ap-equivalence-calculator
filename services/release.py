"""Public reproducibility metadata; contains no prescription data or credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '2026.09.29-paper-references-plain-excel'


def metadata():
    from services.feedback_store import configured
    from services.feedback_learning import enabled, MODEL_VERSION
    root = Path(__file__).resolve().parents[1]
    return {'version': VERSION, 'commit': os.getenv('RENDER_GIT_COMMIT', ''),
            'name_llm_enabled': False,
            'name_llm_backend': None,
            'name_llm_worker_online': False,
            'name_retrieval': 'disabled',
            'name_retrieval_channels': [],
            'name_ranker_enabled': False, 'automatic_confirmation_enabled': False,
            'feedback_configured': configured(), 'automatic_training_enabled': enabled(),
            'feedback_learning_model': MODEL_VERSION, 'feedback_learning_scope': 'review_suggestions_only',
            'name_retrieval_fallback_channels': [],
            'antidepressant_names_sha256': hashlib.sha256((root / 'lookup/antidepressant_names.json').read_bytes()).hexdigest(),
            'injection_names_sha256': hashlib.sha256((root / 'lookup/injection_product_names.json').read_bytes()).hexdigest(),
            'lookup_sha256': hashlib.sha256((root / 'lookup/master_lookup.csv').read_bytes()).hexdigest(),
            'anchors_sha256': hashlib.sha256((root / 'lookup/equivalence_anchors.csv').read_bytes()).hexdigest()}
