"""Exact ingredient exclusions with source classifications kept separately."""
import json
from pathlib import Path
from services.antidepressants import ALIASES as AD_ALIASES, INGREDIENTS as AD_INGREDIENTS

CATALOG = json.loads((Path(__file__).resolve().parents[1] /
                      'lookup/companion_medications.json').read_text(encoding='utf-8'))
SOURCE_ROWS = {r['ingredient']: r for r in CATALOG['drugs']}
CLASSES = dict.fromkeys(AD_INGREDIENTS, 'antidepressant')
CLASSES.update({r['ingredient']: r['drug_class'] for r in CATALOG['drugs'] if r['exclude']})
INGREDIENTS = frozenset(CLASSES)
CLASS_LABELS = {
    'mood_stabilizer': '기분조절제', 'antidepressant': '항우울제',
    'anxiolytic': '항불안제', 'stimulant': '각성제',
    'side_effect_management': '부작용처리약', 'opioid_antagonist': '오피오이드 길항제',
}
ALIASES = {**AD_ALIASES, **{name: name for name in INGREDIENTS}}
EXCLUSION_NOTE = '병용약물 제외: 항정신병약 환산값 0 (실제 복용량이 아님)'


def is_excluded(item):
    return item.get('status') == 'non_target' and item.get('drug') in INGREDIENTS


def exclusion_label(drug):
    return '항우울제 제외' if CLASSES.get(drug) == 'antidepressant' else '병용약물 제외'


def exclusion_basis(drug):
    source = SOURCE_ROWS.get(drug)
    suffix = f"; {CATALOG['source_file']} {source['source_cell']}; 원본 분류={source['source_group']}" if source else ''
    return exclusion_label(drug) + ': 항정신병약 환산값 0 (실제 복용량이 아님)' + suffix


def review_fields(drug):
    """Informational Review entries must not set needs_review or block totals."""
    return {'recognized_drug': drug, 'drug_group': CLASS_LABELS[CLASSES[drug]],
            'calculation': '배제 완료', 'equivalent_contribution': 0}
