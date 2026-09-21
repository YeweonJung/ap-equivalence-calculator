"""Portable source preservation checks across the explicitly reviewed app integration."""
import hashlib
import json


def normalized_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def verify_integration(root):
    manifest = json.loads((root / 'data/candidate_retrieval/integration_manifest.json').read_text())
    changed = [name for name, digest in manifest['expected_source_sha256_lf'].items()
               if normalized_sha(root / name) != digest]
    if changed:
        raise ValueError('Protected source changed: ' + ', '.join(changed))
    return manifest
