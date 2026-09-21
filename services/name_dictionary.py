"""Read-only view of the existing dictionary; never changes conversion tables."""
import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from services.parser import alias_map
from services.name_distance import BRANDS
from services.lai_support import PRODUCTS


def normalize_name(value):
    return re.sub(r'[^a-z가-힣]', '', unicodedata.normalize('NFKC', str(value)).casefold())


def name_and_suffix(original):
    """Only isolate the name. Retain all numbers/schedule/formulation verbatim."""
    boundary = re.search(r'[+-]?(?:\d|\.\d)|\s+(?:XR|ER|SR|IR|LAI|depot|tablet|capsule|oral|injection|서방정|서방|주사|정제|캡슐)\b', original, re.I)
    end = boundary.start() if boundary else len(original)
    name = original[:end].strip()
    return name, original[len(original[:end].rstrip()):]


@lru_cache(maxsize=1)
def records():
    result = []
    for alias, drug in sorted(alias_map.items()):
        korean = bool(re.search('[가-힣]', alias))
        if len(normalize_name(alias)) < 3:
            continue
        if not korean and alias not in BRANDS and alias != drug and not alias.startswith('invega '):
            continue
        profile = next((value[1] for product, value in PRODUCTS.items()
                        if alias == product or alias == 'invega ' + product), '')
        kind = 'ingredient' if alias == drug else 'product' if alias in BRANDS or profile else 'registered_alias'
        # Generic ingredients can occur in more than one route: unknown is not oral.
        route = 'injection' if profile else 'oral' if alias in BRANDS else 'unknown'
        result.append(dict(alias=alias, drug=drug, kind=kind, route=route, profile=profile,
                           target_key=drug + '|' + (profile or 'non_product_specific')))
    return tuple(result)


def registry():
    return {row['alias']: row for row in records()}


def dictionary_version():
    content = json.dumps(records(), ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def explicit_route(text):
    oral = bool(re.search(r'\b(?:oral|tablet|capsule|po)\b|경구|정제|캡슐', text, re.I))
    injection = bool(re.search(r'\b(?:injection|injectable|lai|depot|im|iv|sc|pp[136]m)\b|주사|데포', text, re.I))
    return 'conflict' if oral and injection else 'oral' if oral else 'injection' if injection else 'unknown'


def formulation_conflict(text, record):
    route = explicit_route(text)
    if route == 'conflict':
        return True
    if route != 'unknown' and record['route'] != 'unknown' and route != record['route']:
        return True
    profiles = {s.upper() for s in re.findall(r'\bPP[136]M\b', text, re.I)}
    if profiles and (record['drug'] != 'paliperidone' or len(profiles) > 1):
        return True
    return bool(profiles and record['profile'] and record['profile'] not in profiles)
