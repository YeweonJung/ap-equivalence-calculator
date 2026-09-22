"""Connect a local Ollama model to Render using outbound authenticated requests."""
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from services.llm_candidates import _ollama, _NoRedirect


def main():
    config = Path(__file__).resolve().parent / '.env.llm-worker'
    if config.exists():
        for line in config.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                if key in {'NAME_LLM_WORKER_KEY', 'NAME_LLM_SITE_URL', 'NAME_LLM_MODEL'}:
                    os.environ[key] = value
    base = os.environ['NAME_LLM_SITE_URL'].rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Worker requires a fixed HTTPS site URL')
    key = os.environ['NAME_LLM_WORKER_KEY']
    if len(key) < 32:
        raise ValueError('Worker key must be at least 32 characters')
    os.environ['NAME_LLM_URL'] = 'http://127.0.0.1:11434'
    os.environ['NAME_LLM_TIMEOUT_SECONDS'] = '75'
    os.environ.setdefault('NAME_LLM_MODEL', 'qwen2.5:7b')

    def call(path, data=None):
        req = Request(base+path, data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
        with build_opener(_NoRedirect()).open(req, timeout=20) as reply:
            raw = reply.read(32769)
            if len(raw) > 32768:
                raise ValueError('Oversized job')
            return json.loads(raw) if raw else None

    def keep_online():
        while True:
            try:
                call('/api/name-llm/heartbeat', {})
            except Exception:
                pass
            time.sleep(8)

    threading.Thread(target=keep_online, daemon=True).start()
    print('Local model worker started; outgoing HTTPS connection only.', flush=True)
    connected = False
    while True:
        try:
            job = call('/api/name-llm/jobs/next')
            if not connected:
                print('Connected to calculator.', flush=True)
                connected = True
            if job:
                try:
                    result = _ollama(job['messages'])
                except Exception:
                    result = '{"status":"unknown","candidates":[]}'
                call('/api/name-llm/jobs/'+job['id'], {'result': result})
                print('Completed an inference job.', flush=True)
            else:
                time.sleep(3)
        except Exception as exc:
            if connected:
                print('Connection interrupted; retrying ('+type(exc).__name__+').', flush=True)
            connected = False
            time.sleep(8)


if __name__ == '__main__':
    main()
