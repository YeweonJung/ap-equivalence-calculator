"""Low-confidence fallback for registered two-syllable aliases; manual only.

This is a separate serving extension, not a change to the frozen experiment.
Mixed input is compared as typed: Latin letters are never silently translated.
"""
import re
import unicodedata

from services.name_dictionary import name_and_suffix
from services.name_distance import compare_letters
from services.name_features import levenshtein
from services.parser import alias_map

CHANNEL = 'short_registered_alias'


def short_alias_candidates(original):
    name, suffix = name_and_suffix(original)
    query = unicodedata.normalize('NFKC', name).casefold()
    # One trailing Latin character is tolerated only on two complete syllables.
    # Prefix sharing is weak evidence, so never use these for automatic decisions.
    if not re.fullmatch(r'[가-힣]{2}[a-z]?', query):
        return []
    matches = []
    for alias, drug in sorted(alias_map.items()):
        if not re.fullmatch(r'[가-힣]{2}', alias) or alias[0] != query[0]:
            continue
        if len(query) == 2 and levenshtein(unicodedata.normalize('NFD', query),
                unicodedata.normalize('NFD', alias)) > 1:
            continue
        comparison = compare_letters(query, alias)
        if comparison['distance'] > (2 if len(query) == 3 else 1):
            continue
        matches.append(dict(alias=alias, drug=drug, **comparison,
            replacement=alias + suffix, target_key=drug + '|non_product_specific',
            comparison_input=query, retrieved_by=[CHANNEL],
            retrieval_evidence=[dict(channel=CHANNEL, alias=alias,
                reason='same first syllable; registered two-syllable alias; bounded edits; fallback only',
                osa_distance=comparison['distance'])],
            formulation_conflict=False, prediction_source='edit_distance',
            ranking_score=comparison['score'] / 100, score_type='spelling_similarity',
            confidence='low', policy_eligible=False))
    matches.sort(key=lambda c: (-c['score'], c['alias']))
    # Abstain rather than silently drop competing names from this weak fallback.
    return matches if len(matches) <= 3 else []
