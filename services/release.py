"""Public reproducibility metadata; contains no prescription data or credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '2026.10.31-stop-zero'


def metadata():
    from services.supplemented import POLICY_VERSION, PRIORITY
    from services.feedback_store import configured
    from services.feedback_learning import enabled, MODEL_VERSION
    root = Path(__file__).resolve().parents[1]
    from services.evidence import VERSION as evidence_version
    from services.result_status import POLICY_VERSION as review_policy
    return {'version': VERSION, 'commit': os.getenv('RENDER_GIT_COMMIT', ''),
            'review_policy': review_policy,
            'supplemented_policy': POLICY_VERSION, 'supplemented_case_methods': list(PRIORITY),
            'evidence_metadata_version': evidence_version,
            'evidence_grade_policy': 'not_assessed_no_inferred_GRADE',
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
            'companion_medications_sha256': hashlib.sha256((root / 'lookup/companion_medications.json').read_bytes()).hexdigest(),
            'injection_names_sha256': hashlib.sha256((root / 'lookup/injection_product_names.json').read_bytes()).hexdigest(),
            'korean_products_sha256': hashlib.sha256((root / 'lookup/korean_public_products.json').read_bytes()).hexdigest(),
            'lookup_sha256': hashlib.sha256((root / 'lookup/master_lookup.csv').read_bytes()).hexdigest(),
            'anchors_sha256': hashlib.sha256((root / 'lookup/equivalence_anchors.csv').read_bytes()).hexdigest()}
