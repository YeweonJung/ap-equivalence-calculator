"""Rebuild only source-anchored methods; preserve existing methods verbatim."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    anchors = list(csv.DictReader((ROOT / 'lookup/equivalence_anchors.csv').open(encoding='utf-8')))
    methods = {r['method_id'] for r in anchors}
    path = ROOT / 'lookup/master_lookup.csv'
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    lines = [line for line in lines if line.split(',')[0] not in methods]
    for method in sorted(methods):
        rows = [r for r in anchors if r['method_id'] == method]
        if len({r['drug'] for r in rows}) != len(rows):
            raise ValueError('Duplicate anchors')
        for source in rows:
            for target in rows:
                factor = float(target['anchor_dose_mg']) / float(source['anchor_dose_mg'])
                lines.append(f"{method},{source['drug']},{target['drug']},{factor:.16g}")
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    build()
