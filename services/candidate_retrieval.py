"""Offline multi-channel retrieval. Never used by the app's default serving path.

Thresholds are declared before held-out evaluation. Keep original generators,
features and model artifacts unchanged for reproducible comparisons.
"""
import re
import unicodedata
from functools import lru_cache

from services.name_dictionary import records, normalize_name, name_and_suffix
from services.name_distance import compare_letters
from services.name_features import levenshtein, jaccard, ngrams

POLICY_VERSION = 'candidate-retrieval-v1'
MAX_TARGETS = 20
SHORT_MAX_TARGETS = 3
CHANNELS = ('osa', 'short_hangul', 'hangul_jamo', 'ngram', 'normalized_alias')


def retrieval_name(text):
    """Preserve incomplete Unicode jamo as evidence instead of silently dropping it."""
    return re.sub(r'[^a-z가-힣\u1100-\u11ff]', '',
                  unicodedata.normalize('NFKC', text).casefold())


def has_hangul(text):
    return bool(re.search(r'[가-힣\u1100-\u11ff]', text))


@lru_cache(maxsize=1)
def index():
    return tuple((r, normalize_name(r['alias']),
                  unicodedata.normalize('NFD', normalize_name(r['alias']))) for r in records())


def retrieve(original, limit=20, *, channels=None):
    """Return bounded distinct targets with complete admitted-alias provenance.

    Existing OSA candidates precede added candidates, protecting recall of the
    original channel. Scores are channel-specific similarities, not probabilities.
    """
    if not isinstance(original, str) or len(original) > 10000:
        raise ValueError('Expected one bounded medication string')
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError('limit must be a nonnegative integer')
    if channels is None:
        channels = ('osa', 'short_hangul', 'hangul_jamo', 'normalized_alias')
    channels = frozenset(channels)
    if not channels <= set(CHANNELS):
        raise ValueError('Unknown retrieval channel')
    name, suffix = name_and_suffix(original)
    query = retrieval_name(name)
    n = len(query)
    korean = has_hangul(query)
    if not limit or not 2 <= n <= 40 or (n == 2 and not re.fullmatch('[가-힣]{2}', query)):
        return []
    allowed = 1 if n < 6 else 2 if n < 12 else 3
    qj = unicodedata.normalize('NFD', query)
    aliases = []
    for record, word, wj in index():
        if korean != has_hangul(word):
            continue
        # No channel can admit unbounded length differences.
        if abs(n - len(word)) > max(allowed, 2):
            continue
        comp = compare_letters(query, word)
        scores, evidence = {}, []

        def admit(channel, score, reason, **raw):
            if channel in channels:
                scores[channel] = score
                evidence.append(dict(channel=channel, alias=record['alias'],
                                     score=score, reason=reason, **raw))

        if n == 2:
            # Not arbitrary edit distance one: only an interior missing syllable.
            if len(word) == 3 and query == word[0] + word[2]:
                admit('short_hangul', comp['score'] / 100,
                      'two full syllables equal both endpoints of a three-syllable registered alias',
                      osa_distance=comp['distance'])
        else:
            if comp['distance'] <= allowed and comp['score'] >= (60 if korean else 70):
                admit('osa', comp['score'] / 100, 'unchanged OSA length/distance/score gates',
                      osa_distance=comp['distance'])
            if query == word:
                admit('normalized_alias', 1.0, 'exact normalized registered ingredient/brand/alias')
            if korean:
                distance = levenshtein(qj, wj)
                similarity = 1 - distance / max(len(qj), len(wj), 1)
                budget = 1 if n == 3 else 2
                threshold = .80 if n == 3 else .82
                if (abs(n - len(word)) <= 1 and comp['distance'] <= (1 if n == 3 else 2)
                        and distance <= budget and similarity >= threshold):
                    admit('hangul_jamo', similarity, 'bounded NFD jamo edits and syllable edits',
                          jamo_distance=distance, jamo_budget=budget, similarity_threshold=threshold)
            if n >= 6 and len(word) >= 6:
                similarity = jaccard(ngrams(query, 2), ngrams(word, 2))
                if similarity >= .65 and comp['distance'] <= min(allowed + 1, 3):
                    admit('ngram', similarity, 'bigram Jaccard >= .65 plus bounded OSA <= min(allowed+1,3)',
                          osa_distance=comp['distance'])
        if not scores:
            continue
        priority = 0 if 'osa' in scores or 'normalized_alias' in scores else 1
        aliases.append(dict(**record, **comp, comparison_input=query,
            replacement=record['alias'] + suffix,
            explanation='수동 확인용 후보: ' + ', '.join(sorted(scores)),
            retrieved_by=sorted(scores), retrieval_scores=scores,
            retrieval_evidence=evidence, retrieval_priority=priority,
            retrieval_score=comp['score'] / 100 if priority == 0 else max(scores.values()),
            retrieval_policy_version=POLICY_VERSION))
    aliases.sort(key=lambda c: (c['retrieval_priority'], -c['retrieval_score'],
                               -c['score'], c['distance'], c['alias']))
    targets = {}
    for candidate in aliases:
        key = candidate['target_key']
        if key not in targets:
            targets[key] = candidate
            candidate['matched_aliases'] = [candidate['alias']]
        else:
            kept = targets[key]
            kept['matched_aliases'].append(candidate['alias'])
            kept['retrieval_evidence'].extend(candidate['retrieval_evidence'])
            for channel, score in candidate['retrieval_scores'].items():
                kept['retrieval_scores'][channel] = max(kept['retrieval_scores'].get(channel, 0), score)
            kept['retrieved_by'] = sorted(kept['retrieval_scores'])
    cap = min(limit, SHORT_MAX_TARGETS if n == 2 else MAX_TARGETS)
    result = list(targets.values())[:cap]
    for i, candidate in enumerate(result, 1):
        candidate['retrieval_rank'] = i
        candidate['pool_inclusion_reason'] = 'channel gates passed; union by target; deterministic order; bounded top-K'
        candidate['pre_cap_target_count'] = len(targets)
    return result


def review_retrieval(original, *, model=None, channels=None):
    """Offline review; a missing model explicitly uses existing spelling ranking."""
    from services.name_ranker import MODEL_DIR, rank_candidates, decision
    import json
    config = json.loads((MODEL_DIR / 'config.json').read_text(encoding='utf-8'))
    policy = model['metadata']['policy'] if model else config['baseline_policy']
    pool = retrieve(original, policy['candidate_k'], channels=channels)
    ranked = rank_candidates(original, pool, model)
    return dict(**decision(original, ranked, policy), candidates=ranked,
                retrieval_policy_version=POLICY_VERSION,
                model_version=model['metadata']['model_version'] if model else 'baseline',
                model_available=model is not None)
