"""Private, pending-review feedback. Never used directly by inference/training."""
import json
import os
import sqlite3
import time
from contextlib import contextmanager


def configured():
    return bool(os.getenv('FEEDBACK_SIGNING_KEY') and (
        os.getenv('FEEDBACK_DATABASE_URL') or
        (os.getenv('FEEDBACK_SQLITE_PATH') and not os.getenv('RENDER'))))


@contextmanager
def connection():
    url = os.getenv('FEEDBACK_DATABASE_URL')
    if url:
        import psycopg
        with psycopg.connect(url, connect_timeout=5) as db:
            yield db, '%s'
    else:
        if os.getenv('RENDER') or not os.getenv('FEEDBACK_SQLITE_PATH'):
            raise RuntimeError('Durable feedback storage is not configured')
        db = sqlite3.connect(os.environ['FEEDBACK_SQLITE_PATH'], timeout=5)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db, '?'
        finally:
            db.close()


def save(event_id, record):
    now = int(time.time())
    with connection() as (db, param):
        db.execute('CREATE TABLE IF NOT EXISTS medication_feedback '
                   '(event_id TEXT PRIMARY KEY, created_at BIGINT NOT NULL, payload TEXT NOT NULL)')
        if param == '%s':
            db.execute('LOCK TABLE medication_feedback IN SHARE ROW EXCLUSIVE MODE')
        db.execute(f'DELETE FROM medication_feedback WHERE created_at < {param}', (now - 180*86400,))
        if db.execute(f'SELECT event_id FROM medication_feedback WHERE event_id = {param}', (event_id,)).fetchone():
            db.commit()
            return 'already_saved'
        count = db.execute(f'SELECT COUNT(*) FROM medication_feedback WHERE created_at >= {param}', (now-3600,)).fetchone()[0]
        if count >= 500:
            raise OverflowError('Feedback rate limit')
        db.execute(f'INSERT INTO medication_feedback VALUES ({param}, {param}, {param})',
                   (event_id, now, json.dumps(record, ensure_ascii=False)))
        db.commit()
    return 'saved'
