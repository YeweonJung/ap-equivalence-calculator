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


BY_CODE = {record['code']: record for record in CATALOG['products']}


def product_by_code(value):
    """The public catalogue entry for a 9-digit insurance (EDI) product code, or None."""
    digits = re.sub(r'\D', '', unicodedata.normalize('NFKC', str(value)).split('.')[0])
    return BY_CODE.get(digits.zfill(9)) if digits else None


def normalize_product(text):
    normalized = unicodedata.normalize('NFKC', str(text))
    match = PATTERN.match(normalized)
    if not match:
        return text, {}
    record = ALIASES[match.group().casefold()]
    rest = normalized[match.end():]
    if record.get('dose_mg'):
        # The product name already fixes the strength; the same strength written again is not a second dose.
        rest = re.sub(r'(?<![\d.])' + re.escape(f"{record['dose_mg']:g}") + r'(?:\.0+)?\s*(?:mg|㎎)(?![a-z])', ' ', rest, count=1, flags=re.I)
    return record['normalized'] + rest, {
        'recognized_product': record['name'],
        'product_name_source': CATALOG['source'],
        'product_name_checked_on': CATALOG['checked_on'],
        'calculation_note': f"심평원 공개 제품명 일치 ({record['code']}): 주성분 함량 {record['dose_mg']:g} mg 사용; 포장·염 함량 중복 제외",
    }
