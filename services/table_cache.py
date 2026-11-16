"""Start-up cache for name tables built from the large lookup files.

Building the name tables from lookup/*.json takes about 2 s at every start. The finished tables are
pickled once; the cache key covers the content of every input file (SHA-256) and the code that builds
them, so any change to a lookup file or to the building module rebuilds the tables. A missing,
unreadable or unwritable cache only means the tables are built as before.
"""
import hashlib
import os
import pickle
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get('APP_TABLE_CACHE', ROOT / '.cache' / 'tables'))
_VERSION = b'1'


def key(paths):
    digest = hashlib.sha256(_VERSION)
    for path in sorted(Path(p) for p in paths):
        digest.update(str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path).encode())
        digest.update(path.read_bytes() if path.exists() else b'<missing>')
    return digest.hexdigest()


def load(name, paths):
    """(tables or None, key)."""
    if os.environ.get('APP_TABLE_CACHE') == 'off':
        return None, ''
    try:
        cache_key = key(paths)
        with open(CACHE_DIR / f'{name}-{cache_key}.pkl', 'rb') as stream:
            return pickle.load(stream), cache_key
    except Exception:
        return None, locals().get('cache_key', '')


def save(name, cache_key, tables):
    if not cache_key:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for old in CACHE_DIR.glob(f'{name}-*.pkl'):
            old.unlink(missing_ok=True)
        handle, temp = tempfile.mkstemp(dir=CACHE_DIR, suffix='.tmp')
        with os.fdopen(handle, 'wb') as stream:
            pickle.dump(tables, stream, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(temp, CACHE_DIR / f'{name}-{cache_key}.pkl')
    except Exception:
        pass
