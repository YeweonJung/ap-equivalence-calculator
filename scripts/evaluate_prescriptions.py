"""Run locally: python scripts/evaluate_prescriptions.py gold.jsonl --output report.json."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.evaluation import evaluate
from services.release import metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gold', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--predictions', type=Path, help='Optional offline JSONL: id, items (same frame schema); never calls a model')
    parser.add_argument('--external-api-cost-usd', type=float)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.gold, args.predictions) if p}:
        raise ValueError('Output must not overwrite the gold or predictions file')
    raw = args.gold.read_bytes()
    cases = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    predictor = None
    if args.predictions:
        rows = [json.loads(line) for line in args.predictions.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        predictions = {r['id']:r['items'] for r in rows}
        if len(predictions) != len(rows) or set(predictions) != {r['id'] for r in cases}:
            raise ValueError('Offline prediction IDs must match the gold set exactly')
        iterator = iter(cases)
        def offline_predictor(_text):
            return predictions[next(iterator)['id']]
        predictor = offline_predictor
    result = evaluate(cases, predictor)
    result.update(dataset_sha256=hashlib.sha256(raw).hexdigest(), release=metadata(),
                  python=platform.python_version(), platform=platform.platform(),
                  dataset_kind='synthetic_development' if all(r.get('synthetic') is True for r in cases) and cases else 'user_labeled_not_independently_validated')
    if args.external_api_cost_usd is not None:
        import math
        if not math.isfinite(args.external_api_cost_usd) or args.external_api_cost_usd < 0:
            raise ValueError('Cost must be finite and nonnegative')
        result['external_api_cost_usd'] = args.external_api_cost_usd
        result['cost_source'] = 'user_reported'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(output=str(args.output), cases=len(cases), unit_accuracy=result['unit_accuracy'], overall=result['overall']), ensure_ascii=False))


if __name__ == '__main__':
    main()
