import io
import threading
import time

import pandas as pd
import pytest

import services.heavy_lock as heavy
from app import app


def test_calculations_run_one_at_a_time():
    order = []

    def job(name):
        with heavy.one_at_a_time():
            order.append(name + ' start'); time.sleep(0.3); order.append(name + ' end')

    threads = [threading.Thread(target=job, args=(n,)) for n in 'AB']
    [t.start() for t in threads]; [t.join() for t in threads]
    assert order[0].endswith('start') and order[1].endswith('end') and order[2].endswith('start')


def test_waiting_too_long_gives_a_message(monkeypatch):
    if heavy.fcntl is None:
        pytest.skip('no file locks on this platform')
    with heavy.one_at_a_time():
        result = {}

        def other():
            client = app.test_client()
            monkeypatch.setattr(heavy, 'WAIT_SECONDS', 0.5)
            with pytest.raises(ValueError) as error:
                with heavy.one_at_a_time(wait=0.5):
                    pass
            result['message'] = str(error.value)

        t = threading.Thread(target=other); t.start(); t.join()
    assert '다른 연구자' in result['message']


def test_parallel_uploads_all_finish():
    raw = io.BytesIO(); pd.DataFrame({'id': ['P1', 'P2'], 'med': ['olanzapine 5mg', 'risperidone 2mg']}).to_excel(raw, index=False)
    codes = []

    def post():
        codes.append(app.test_client().post('/upload', data={'file': (io.BytesIO(raw.getvalue()), 'a.xlsx'), 'dated': 'page'}).status_code)

    threads = [threading.Thread(target=post) for _ in range(3)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert codes == [200, 200, 200]
