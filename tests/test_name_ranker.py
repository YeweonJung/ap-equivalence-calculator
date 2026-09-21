import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from services import name_ranker as nr
from services.drug_suggestions import baseline_suggestions, generate_candidates, suggest_drugs
from services.name_dictionary import registry, dictionary_version, name_and_suffix
from services.name_features import extract_features, FEATURE_NAMES
from scripts.make_typo_examples import build_dataset
from scripts.ranker_experiment import evaluate, load_rows

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((nr.MODEL_DIR/'config.json').read_text())


@pytest.mark.parametrize('name', ['risperidone', 'risperidnoe', 'risperdone', 'risperidonne'])
def test_named_examples_rank_registered_candidate_without_confirmation(name):
    result = nr.review_name(name)
    assert result['candidates'][0]['drug'] == 'risperidone'
    assert result['confirmed_drug'] is None and not result['auto_accepted']
    assert result['status'] == 'REVIEW_REQUIRED'
    assert result['candidates'][0]['score_type'] == 'uncalibrated_ranking_score'


@pytest.mark.parametrize('name,feature', [('risperidnoe', 'transpositions'),
    ('risperdone', 'insertions'), ('risperidonne', 'deletions')])
def test_character_operation_features(name, feature):
    values = extract_features(name, registry()['risperidone'])
    assert tuple(values) == FEATURE_NAMES
    assert values[feature] == 1


def test_osa_and_levenshtein_are_distinct():
    f = extract_features('risperidnoe', registry()['risperidone'])
    assert f['osa'] == 1 and f['levenshtein'] == 2


@pytest.mark.parametrize('name', ['qx', 'xzqjxzqjx', 'risperidone; olanzapine', 'risperidone\n5mg'])
def test_unreliable_input_never_accepted(name):
    result = nr.review_name(name)
    assert not result['policy_eligible']
    assert not result['auto_accepted']
    assert result['status'] in ('UNKNOWN', 'REVIEW_REQUIRED')


def test_formulation_conflict_abstains():
    result = nr.review_name('sustenna oral tablet 156mg')
    assert 'formulation_conflict' in result['abstention_reasons']
    assert not result['policy_eligible']


def test_close_distinct_ingredients_abstain():
    candidates = [dict(registry()[name], ranking_score=score, formulation_conflict=False)
                  for name, score in [('risperidone', .99), ('paliperidone', .98)]]
    result = nr.decision('risperidone', candidates, CONFIG['baseline_policy'])
    assert 'small_margin_between_distinct_targets' in result['abstention_reasons']


def test_unknown_candidate_rejected():
    with pytest.raises(ValueError, match='registered'):
        nr.rank_candidates('madeup', [dict(alias='madeup', drug='madeup', score=100)])


def test_forged_drug_rejected():
    with pytest.raises(ValueError, match='registered'):
        nr.rank_candidates('risperidone', [dict(alias='risperidone', drug='olanzapine', score=100)])


@pytest.mark.parametrize('suffix', [' XR 2mg bid', ' 156mg LAI q4w', ' -2mg PRN'])
def test_candidate_replacement_preserves_entire_suffix(suffix):
    original = 'risperidnoe'+suffix
    assert name_and_suffix(original) == ('risperidnoe', suffix)
    for candidate in generate_candidates(original):
        assert candidate['replacement'] == candidate['alias']+suffix


@pytest.mark.parametrize('enabled', ['0', '1'])
def test_unapproved_model_does_not_change_app_behavior(monkeypatch, enabled):
    monkeypatch.setenv('NAME_RANKER_ENABLED', enabled)
    assert nr.load_ranker()['metadata']['production_enabled'] is False
    assert suggest_drugs('risperidnoe 2mg bid') == baseline_suggestions('risperidnoe 2mg bid')


def test_missing_model_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(nr, 'MODEL_DIR', tmp_path)
    nr.load_ranker.cache_clear()
    try:
        monkeypatch.setenv('NAME_RANKER_ENABLED', '1')
        assert nr.load_ranker() is None
        assert suggest_drugs('risperidnoe 2mg') == baseline_suggestions('risperidnoe 2mg')
    finally:
        nr.load_ranker.cache_clear()


@pytest.mark.parametrize('field', ['model_sha256', 'dictionary_version', 'feature_version'])
def test_stale_or_corrupt_artifact_rejected(tmp_path, field):
    shutil.copy(nr.MODEL_DIR/'model.json', tmp_path/'model.json')
    metadata = json.loads((nr.MODEL_DIR/'metadata.json').read_text())
    metadata[field] = 'invalid'
    (tmp_path/'metadata.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        nr.read_ranker(tmp_path)


def test_split_isolation_reproducibility_and_artifact_hashes():
    rows = load_rows(ROOT)
    generated, _, _ = build_dataset(CONFIG)
    assert rows == generated
    groups = [{r['origin_drug'] for r in rows if r['split'] == split}
              for split in ('train', 'validation', 'test')]
    inputs = [{r['original'] for r in rows if r['split'] == split}
              for split in ('train', 'validation', 'test')]
    for collection in (groups, inputs):
        assert not collection[0] & collection[1]
        assert not collection[0] & collection[2]
        assert not collection[1] & collection[2]
    metadata = nr.read_ranker(nr.MODEL_DIR)['metadata']
    assert metadata['dictionary_version'] == dictionary_version()
    assert metadata['dataset_sha256'] == hashlib.sha256((ROOT/'data/name_ranker/synthetic.jsonl').read_bytes()).hexdigest()
    train_ids = {r['id'] for r in rows if r['split'] == 'train'}
    pairs = [json.loads(s) for s in (ROOT/'data/name_ranker/training_pairs.jsonl').read_text().splitlines()]
    assert {p['case_id'] for p in pairs} <= train_ids
    assert {p['label'] for p in pairs} == {0, 1}
    assert len(pairs) == metadata['number_of_training_pairs']


def test_retrieval_miss_is_not_hidden_in_ranking_metric():
    rows = [dict(id='test', original='xzqjxzqjx', target_key=registry()['risperidone']['target_key'],
                 safety_case=False, error_type='test')]
    metric = evaluate(rows, None, CONFIG['baseline_policy'])
    assert metric['candidate_recall']['@20'] == 0
    assert metric['top_accuracy']['@1'] == 0
    assert metric['ranking_top1_given_retrieved'] is None
    assert metric['simulated_policy']['accuracy_among_auto_accepted'] is None


def test_exported_json_matches_sklearn_and_reproduces_fitted_weights():
    sklearn = pytest.importorskip('sklearn')
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    pairs = [json.loads(s) for s in (ROOT/'data/name_ranker/training_pairs.jsonl').read_text().splitlines()]
    x = [[p['features'][f] for f in FEATURE_NAMES] for p in pairs]
    y = [p['label'] for p in pairs]
    scaler = StandardScaler().fit(x)
    classifier = LogisticRegression(random_state=CONFIG['seed'], **CONFIG['logistic']).fit(scaler.transform(x), y)
    ranker = nr.read_ranker(nr.MODEL_DIR)
    assert np.allclose(classifier.coef_[0], ranker['model']['coefficients'], atol=1e-9)
    candidate = registry()['risperidone']
    features = extract_features('risperidnoe', candidate)
    expected = classifier.predict_proba(scaler.transform([[features[f] for f in FEATURE_NAMES]]))[0, 1]
    assert nr.score_candidate('risperidnoe', candidate, ranker) == pytest.approx(expected, abs=1e-12)


def test_feedback_requires_manual_deidentification_and_stays_pending(tmp_path):
    from services.name_feedback import make_feedback, append_feedback
    kwargs = dict(name_token='risperidnoe', ranked_result=nr.review_name('risperidnoe'), selected_alias='risperidone')
    with pytest.raises(ValueError):
        make_feedback(**kwargs)
    record = make_feedback(**kwargs, reviewer_verified_deidentified=True)
    assert record['eligible_for_training'] is False
    with pytest.raises(ValueError):
        append_feedback(tmp_path/'private.jsonl', dict(record, patient_id='123'))
    append_feedback(tmp_path/'private.jsonl', record)
    saved = json.loads((tmp_path/'private.jsonl').read_text())
    assert saved['review_status'] == 'pending_second_review'
    assert 'patient_id' not in saved


@pytest.mark.parametrize('token', ['risperidone 2mg', 'patient123', 'risperidone\nJohn'])
def test_feedback_rejects_prescription_or_identifier_text(token):
    from services.name_feedback import make_feedback
    with pytest.raises(ValueError):
        make_feedback(name_token=token, ranked_result=nr.review_name('risperidnoe'),
                      selected_alias='risperidone', reviewer_verified_deidentified=True)


def test_external_records_staged_separately_with_provenance(tmp_path, monkeypatch):
    from services.drug_data_sources import stage_reviewed_records, credentials_for
    before = dictionary_version()
    monkeypatch.delenv('MFDS_API_KEY', raising=False)
    with pytest.raises(ValueError, match='MFDS_API_KEY'):
        credentials_for('mfds')
    path = stage_reviewed_records([dict(source_id='example', ingredient_name='example')],
        source='rxnorm', version='test-only', usage_note='test fixture', directory=tmp_path)
    payload = json.loads(path.read_text())
    assert payload['status'] == 'staged_not_merged'
    assert all(key in payload for key in ('source', 'retrieved_at', 'version', 'usage_note'))
    assert dictionary_version() == before
    with pytest.raises(ValueError):
        stage_reviewed_records([dict(source_id='x', ingredient_name='x', patient_id='x')],
            source='rxnorm', version='test', usage_note='test', directory=tmp_path)
