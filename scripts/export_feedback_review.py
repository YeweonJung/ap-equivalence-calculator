"""Export pending corrections to a PRIVATE local file. Never marks data as training-ready."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.feedback_store import connection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with connection() as (db, param):
        db.execute(f'DELETE FROM medication_feedback WHERE created_at < {param}', (int(time.time())-180*86400,))
        rows = db.execute('SELECT event_id, created_at, payload FROM medication_feedback ORDER BY created_at').fetchall()
        db.commit()
    # Do not overwrite an earlier review/export; never print contents to the console.
    with args.output.open('x', encoding='utf-8') as out:
        for event_id, created_at, payload in rows:
            out.write(json.dumps(dict(event_id=event_id, created_at=created_at, **json.loads(payload)), ensure_ascii=False)+'\n')
    print(f'Exported {len(rows)} pending records. Human review is required before any training.')


if __name__ == '__main__':
    main()
