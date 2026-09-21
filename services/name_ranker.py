"""Small local logistic model. Ranking never authorizes medication conversion."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from services.name_dictionary import dictionary_version, registry, name_and_suffix, normalize_name, formulation_conflict
from services.name_features import FEATURE_NAMES, FEATURE_VERSION, extract_features

MODEL_DIR = Path(__file__).resolve().parents[1] / 'models/name_ranker'


def read_ranker(directory):
    directory = Path(directory)
    raw = (directory/'model.json').read_bytes()
    metadata = json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
    model = json.loads(raw)
    if metadata['model_sha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('Model checksum mismatch')
    if metadata['dictionary_version'] != dictionary_version():
        raise ValueError('Dictionary changed: retrain/review before activation')
    if metadata['feature_list'] != list(FEATURE_NAMES) or metadata['feature_version'] != FEATURE_VERSION:
        raise ValueError('Feature schema mismatch')
    for key in ('coefficients', 'mean', 'scale'):
        if len(model[key]) != len(FEATURE_NAMES) or not all(math.isfinite(x) for x in model[key]):
            raise ValueError('Invalid model parameters')
    if not math.isfinite(model['intercept']) or any(x<=0 for x in model['scale']):
        raise ValueError('Invalid model scaling')
    policy = metadata['policy']
    for key in ('threshold','margin_threshold'):
        if not 0 <= policy[key] <= 1:
            raise ValueError('Invalid score policy')
    if not 3 <= policy['min_name_length'] <= 40 or not 1 <= policy['candidate_k'] <= 100:
        raise ValueError('Invalid input policy')
    return dict(model=model, metadata=metadata)


@lru_cache(maxsize=1)
def load_ranker():
    try:
        return read_ranker(MODEL_DIR)
    except (OSError, ValueError, KeyError, TypeError):
        return None  # Optional model unavailable: retain baseline; never fail conversion.


def score_candidate(original, candidate, ranker):
    features = extract_features(original,candidate)
    model = ranker['model']
    value = model['intercept'] + math.fsum(
        coef*(features[name]-mean)/scale for name,coef,mean,scale in
        zip(FEATURE_NAMES,model['coefficients'],model['mean'],model['scale']))
    # Training pair sampling changes class prevalence. This is NOT a calibrated probability.
    return 1/(1+math.exp(-max(-700,min(700,value))))


def rank_candidates(original, candidates, ranker=None):
    registered = registry()
    result = []
    for candidate in candidates:
        record = registered.get(candidate.get('alias'))
        if not record or record['drug'] != candidate.get('drug'):
            raise ValueError('Candidate is not in the registered dictionary')
        canonical = dict(candidate, **record)
        score = score_candidate(original,canonical,ranker) if ranker else candidate['score']/100
        result.append(dict(canonical, ranking_score=score,
            score_type='uncalibrated_ranking_score' if ranker else 'spelling_similarity',
            prediction_source='local_logistic_regression' if ranker else 'edit_distance',
            formulation_conflict=formulation_conflict(original,record)))
    result.sort(key=lambda c:(-c['ranking_score'],-c['score'],c['alias']))
    return [dict(c,rank=i) for i,c in enumerate(result,1)]


def decision(original, candidates, policy):
    """Research policy eligibility is separate from actual auto-accept (always disabled)."""
    name, _ = name_and_suffix(original)
    reasons = []
    if len(normalize_name(name)) < policy['min_name_length']:
        reasons.append('short_input')
    if len(name)>80 or any(x in original for x in ('\n',';','@','<','>')):
        reasons.append('untrusted_or_multiple_input')
    if not candidates:
        reasons.append('no_registered_candidate')
    else:
        first = candidates[0]
        if first['ranking_score'] < policy['threshold']:
            reasons.append('low_score')
        alternatives = [c for c in candidates[1:] if c['target_key'] != first['target_key']]
        if alternatives and first['ranking_score']-alternatives[0]['ranking_score'] < policy['margin_threshold']:
            reasons.append('small_margin_between_distinct_targets')
        if first['formulation_conflict']:
            reasons.append('formulation_conflict')
    return dict(status='REVIEW_REQUIRED' if candidates else 'UNKNOWN',
        confirmed_drug=None, auto_accepted=False, needs_review=True,
        policy_eligible=not reasons,
        confidence='candidate_for_manual_review' if not reasons else 'abstain',
        abstention_reasons=reasons or ['manual_confirmation_required'])


def review_name(original, model=None):
    from services.drug_suggestions import generate_candidates
    if not isinstance(original,str) or len(original)>10000:
        raise ValueError('Expected one bounded medication string')
    if model is None:
        model = load_ranker()
    config = json.loads((MODEL_DIR/'config.json').read_text(encoding='utf-8'))
    policy = model['metadata']['policy'] if model else config['baseline_policy']
    candidates = rank_candidates(original,generate_candidates(original,policy['candidate_k']),model)
    return dict(**decision(original,candidates,policy),candidates=candidates,
        model_version=model['metadata']['model_version'] if model else 'baseline',
        dictionary_version=dictionary_version(),
        prediction_source='local_logistic_regression' if model else 'edit_distance',
        model_available=model is not None)
