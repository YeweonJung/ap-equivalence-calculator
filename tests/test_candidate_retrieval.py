import hashlib
import json
from pathlib import Path
import unicodedata

import pytest
from services import candidate_retrieval as cr
from services.drug_suggestions import generate_candidates, baseline_suggestions, suggest_drugs
from services.name_dictionary import registry
from services.name_ranker import load_ranker
from scripts.evaluate_candidate_retrieval import metrics
from scripts.make_retrieval_stress import build

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name,target', [('로핀', 'zotepine'), ('조핀', 'zotepine'), ('지돈', 'ziprasidone')])
def test_short_interior_deletion_recovers_target_without_confirmation(name, target):
    assert generate_candidates(name) == []
    result = cr.review_retrieval(name, model=load_ranker())
    assert any(c['drug'] == target for c in result['candidates'])
    assert len(result['candidates']) <= 3
    assert result['confirmed_drug'] is None and result['auto_accepted'] is False
    assert 'short_input' in result['abstention_reasons']


@pytest.mark.parametrize('name', ['로', 'qx', '리ㅅ', '', 'a' * 41])
def test_short_policy_is_not_global_minimum_length_relaxation(name):
    assert cr.retrieve(name) == []


@pytest.mark.parametrize('channel,name', [('osa', 'risperidnoe'),
    ('short_hangul', '지돈'), ('hangul_jamo', '헬로패리돌'),
    ('ngram', 'risperidone'), ('normalized_alias', 'RISPERIDONE')])
def test_each_channel_independently_admits_registered_candidates(channel, name):
    pool = cr.retrieve(name, channels=[channel])
    assert pool
    assert all(c['retrieved_by'] == [channel] for c in pool)
    assert all(registry()[c['alias']]['target_key'] == c['target_key'] for c in pool)


def test_two_vowel_jamo_error_adds_recall_without_changing_osa():
    name = '헬로패리돌'
    assert not any(c['drug'] == 'haloperidol' for c in generate_candidates(name))
    pool = cr.retrieve(name, channels=['hangul_jamo'])
    candidate = next(c for c in pool if c['drug'] == 'haloperidol')
    assert candidate['retrieval_evidence'][0]['jamo_distance'] == 2


def test_two_jamo_edits_below_similarity_gate_remain_rejected():
    # 2/11 NFD edits yields .81818, below the frozen .82 gate.
    assert not any(c['drug'] == 'risperidone' for c in cr.retrieve('레스패리돈', channels=['hangul_jamo']))


def test_incomplete_jamo_not_silently_removed_by_retrieval_normalizer():
    word = unicodedata.normalize('NFD', '리스페리돈')
    incomplete = word[:1] + word[2:]
    assert '\u1105' in cr.retrieval_name(incomplete)


def test_target_union_retains_evidence_for_every_matching_alias():
    pool = cr.retrieve('risperidone')
    assert len({c['target_key'] for c in pool}) == len(pool)
    assert any(len(c['matched_aliases']) > 1 for c in cr.retrieve('리스페리돈'))
    for candidate in pool:
        assert set(candidate['retrieved_by']) == set(candidate['retrieval_scores'])
        assert candidate['pool_inclusion_reason']
        for channel, score in candidate['retrieval_scores'].items():
            assert score == max(e['score'] for e in candidate['retrieval_evidence'] if e['channel'] == channel)


@pytest.mark.parametrize('name', ['qxzjxqzx', '뉴로자핀', 'neurozapine'])
def test_unrelated_or_drug_like_unknown_never_confirmed(name):
    result = cr.review_retrieval(name, model=load_ranker())
    assert not result['auto_accepted'] and result['confirmed_drug'] is None
    assert result['needs_review']


def test_drug_like_unknown_can_generate_candidates_but_is_not_confirmed():
    result = cr.review_retrieval('risperidonex', model=load_ranker())
    assert result['candidates']
    assert result['confirmed_drug'] is None and not result['auto_accepted']


@pytest.mark.parametrize('name,cap', [('가다', 3), ('risperidone', 20)])
def test_candidate_explosion_cap_even_with_adversarial_dense_dictionary(monkeypatch, name, cap):
    alias = '가나다' if cap == 3 else name
    fake = tuple((dict(alias=alias, drug=f'test{i}', target_key=f'test{i}', route='unknown', profile='', kind='ingredient'),
                  alias, unicodedata.normalize('NFD', alias)) for i in range(40))
    monkeypatch.setattr(cr, 'index', lambda: fake)
    candidates = cr.retrieve(name, 1000)
    assert len(candidates) == cap
    assert candidates[0]['pre_cap_target_count'] == 40


def test_formulation_conflict_and_suffix_preservation():
    result = cr.review_retrieval('sustenna oral tablet 156mg', model=load_ranker())
    assert 'formulation_conflict' in result['abstention_reasons']
    assert not result['policy_eligible'] and not result['auto_accepted']
    assert all(c['replacement'].endswith(' oral tablet 156mg') for c in result['candidates'])


def test_depot_profiles_not_collapsed_as_one_ingredient():
    a = cr.retrieve('sustenna')[0]
    b = cr.retrieve('trinza')[0]
    assert a['drug'] == b['drug'] == 'paliperidone'
    assert a['target_key'] != b['target_key']


def test_deterministic_result_and_channel_order():
    channels = list(cr.CHANNELS)
    assert cr.retrieve('리스페리돈', channels=channels) == cr.retrieve('리스페리돈', channels=channels[::-1])


def test_missing_ranker_uses_spelling_and_app_baseline_remains(monkeypatch):
    result = cr.review_retrieval('risperidnoe', model=None)
    assert result['model_version'] == 'baseline'
    assert result['candidates'][0]['prediction_source'] == 'edit_distance'
    monkeypatch.setenv('NAME_RANKER_ENABLED', '1')
    assert suggest_drugs('로핀 1mg QD') == baseline_suggestions('로핀 1mg QD') == []


def test_original_sources_data_models_and_existing_tests_byte_identical():
    if (ROOT / 'data/candidate_retrieval/integration_manifest.json').exists():
        from scripts.retrieval_integrity import verify_integration
        verify_integration(ROOT)
        return
    audit = json.loads((ROOT / 'data/candidate_retrieval/phase1_audit.json').read_text(encoding='utf-8'))
    for path, digest in audit['original_file_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_stress_reproducible_separate_and_includes_ambiguous_unknowns():
    rows = [json.loads(line) for line in (ROOT / 'data/candidate_retrieval/stress.jsonl').read_text(encoding='utf-8').splitlines()]
    assert rows == build()
    assert any(r['ambiguous'] for r in rows)
    assert any(r['error_type'] == 'unknown_drug_like' for r in rows)
    assert all(r['split'] == 'stress' for r in rows)


@pytest.mark.parametrize('limit', [-1, True, 1.5])
def test_invalid_limit_rejected(limit):
    with pytest.raises(ValueError):
        cr.retrieve('risperidone', limit)


def test_zero_limit_and_unknown_channel():
    assert cr.retrieve('risperidone', 0) == []
    with pytest.raises(ValueError):
        cr.retrieve('risperidone', channels=['made_up'])


def test_evaluation_separates_miss_from_misrank():
    common = dict(name_length=4, candidate_count=1, raw_candidate_count=1,
                  pre_cap_target_count=1, false_candidate_count=1, policy_eligible=False, unsafe_eligible=False,
                  target_key='correct', raw_retrieval_rank=None)
    cases = [dict(common, retrieved=False, retrieval_rank=None, ranking_rank=None),
             dict(common, retrieved=True, retrieval_rank=2, ranking_rank=2)]
    result = metrics(cases)
    assert result['retrieval_errors'] == 1 and result['ranking_errors'] == 1
    assert result['recall']['20'] == .5 and result['top']['1'] == 0
