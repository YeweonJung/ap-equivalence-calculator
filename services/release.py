"""Public reproducibility metadata; contains no prescription data or credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '2026.09.21-candidate-retrieval-short-alias-manual'


def metadata():
    from services.manual_suggestions import SERVING_CHANNELS, SERVING_VERSION
    root = Path(__file__).resolve().parents[1]
    return {'version': VERSION, 'commit': os.getenv('RENDER_GIT_COMMIT', ''),
            'name_retrieval': SERVING_VERSION if os.getenv('NAME_RETRIEVAL_ENABLED', '1') != '0' else 'legacy-baseline',
            'name_retrieval_channels': list(SERVING_CHANNELS) if os.getenv('NAME_RETRIEVAL_ENABLED', '1') != '0' else ['osa'],
            'name_ranker_enabled': False, 'automatic_confirmation_enabled': False,
            'name_retrieval_fallback_channels': ['short_registered_alias'] if os.getenv('NAME_RETRIEVAL_ENABLED', '1') != '0' else [],
            'lookup_sha256': hashlib.sha256((root / 'lookup/master_lookup.csv').read_bytes()).hexdigest(),
            'anchors_sha256': hashlib.sha256((root / 'lookup/equivalence_anchors.csv').read_bytes()).hexdigest()}
