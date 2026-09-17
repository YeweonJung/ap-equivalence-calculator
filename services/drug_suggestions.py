"""오타 후보만 제시합니다. 사용자 선택 전 성분/용량을 확정하지 않습니다."""
import re
import unicodedata
from difflib import SequenceMatcher

from services.parser import alias_map


def compact(value):
    return re.sub(r'[^a-z가-힣]', '', unicodedata.normalize('NFKC', value).casefold())


def suggest_drugs(original, limit=3):
    # 이름 다음의 용량·빈도 원문을 그대로 유지할 수 있는 경우만 제안합니다.
    dose_start = re.search(r'[+-]?(?:\d|\.\d)', original)
    if not dose_start:
        return []
    prefix = original[:dose_start.start()]
    query = compact(prefix)
    if len(query) < 3 or len(query) > 40:
        return []
    # 추정 오타/축약을 재차 비교 대상으로 삼지 않고 제품명과 정식 성분명 우선.
    from pathlib import Path
    import csv
    source_file = Path(__file__).resolve().parents[1] / 'lookup/drug_alias_sources.csv'
    kinds = {}
    if source_file.exists():
        with source_file.open(encoding='utf-8-sig', newline='') as stream:
            kinds = {r['alias']: r['kind'] for r in csv.DictReader(stream)}
    by_drug = {}
    for alias, drug in alias_map.items():
        candidate = compact(alias)
        if len(candidate) < 3 or kinds.get(alias) in {'hypothesized_typo', 'preserved_user'}:
            continue
        korean = bool(re.search('[가-힣]', query))
        if korean != bool(re.search('[가-힣]', candidate)):
            continue
        if korean:
            left, right = (unicodedata.normalize('NFD', word) for word in (query, candidate))
        else:
            left, right = query, candidate
        score = SequenceMatcher(None, left, right).ratio() * 100
        if score < 70:
            continue
        previous = by_drug.get(drug)
        if previous is None or score > previous['score']:
            by_drug[drug] = dict(alias=alias, drug=drug, score=round(score, 1),
                                 replacement=alias + ' ' + original[dose_start.start():])
    return sorted(by_drug.values(), key=lambda value: (-value['score'], value['drug']))[:limit]
