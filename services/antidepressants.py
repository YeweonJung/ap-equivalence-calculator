"""Source-backed, local-only antidepressant exclusion dictionary.

Zero means zero contribution to antipsychotic equivalents, never zero drug dose.
No fuzzy matching, web calls, or antidepressant equivalence factors are used.
"""
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1] /
                      'lookup/antidepressant_names.json').read_text(encoding='utf-8'))
INGREDIENTS = frozenset(row['ingredient'] for row in CATALOG['drugs'])
ALIASES = {}
for row in CATALOG['drugs']:
    for name in [row['ingredient'], *row['aliases']]:
        ALIASES[name.casefold()] = row['ingredient']
        # Korean dosage-form suffixes are spelling variants, not new products.
        if all('가' <= char <= '힣' for char in name):
            for suffix in ('정', '캡슐', '서방정', '서방캡슐', '오디정'):
                ALIASES[name + suffix] = row['ingredient']

EXCLUSION_NOTE = '항우울제 제외: 항정신병약 환산값 0 (실제 복용량이 아님)'


def is_excluded(item):
    return item.get('status') == 'non_target' and item.get('drug') in INGREDIENTS
