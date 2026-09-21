"""Serving adapter: validated retrieval candidates require explicit user selection.

No LR model is loaded or enabled here. NAME_RETRIEVAL_ENABLED=0 rolls back to
the original spelling suggestions without touching conversion or parsing rules.
"""
import logging
import os

from services.drug_suggestions import baseline_suggestions

SERVING_CHANNELS = ('osa', 'short_hangul', 'hangul_jamo', 'normalized_alias')
SERVING_VERSION = 'candidate-retrieval-v2-short-alias-manual'
logger = logging.getLogger(__name__)


def suggest_for_review(original, limit=3):
    if os.getenv('NAME_RETRIEVAL_ENABLED', '1') == '0':
        return baseline_suggestions(original, limit)
    try:
        from services.candidate_retrieval import review_retrieval
        review = review_retrieval(original, model=None, channels=SERVING_CHANNELS)
        if not review['candidates']:
            from services.short_alias_suggestions import short_alias_candidates
            review['candidates'] = short_alias_candidates(original)
        result = []
        labels = {'insert': '삽입', 'delete': '삭제', 'replace': '교체', 'transpose': '순서 교환'}
        for candidate in review['candidates'][:max(0, min(limit, 20))]:
            explanation = '; '.join(
                f"{edit['position']}번째 {labels[edit['operation']]}: {edit['source'] or '∅'} → {edit['target'] or '∅'}"
                for edit in candidate['edits']) or '띄어쓰기·문장부호 정규화'
            if 'short_hangul' in candidate['retrieved_by']:
                explanation += ' · 짧은 이름은 혼동하기 쉬우므로 약물명을 직접 확인하세요.'
            if 'short_registered_alias' in candidate['retrieved_by']:
                explanation += ' · 낮은 유사도의 짧은 이름 후보입니다. 원문 약물명을 반드시 확인하세요.'
            if candidate['formulation_conflict']:
                explanation += ' · 입력 제형과 후보의 투여경로가 다릅니다. 직접 확인하세요.'
            result.append(dict(candidate, explanation=explanation, confirmed_drug=None,
                auto_accepted=False, needs_review=True, status='REVIEW_REQUIRED',
                serving_version=SERVING_VERSION))
        return result
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        # Do not log the prescription text or traceback/exception message.
        logger.warning('Candidate retrieval unavailable (%s); using spelling baseline', type(exc).__name__)
        return baseline_suggestions(original, limit)
