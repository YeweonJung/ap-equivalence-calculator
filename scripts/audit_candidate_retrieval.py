"""Read-only baseline audit; run before implementing experimental retrieval."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ranker_experiment import load_rows
from services.drug_suggestions import generate_candidates
from services.name_dictionary import normalize_name, name_and_suffix, registry
from services.name_distance import compare_letters


def main():
    rows = [r for r in load_rows(ROOT) if r['split'] == 'test']
    known = [r for r in rows if r['target_key'] is not None]
    pools = {r['id']: generate_candidates(r['original'], 20) for r in rows}
    failures = []
    for row in known:
        if not any(c['target_key'] == row['target_key'] for c in pools[row['id']]):
            query = normalize_name(name_and_suffix(row['original'])[0])
            expected = normalize_name(row['origin_alias'])
            failures.append(dict(**row, query=query, query_length=len(query),
                first_rejection='drug_suggestions.generate_candidates: not 3 <= len(query) <= 40',
                counterfactual_comparison=compare_letters(query, expected)))
    paths = [p for folder in ('services', 'lookup', 'models', 'tests', 'static', 'templates')
             for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / 'app.py', ROOT / 'data/name_ranker/synthetic.jsonl',
              ROOT / 'data/name_ranker/evaluation.json']
    report = dict(total=len(rows), known=len(known),
        recall_hits={str(k): sum(any(c['target_key'] == r['target_key'] for c in pools[r['id']][:k])
                                for r in known) for k in (1, 3, 5, 10, 20)},
        failures=failures,
        original_file_sha256={str(p.relative_to(ROOT)).replace('\\', '/'):
                              hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})
    output = ROOT / 'data/candidate_retrieval'
    output.mkdir(exist_ok=True)
    destination = output / 'phase1_audit.json'
    if destination.exists():
        raise RuntimeError('Preserve the pre-change audit; do not overwrite it')
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'original_file_sha256'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
