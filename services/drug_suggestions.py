"""Character-level candidates. Selection is required before conversion."""
import re
import unicodedata
from services.parser import alias_map
from services.name_distance import compare_letters, BRANDS



def compact(value):
    return re.sub(r'[^a-z가-힣]', '', unicodedata.normalize('NFKC', value).casefold())


def baseline_suggestions(original, limit=3):
    dose_start = re.search(r'[+-]?(?:\d|\.\d)', original)
    if not dose_start:
        return []
    prefix = original[:dose_start.start()]
    # Preserve formulation tokens as well as the complete dose/schedule suffix.
    name = re.sub(r'\s+(?:XR|ER|SR|IR|LAI|depot|서방정|서방|주사)\b.*$', '', prefix, flags=re.I).strip()
    query = compact(name)
    if not 3 <= len(query) <= 40:
        return []
    korean = bool(re.search('[가-힣]', query))
    by_alias = []
    for alias, drug in alias_map.items():
        candidate = compact(alias)
        if len(candidate) < 3 or korean != bool(re.search('[가-힣]', candidate)):
            continue
        if not korean and alias not in BRANDS and alias != drug and not alias.startswith('invega '):
            continue
        comparison = compare_letters(query, candidate)
        allowed = 1 if len(query) < 6 else 2 if len(query) < 12 else 3
        if comparison['distance'] > allowed or comparison['score'] < (60 if korean else 70):
            continue
        labels = {'insert':'삽입', 'delete':'삭제', 'replace':'교체', 'transpose':'순서 교환'}
        explanation = '; '.join(f"{e['position']}번째 {labels[e['operation']]}: {e['source'] or '∅'} → {e['target'] or '∅'}" for e in comparison['edits'])
        by_alias.append(dict(alias=alias, drug=drug, **comparison, comparison_input=query,
            explanation=explanation or '띄어쓰기·문장부호 정규화',
            replacement=alias + ' ' + original[len(name):].lstrip()))
    # Keep different depot brands separate, even when the active ingredient agrees.
    by_alias.sort(key=lambda v: (-v['score'], v['distance'], v['alias']))
    return by_alias[:limit]


def generate_candidates(original, limit=20):
    """Same distance/filter policy as baseline, also accepts a name without a dose."""
    from services.name_dictionary import name_and_suffix, normalize_name, records
    name, suffix = name_and_suffix(original)
    query = normalize_name(name)
    if not 3 <= len(query) <= 40:
        return []
    korean = bool(re.search('[가-힣]', query))
    result = []
    for record in records():
        candidate = normalize_name(record['alias'])
        if korean != bool(re.search('[가-힣]', candidate)):
            continue
        if abs(len(query)-len(candidate)) > (1 if len(query)<6 else 2 if len(query)<12 else 3):
            continue
        comparison = compare_letters(query, candidate)
        allowed = 1 if len(query)<6 else 2 if len(query)<12 else 3
        if comparison['distance']>allowed or comparison['score']<(60 if korean else 70):
            continue
        labels={'insert':'삽입','delete':'삭제','replace':'교체','transpose':'순서 교환'}
        explanation='; '.join(f"{e['position']}번째 {labels[e['operation']]}: {e['source'] or '∅'} → {e['target'] or '∅'}" for e in comparison['edits'])
        result.append(dict(**record, **comparison, comparison_input=query,
            explanation=explanation or '띄어쓰기·문장부호 정규화',
            replacement=record['alias']+suffix))
    return sorted(result,key=lambda v:(-v['score'],v['distance'],v['alias']))[:limit]


def suggest_drugs(original, limit=3):
    """Opt-in, approved model only. Default behavior remains byte-for-byte baseline."""
    import os
    if os.getenv('NAME_RANKER_ENABLED') == '1':
        from services.name_ranker import load_ranker, review_name
        model = load_ranker()
        if model and model['metadata'].get('production_enabled') is True:
            return review_name(original, model=model)['candidates'][:limit]
    return baseline_suggestions(original, limit)
