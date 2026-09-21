"""Pair features only: no learned drug identity or dose/frequency imputation."""
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from services.name_dictionary import normalize_name, name_and_suffix, explicit_route, formulation_conflict
from services.name_distance import compare_letters

FEATURE_VERSION = '1'
FEATURE_NAMES = ('levenshtein', 'osa', 'normalized_edit', 'insertions', 'deletions',
    'substitutions', 'transpositions', 'length_difference', 'prefix_ratio', 'suffix_ratio',
    'bigram_jaccard', 'trigram_jaccard', 'character_jaccard', 'sequence_similarity',
    'ingredient_exact', 'ingredient_partial', 'product_exact', 'product_partial',
    'alias_exact', 'normalized_exact', 'hangul_present', 'jamo_similarity',
    'script_match', 'route_known', 'route_consistent', 'formulation_conflict')


def levenshtein(left, right):
    row = list(range(len(right)+1))
    for i, a in enumerate(left, 1):
        new = [i]
        for j, b in enumerate(right, 1):
            new.append(min(new[-1]+1, row[j]+1, row[j-1]+(a != b)))
        row = new
    return row[-1]


def jaccard(a, b):
    return len(a & b) / len(a | b) if a or b else 0.0


def ngrams(word, n):
    return {word[i:i+n] for i in range(max(0, len(word)-n+1))}


def common_prefix(a, b):
    count = 0
    for x, y in zip(a, b):
        if x != y:
            break
        count += 1
    return count


def extract_features(original, candidate):
    name, _ = name_and_suffix(original)
    left, right = normalize_name(name), normalize_name(candidate['alias'])
    if max(len(left), len(right)) > 80:
        raise ValueError('Name too long for ranking')
    comparison = compare_letters(left, right)
    counts = Counter(e['operation'] for e in comparison['edits'])
    length = max(len(left), len(right), 1)
    ingredient = normalize_name(candidate['drug'])
    partial = lambda a, b: bool(a and b and min(len(a), len(b)) >= 3 and (a in b or b in a))
    hangul = bool(re.search('[가-힣]', left))
    route = explicit_route(original)
    known = route != 'unknown' and candidate['route'] != 'unknown'
    values = (levenshtein(left, right), comparison['distance'], comparison['distance']/length,
        counts['insert'], counts['delete'], counts['replace'], counts['transpose'],
        abs(len(left)-len(right)), common_prefix(left,right)/length,
        common_prefix(left[::-1],right[::-1])/length,
        jaccard(ngrams(left,2),ngrams(right,2)), jaccard(ngrams(left,3),ngrams(right,3)),
        jaccard(set(left),set(right)), SequenceMatcher(None,left,right,autojunk=False).ratio(),
        left == ingredient, partial(left,ingredient), candidate['kind']=='product' and left==right,
        candidate['kind']=='product' and partial(left,right), name.casefold()==candidate['alias'],
        left==right, hangul,
        SequenceMatcher(None,unicodedata.normalize('NFD',left),unicodedata.normalize('NFD',right),autojunk=False).ratio(),
        hangul==bool(re.search('[가-힣]',right)), known,
        known and route==candidate['route'], formulation_conflict(original,candidate))
    return dict(zip(FEATURE_NAMES, map(float, values)))
