"""Rebuild only source-anchored methods; preserve existing methods verbatim."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.evidence import METADATA_COLUMNS, pair_metadata


def build():
    anchors = list(csv.DictReader((ROOT / 'lookup/equivalence_anchors.csv').open(encoding='utf-8')))
    methods = {r['method_id'] for r in anchors}
    path = ROOT / 'lookup/master_lookup.csv'
    with path.open(encoding='utf-8-sig', newline='') as stream:
        output = [r for r in csv.DictReader(stream) if r['method_id'] not in methods]
    for method in sorted(methods):
        rows = [r for r in anchors if r['method_id'] == method]
        if len({r['drug'] for r in rows}) != len(rows):
            raise ValueError('Duplicate anchors')
        for source in rows:
            for target in rows:
                factor = float(target['anchor_dose_mg']) / float(source['anchor_dose_mg'])
                output.append(dict(method_id=method, source_drug=source['drug'], target_drug=target['drug'], factor=f'{factor:.16g}'))
    index = {(r['method_id'], r['drug']): r for r in anchors}
    for row in output:
        row.update(pair_metadata(row['method_id'], row['source_drug'], row['target_drug'], index))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['method_id', 'source_drug', 'target_drug', 'factor'] + METADATA_COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(output)


if __name__ == '__main__':
    build()
