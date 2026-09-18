"""Public reproducibility metadata; contains no prescription data or credentials."""
import hashlib
import os
from pathlib import Path

VERSION = '2026.09.18-character-review-cmd'


def metadata():
    root = Path(__file__).resolve().parents[1]
    return {'version': VERSION, 'commit': os.getenv('RENDER_GIT_COMMIT', ''),
            'lookup_sha256': hashlib.sha256((root / 'lookup/master_lookup.csv').read_bytes()).hexdigest(),
            'anchors_sha256': hashlib.sha256((root / 'lookup/equivalence_anchors.csv').read_bytes()).hexdigest()}
