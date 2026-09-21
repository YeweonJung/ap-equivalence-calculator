"""Descriptive stress ablations; never selects or changes the locked policy."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_candidate_retrieval import OUT, VARIANTS, evaluate, dump, sha, guarded_inputs
from services.candidate_retrieval import retrieve


def main():
    guarded_inputs()
    lock = json.loads((OUT / 'policy_lock.json').read_text())
    if sha(ROOT / 'services/candidate_retrieval.py') != lock['implementation_sha256']:
        raise ValueError('Frozen implementation changed')
    rows = [json.loads(line) for line in (OUT / 'stress.jsonl').read_text(encoding='utf-8').splitlines()]
    config = json.loads((ROOT / 'models/name_ranker/config.json').read_text())
    reports = {}
    for name, channels in VARIANTS.items():
        reports[name] = evaluate(rows, lambda original, limit: retrieve(original, limit, channels=channels),
                                 None, config['baseline_policy'])
    dump(OUT / 'stress_channels.json', dict(selection_allowed=False, selected=lock['selected'],
        stress_sha256=sha(OUT / 'stress.jsonl'), results=reports))
    print(json.dumps({k: v['metrics'] for k, v in reports.items()}, indent=2))


if __name__ == '__main__':
    main()
