"""Local inspection only: no logging, confirmation, dose inference or conversion."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.name_ranker import review_name

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='De-identified medication name only')
    args = parser.parse_args()
    print(json.dumps(review_name(args.name), ensure_ascii=False, indent=2))
