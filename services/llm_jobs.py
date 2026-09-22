"""Bounded ephemeral queue shared by Render workers; no prescriptions or doses."""
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time


def connect():
    path = os.getenv('NAME_LLM_QUEUE_PATH', str(Path(tempfile.gettempdir()) / 'ap-llm-jobs.sqlite3'))
    db = sqlite3.connect(path, timeout=3)
    db.execute('PRAGMA secure_delete=ON')
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT, result TEXT, status TEXT, expires REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS worker (id INTEGER PRIMARY KEY, seen REAL)')
    db.execute('DELETE FROM jobs WHERE expires < ?', (time.time(),))
    db.commit()
    return db


def heartbeat():
    with closing(connect()) as db, db:
        db.execute('INSERT OR REPLACE INTO worker VALUES (1, ?)', (time.time(),))


def online():
    with closing(connect()) as db:
        row = db.execute('SELECT seen FROM worker WHERE id=1').fetchone()
    return bool(row and time.time()-row[0] < 20)


def submit(messages, ttl=90):
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT seen FROM worker WHERE id=1').fetchone()
        if not row or time.time()-row[0] >= 20:
            return None
        if db.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0] >= 4:
            return None
        job_id = secrets.token_hex(16)
        db.execute('INSERT INTO jobs VALUES (?, ?, NULL, ?, ?)',
                   (job_id, json.dumps(messages), 'pending', time.time()+ttl))
        return job_id


def claim():
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR REPLACE INTO worker VALUES (1, ?)', (time.time(),))
        row = db.execute("SELECT id,payload FROM jobs WHERE status='pending' ORDER BY expires LIMIT 1").fetchone()
        if not row:
            return None
        db.execute("UPDATE jobs SET status='running' WHERE id=?", (row[0],))
        return dict(id=row[0], messages=json.loads(row[1]))


def complete(job_id, result):
    with closing(connect()) as db, db:
        changed = db.execute("UPDATE jobs SET result=?, payload=NULL, status='done' WHERE id=? AND status='running'",
                             (result, job_id)).rowcount
        return bool(changed)


def take(job_id):
    with closing(connect()) as db, db:
        row = db.execute("SELECT result FROM jobs WHERE id=? AND status='done'", (job_id,)).fetchone()
        if not row:
            return None
        db.execute('DELETE FROM jobs WHERE id=?', (job_id,))
        return row[0]


def discard(job_id):
    with closing(connect()) as db, db:
        db.execute('DELETE FROM jobs WHERE id=?', (job_id,))


def infer(messages):
    job_id = submit(messages)
    if not job_id:
        return '{"status":"unknown","candidates":[]}'
    deadline = time.monotonic()+85
    try:
        while time.monotonic() < deadline:
            result = take(job_id)
            if result is not None:
                return result
            time.sleep(.25)
        return '{"status":"unknown","candidates":[]}'
    finally:
        discard(job_id)
