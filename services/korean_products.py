"""Exact public product labels; never guess a brand, strength or interval."""
import json
from pathlib import Path
import re
import unicodedata

CATALOG = json.loads((Path(__file__).resolve().parents[1] /
                      'lookup/korean_public_products.json').read_text(encoding='utf-8'))
ALIASES = {}
for record in CATALOG['products']:
    for alias in record['aliases']:
        key = unicodedata.normalize('NFKC', alias).casefold()
        if key in ALIASES and ALIASES[key]['normalized'] != record['normalized']:
            raise ValueError('Conflicting public product label: ' + alias)
        ALIASES[key] = record
PATTERN = re.compile(r'^(?:' + '|'.join(re.escape(a) for a in sorted(ALIASES, key=len, reverse=True)) + r')(?=$|\s)', re.I)


def normalize_product(text):
    normalized = unicodedata.normalize('NFKC', str(text))
    match = PATTERN.match(normalized)
    if not match:
        return text, {}
    record = ALIASES[match.group().casefold()]
    return record['normalized'] + normalized[match.end():], {
        'recognized_product': record['name'],
        'product_name_source': CATALOG['source'],
        'product_name_checked_on': CATALOG['checked_on'],
        'calculation_note': f"심평원 공개 제품명 일치 ({record['code']}): 주성분 함량 {record['dose_mg']:g} mg 사용; 포장·염 함량 중복 제외",
    }
