"""One file calculation at a time on the server.

The hosted server has 512 MB. One large upload fits; three at once ran it out of memory and every
request failed (measured 2026-11-19). Uploads therefore queue: each waits for the one before it.
The lock is a file lock, so it holds across gunicorn worker processes and threads.
"""
import os
import tempfile
import time
from contextlib import contextmanager

try:
    import fcntl
except ImportError:          # Windows development machine: no queue needed
    fcntl = None

LOCK_PATH = os.path.join(tempfile.gettempdir(), 'ap_equivalence_heavy.lock')
WAIT_SECONDS = 600
BUSY_MESSAGE = '다른 연구자의 파일을 계산하고 있어 기다렸지만 차례가 오지 않았습니다. 몇 분 뒤 다시 올려 주세요.'


@contextmanager
def one_at_a_time(wait=WAIT_SECONDS):
    if fcntl is None:
        yield
        return
    handle = open(LOCK_PATH, 'a+')
    try:
        deadline = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise ValueError(BUSY_MESSAGE)
                time.sleep(0.3)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        handle.close()
