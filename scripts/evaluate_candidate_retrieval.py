"""Separate retrieval/ranking metrics, validation-only selection, frozen final evaluation.

Run --select first, then --evaluate. Never regenerates the original dataset/model.
"""
import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ranker_experiment import load_rows, unique_targets
from services.drug_suggestions import generate_candidates
from services.candidate_retrieval import retrieve, retrieval_name
from services.name_dictionary import name_and_suffix, dictionary_version
from services.name_ranker import read_ranker, rank_candidates, decision

OUT = ROOT / 'data/candidate_retrieval'
KS = (1, 3, 5, 10, 20)
VARIANTS = {
    'osa_short': ['osa', 'short_hangul', 'normalized_alias'],
    'osa_short_jamo': ['osa', 'short_hangul', 'hangul_jamo', 'normalized_alias'],
    'osa_short_jamo_ngram': ['osa', 'short_hangul', 'hangul_jamo', 'ngram', 'normalized_alias'],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def metrics(cases):
    known = [c for c in cases if c['target_key'] is not None]
    unknown = [c for c in cases if c['target_key'] is None]
    short = [c for c in cases if 2 <= c['name_length'] <= 3]
    conditional = [c for c in known if c['retrieved']]
    ratio = lambda n, d: n / d if d else None
    return dict(total=len(cases), known=len(known), unknown=len(unknown), short_count=len(short),
        recall_hits={str(k): sum(c['retrieval_rank'] is not None and c['retrieval_rank'] <= k for c in known) for k in KS},
        recall={str(k): ratio(sum(c['retrieval_rank'] is not None and c['retrieval_rank'] <= k for c in known), len(known)) for k in KS},
        raw_alias_recall={str(k): ratio(sum(c['raw_retrieval_rank'] is not None and c['raw_retrieval_rank'] <= k for c in known), len(known)) for k in KS},
        top={str(k): ratio(sum(c['ranking_rank'] is not None and c['ranking_rank'] <= k for c in known), len(known)) for k in (1, 3, 5)},
        retrieval_errors=sum(not c['retrieved'] for c in known),
        ranking_errors=sum(c['retrieved'] and c['ranking_rank'] != 1 for c in known),
        mean_correct_retrieval_rank=statistics.mean([c['retrieval_rank'] for c in conditional]) if conditional else None,
        mean_correct_ranking_rank=statistics.mean([c['ranking_rank'] for c in conditional]) if conditional else None,
        conditional_top1=ratio(sum(c['ranking_rank'] == 1 for c in conditional), len(conditional)),
        candidate_mean=statistics.mean([c['candidate_count'] for c in cases]) if cases else None,
        candidate_median=statistics.median([c['candidate_count'] for c in cases]) if cases else None,
        candidate_max=max([c['candidate_count'] for c in cases], default=0),
        raw_alias_candidate_mean=statistics.mean([c['raw_candidate_count'] for c in cases]) if cases else None,
        pre_cap_target_max=max([c['pre_cap_target_count'] for c in cases], default=0),
        false_target_mean=statistics.mean([c['false_candidate_count'] for c in cases]) if cases else None,
        unknown_candidate_rate=ratio(sum(c['candidate_count'] > 0 for c in unknown), len(unknown)),
        unknown_empty_rejection=ratio(sum(c['candidate_count'] == 0 for c in unknown), len(unknown)),
        unknown_policy_rejection=ratio(sum(not c['policy_eligible'] for c in unknown), len(unknown)),
        short_candidate_rate=ratio(sum(c['candidate_count'] > 0 for c in short), len(short)),
        simulated_abstention=ratio(sum(not c['policy_eligible'] for c in cases), len(cases)),
        simulated_unsafe_eligible=sum(c['unsafe_eligible'] for c in cases),
        actual_abstention=1.0, actual_auto_accept_count=0)


def evaluate(rows, generator, model, policy):
    cases = []
    for row in rows:
        pool = generator(row['original'], 20)
        distinct = unique_targets(pool)
        ranked = unique_targets(rank_candidates(row['original'], pool, model))
        target = row['target_key']
        position = lambda candidates: next((i for i, c in enumerate(candidates, 1)
                                            if target is not None and c['target_key'] == target), None)
        rr, rank = position(distinct), position(ranked)
        outcome = decision(row['original'], ranked, policy)
        cases.append(dict(id=row['id'], original=row['original'], target_key=target,
            origin_alias=row.get('origin_alias'), error_type=row['error_type'],
            ambiguous=row.get('ambiguous', False), safety_case=row['safety_case'],
            name_length=len(retrieval_name(name_and_suffix(row['original'])[0])),
            raw_retrieval_rank=position(pool), retrieval_rank=rr, ranking_rank=rank, retrieved=rr is not None,
            candidate_count=len(distinct), raw_candidate_count=len(pool),
            pre_cap_target_count=max([c.get('pre_cap_target_count', len(distinct)) for c in pool], default=0),
            false_candidate_count=sum(c['target_key'] != target for c in distinct),
            top_target=ranked[0]['target_key'] if ranked else None,
            policy_eligible=outcome['policy_eligible'],
            unsafe_eligible=outcome['policy_eligible'] and (rank != 1 or row['safety_case']),
            reasons=outcome['abstention_reasons'], confirmed_drug=outcome['confirmed_drug'],
            auto_accepted=outcome['auto_accepted'],
            candidates=[dict(target_key=c['target_key'], alias=c['alias'],
                retrieved_by=c.get('retrieved_by', ['osa']),
                retrieval_scores=c.get('retrieval_scores', {'osa': c['score'] / 100}),
                retrieval_evidence=c.get('retrieval_evidence', [])) for c in distinct]))
    return dict(metrics=metrics(cases), by_error_type={t: metrics([c for c in cases if c['error_type'] == t])
                for t in sorted({c['error_type'] for c in cases})}, cases=cases)


def guarded_inputs():
    audit = json.loads((OUT / 'phase1_audit.json').read_text(encoding='utf-8'))
    if (OUT / 'integration_manifest.json').exists():
        from scripts.retrieval_integrity import verify_integration
        verify_integration(ROOT)
        return audit
    changed = [name for name, expected in audit['original_file_sha256'].items() if sha(ROOT / name) != expected]
    if changed:
        raise ValueError('Original artifacts changed: ' + ', '.join(changed))
    return audit


def select():
    guarded_inputs()
    if (OUT / 'policy_lock.json').exists():
        raise RuntimeError('Policy already frozen; do not tune after final evaluation')
    rows = [r for r in load_rows(ROOT) if r['split'] == 'validation']
    config = json.loads((ROOT / 'models/name_ranker/config.json').read_text())
    reports = {'existing': evaluate(rows, generate_candidates, None, config['baseline_policy'])}
    for name, channels in VARIANTS.items():
        reports[name] = evaluate(rows, lambda original, limit: retrieve(original, limit, channels=channels),
                                 None, config['baseline_policy'])
    # Predeclared selection: full-pool recall, then fewer unknown hits, fewer false
    # targets, then channel count. No ranking or test outcomes drive selection.
    def key(name):
        m = reports[name]['metrics']
        return (m['recall']['20'], -m['unknown_candidate_rate'], -m['false_target_mean'], -len(VARIANTS[name]))
    selected = max(VARIANTS, key=key)
    dump(OUT / 'validation.json', reports)
    lock = dict(selected=selected, channels=VARIANTS[selected], validation_count=len(rows),
        selection='maximize validation recall@20; minimize unknown hit rate, false target mean, channel count',
        test_used=False, stress_used=False, dictionary_version=dictionary_version(),
        implementation_sha256=sha(ROOT / 'services/candidate_retrieval.py'),
        evaluator_sha256=sha(Path(__file__)),
        dataset_sha256=sha(ROOT / 'data/name_ranker/synthetic.jsonl'),
        validation_sha256=sha(OUT / 'validation.json'))
    dump(OUT / 'policy_lock.json', lock)
    print(json.dumps(dict(selected=selected, validation={k: v['metrics'] for k, v in reports.items()}), indent=2))


def final_evaluation():
    guarded_inputs()
    lock = json.loads((OUT / 'policy_lock.json').read_text())
    for key, path in [('implementation_sha256', ROOT / 'services/candidate_retrieval.py'),
                      ('evaluator_sha256', Path(__file__)),
                      ('dataset_sha256', ROOT / 'data/name_ranker/synthetic.jsonl'),
                      ('validation_sha256', OUT / 'validation.json')]:
        if sha(path) != lock[key]:
            raise ValueError('Frozen selection artifact changed: ' + key)
    config = json.loads((ROOT / 'models/name_ranker/config.json').read_text())
    model = read_ranker(ROOT / 'models/name_ranker')
    improved = lambda original, limit: retrieve(original, limit, channels=lock['channels'])
    systems = [('A_existing', generate_candidates, None, config['baseline_policy']),
               ('A_existing_LR', generate_candidates, model, model['metadata']['policy']),
               ('B_improved', improved, None, config['baseline_policy']),
               ('C_improved_LR', improved, model, model['metadata']['policy'])]
    fixed = [r for r in load_rows(ROOT) if r['split'] == 'test']
    if len(fixed) != 247:
        raise ValueError('Expected unchanged 247-case test')
    stress = [json.loads(line) for line in (OUT / 'stress.jsonl').read_text(encoding='utf-8').splitlines()]
    report = dict(policy=lock, stress_sha256=sha(OUT / 'stress.jsonl'),
        denominator='known targets only for recall/top; all inputs for candidate counts and abstention',
        k_unit='distinct targets in native pool; raw_alias_recall also retained for historical comparison',
        unknown_rejection='report both empty pool and research policy rejection; actual manual review always required',
        clinical_validation=False,
        fixed={name: evaluate(fixed, gen, ranker, policy) for name, gen, ranker, policy in systems},
        stress={name: evaluate(stress, gen, ranker, policy) for name, gen, ranker, policy in systems})
    dump(OUT / 'evaluation.json', report)
    print(json.dumps({dataset: {k: v['metrics'] for k, v in report[dataset].items()}
                      for dataset in ('fixed', 'stress')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--select', action='store_true')
    group.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    select() if args.select else final_evaluation()
