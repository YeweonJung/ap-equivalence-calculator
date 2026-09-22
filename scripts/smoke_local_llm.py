"""Run synthetic cases against the local app; never use patient prescriptions."""
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def post(text):
    started = time.monotonic()
    request = Request('http://127.0.0.1:5055/api/parse',
                      data=json.dumps({'text': text}).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=180) as response:
        result = json.load(response)
    return result, round(time.monotonic() - started, 2)


def main():
    report = []
    for text in ('aripiprazold 2mg', '리쓰페리도오온 2mg BID',
                 '쿠에티아피이인 25mg QHS', 'zzzzzz 2mg', '얀센 주사제 150mg'):
        result, seconds = post(text)
        item = result['items'][0]
        candidates = item.get('suggestions', [])
        assert item['drug'] is None and item['conversions'] == [], text
        assert all(not c.get('auto_accepted') for c in candidates), text
        row = dict(input=text, seconds=seconds, status=item['status'],
                   candidates=[dict(drug=c['drug'], source=c.get('source', 'retrieval'))
                               for c in candidates])
        if any(c.get('source') == 'llm' for c in candidates):
            selected = next(c for c in candidates if c.get('source') == 'llm')
            confirmed, _ = post(selected['replacement'])
            row['after_selection'] = dict(drug=confirmed['items'][0]['drug'],
                daily_dose_mg=confirmed['items'][0]['daily_dose_mg'])
            assert row['after_selection']['drug'] == selected['drug']
        report.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    output = Path(__file__).resolve().parents[1] / 'output/local_llm_smoke.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
