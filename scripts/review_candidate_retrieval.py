"""Inspect frozen experimental retrieval locally, without conversion or logging."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.candidate_retrieval import review_retrieval
from services.name_ranker import load_ranker


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='Synthetic or de-identified name token only')
    parser.add_argument('--lr', action='store_true', help='Use existing local LR; fall back if unavailable')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'data/candidate_retrieval/policy_lock.json').read_text())
    print(json.dumps(review_retrieval(args.name, model=load_ranker() if args.lr else None,
                                    channels=lock['channels']), ensure_ascii=False, indent=2))
