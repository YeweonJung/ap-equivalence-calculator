"""Measure actual local inference with one synthetic misspelling."""
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.llm_candidates import _messages, validate_response
from services.parser import alias_map

payload = dict(model='qwen2.5:7b', stream=False, format='json', keep_alive='10m',
    messages=_messages('리쓰페리도오온', 'unknown', sorted(set(alias_map.values()))),
    options=dict(temperature=0, num_predict=300, num_ctx=2048))
request = Request('http://127.0.0.1:11434/api/chat',
    data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
started = time.monotonic()
try:
    with urlopen(request, timeout=300) as reply:
        data = json.load(reply)
except Exception as exc:
    print(type(exc).__name__, str(exc), flush=True)
    if hasattr(exc, 'read'):
        print(exc.read().decode(), flush=True)
    raise
result = dict(seconds=round(time.monotonic()-started,2),
    model=data.get('model'), message=data.get('message'),
    load_seconds=round(data.get('load_duration',0)/1e9,2),
    evaluation_seconds=round(data.get('eval_duration',0)/1e9,2),
    token_count=data.get('eval_count'),
    validated=validate_response(data['message']['content'], '리쓰페리도오온 2mg BID'))
out = Path(__file__).resolve().parents[1] / 'output/local_model_probe.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
