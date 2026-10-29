"""Exact ingredient exclusions with source classifications kept separately."""
import json
import re
from pathlib import Path
from services.antidepressants import ALIASES as AD_ALIASES, INGREDIENTS as AD_INGREDIENTS

CATALOG = json.loads((Path(__file__).resolve().parents[1] /
                      'lookup/companion_medications.json').read_text(encoding='utf-8'))
SOURCE_ROWS = {r['ingredient']: r for r in CATALOG['drugs']}
CLASSES = dict.fromkeys(AD_INGREDIENTS, 'antidepressant')
CLASSES.update({r['ingredient']: r['drug_class'] for r in CATALOG['drugs'] if r['exclude']})
from services.name_supplement import OTHER_ALIASES, OTHER_CLASSES, CLASS_LABELS as SUPPLEMENT_LABELS
# Reviewed supplement names never reclassify a catalog ingredient.
CLASSES.update({k: v for k, v in OTHER_CLASSES.items() if k not in CLASSES})
INGREDIENTS = frozenset(CLASSES)
CLASS_LABELS = {
    'mood_stabilizer': '기분조절제', 'antidepressant': '항우울제',
    'anxiolytic': '항불안제', 'stimulant': '각성제',
    'side_effect_management': '부작용처리약', 'opioid_antagonist': '오피오이드 길항제',
    **SUPPLEMENT_LABELS,
}
ALIASES = {**OTHER_ALIASES, **AD_ALIASES, **{name: name for name in INGREDIENTS}}
EXCLUSION_NOTE = '병용약물 제외: 항정신병약 환산값 0 (실제 복용량이 아님)'


# PRN (as-needed) antipsychotic orders are not part of the regular daily dose:
# they contribute 0 and are reported, like companion-drug exclusions.
PRN_RE = re.compile(r'\b(?:prn|as\s+needed)\b|필요\s*시', re.I)
PRN_LABEL = 'PRN 제외'
PRN_BASIS = 'PRN(필요시) 처방 제외: 정규 일일 용량에 포함하지 않음 (항정신병약 환산값 0)'


def is_excluded(item):
    return item.get('status') == 'non_target' and (item.get('drug') in INGREDIENTS or bool(item.get('prn_excluded')))


def item_exclusion_label(item):
    return PRN_LABEL if item.get('prn_excluded') else exclusion_label(item.get('drug'))


def item_exclusion_basis(item):
    if item.get('unlisted'):
        return item.get('exclusion_basis') or exclusion_basis(item.get('drug'))
    return PRN_BASIS if item.get('prn_excluded') else exclusion_basis(item.get('drug'))


def exclusion_label(drug):
    if CLASSES.get(drug) == 'unlisted':
        return '사전 외 약물 0 처리'
    return '항우울제 제외' if CLASSES.get(drug) == 'antidepressant' else '병용약물 제외'


def exclusion_basis(drug):
    source = SOURCE_ROWS.get(drug)
    suffix = f"; {CATALOG['source_file']} {source['source_cell']}; 원본 분류={source['source_group']}" if source else ''
    return exclusion_label(drug) + ': 항정신병약 환산값 0 (실제 복용량이 아님)' + suffix


def review_fields(drug, prn=False):
    """Informational Review entries must not set needs_review or block totals."""
    if prn:
        return {'recognized_drug': drug, 'drug_group': PRN_LABEL, 'calculation': '배제 완료', 'equivalent_contribution': 0}
    return {'recognized_drug': drug, 'drug_group': CLASS_LABELS[CLASSES[drug]],
            'calculation': '배제 완료', 'equivalent_contribution': 0}
