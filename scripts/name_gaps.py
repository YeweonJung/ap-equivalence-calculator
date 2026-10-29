"""Find medication names the app cannot recognize and register reviewed ones (no AI).

1) List gaps:   python scripts/name_gaps.py data.xlsx [more files...] --out gaps.csv
   Every cell of every sheet (or every line of a .txt) is parsed. Names still unknown after
   the dictionary and spelling correction are counted with an example and nearby candidates.
2) Review:      fill 등록할_성분 (e.g. lorazepam) and 분류 (antipsychotic, anxiolytic,
   mood_stabilizer, antidepressant, side_effect_management, other_non_antipsychotic) and 출처.
3) Register:    python scripts/name_gaps.py --apply gaps.csv
   Filled rows are added to lookup/name_supplement.json; empty rows are skipped.
Only drug names leave the input; IDs and other columns are never written.
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SUPPLEMENT = ROOT / 'lookup/name_supplement.json'
CLASSES = {'antipsychotic', 'anxiolytic', 'mood_stabilizer', 'antidepressant', 'side_effect_management',
           'stimulant', 'opioid_antagonist', 'other_non_antipsychotic'}
HEADER = ['미인식_이름', '건수', '예시_원문', '가까운_후보', '등록할_성분', '분류', '출처']


def cells(path):
    path = Path(path)
    if path.suffix.lower() == '.txt':
        yield from path.read_text(encoding='utf-8').splitlines()
        return
    import pandas as pd
    sheets = pd.read_excel(path, sheet_name=None, dtype=str) if path.suffix.lower() in ('.xlsx', '.xls') \
        else {'csv': pd.read_csv(path, dtype=str, encoding='utf-8-sig')}
    for df in sheets.values():
        for value in df.to_numpy().ravel():
            if isinstance(value, str) and re.search(r'[^\W\d_]{2,}', value):
                yield value


def gaps(paths):
    from services.frames import parse_frames
    from services.manual_suggestions import suggest_for_review
    from services.name_dictionary import name_and_suffix
    counts, examples = Counter(), {}
    for path in paths:
        for value in cells(path):
            for item in parse_frames(value):
                if item.get('status') != 'unknown_drug':
                    continue
                name = (name_and_suffix(item['original'])[0] or item['original']).strip()
                if not name or re.fullmatch(r'[\d\W_]+', name):
                    continue
                counts[name.casefold()] += 1
                examples.setdefault(name.casefold(), item['original'])
    rows = []
    for name, n in counts.most_common():
        near = ', '.join(dict.fromkeys(c['drug'] for c in suggest_for_review(examples[name], limit=3)))
        rows.append([name, n, examples[name], near, '', '', ''])
    return rows


def apply(path):
    catalog = json.loads(SUPPLEMENT.read_text(encoding='utf-8'))
    known = {a.casefold() for e in catalog['entries'] for a in e['alias']}
    from services.converter import lookup
    antipsychotics = set(lookup.source_drug)
    grouped, skipped = defaultdict(list), []
    with open(path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            name, ingredient, cls = row['미인식_이름'].strip().casefold(), row['등록할_성분'].strip().casefold(), row['분류'].strip()
            if not ingredient:
                continue
            if cls not in CLASSES or (cls == 'antipsychotic') != (ingredient in antipsychotics):
                skipped.append(f'{name}: 분류 확인 ({cls}, {ingredient})')
                continue
            if name in known:
                skipped.append(f'{name}: 이미 등록됨')
                continue
            grouped[(ingredient, cls, row.get('출처', '').strip() or '연구자 확인')].append(name)
    for (ingredient, cls, source), names in grouped.items():
        catalog['entries'].append({'alias': names, 'ingredient': ingredient, 'class': cls, 'kind': 'reviewed_gap',
                                   'source': source, 'seen_in': f'scripts/name_gaps.py {date.today().isoformat()}'})
    SUPPLEMENT.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'등록 {sum(map(len, grouped.values()))}개 이름 ({len(grouped)}개 성분)')
    for line in skipped:
        print('건너뜀 -', line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('files', nargs='*')
    parser.add_argument('--out', default='name_gaps.csv')
    parser.add_argument('--apply')
    args = parser.parse_args()
    if args.apply:
        apply(args.apply)
    else:
        rows = gaps(args.files)
        with open(args.out, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerows([HEADER] + rows)
        print(f'미인식 이름 {len(rows)}개 → {args.out}')
