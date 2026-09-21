"""Shared, explicitly separated candidate retrieval / ranking / decision evaluation."""
import json
from pathlib import Path
from services.drug_suggestions import generate_candidates
from services.name_dictionary import registry, normalize_name, name_and_suffix, formulation_conflict
from services.name_features import extract_features
from services.name_ranker import rank_candidates, decision


def load_rows(root):
    return [json.loads(line) for line in (Path(root)/'data/name_ranker/synthetic.jsonl').read_text(encoding='utf-8').splitlines()]


def unique_targets(candidates):
    seen=set()
    result=[]
    for c in candidates:
        if c['target_key'] not in seen:
            seen.add(c['target_key'])
            result.append(c)
    return result


def evaluate(rows,ranker,policy,rankings=None,generator=generate_candidates):
    n_known=n_retrieved=conditional_correct=eligible=wrong=eligible_correct=0
    hits={1:0,3:0,5:0}
    recall={1:0,3:0,5:0,policy['candidate_k']:0}
    per_case=[]
    for row in rows:
        # Ground truth NEVER enters candidate generation, including when retrieval fails.
        if rankings is None:
            pool=generator(row['original'],policy['candidate_k'])
            pool=[dict(c, **registry()[c['alias']]) for c in pool]
            ordered=rank_candidates(row['original'],pool,ranker)
        else:
            pool,ordered=rankings[row['id']]
        distinct=unique_targets(ordered)
        target=row['target_key']
        retrieved=target is not None and any(c['target_key']==target for c in pool)
        correct=bool(distinct and target is not None and distinct[0]['target_key']==target)
        if target is not None:
            n_known+=1
            n_retrieved+=retrieved
            conditional_correct+=retrieved and correct
            for k in hits:
                hits[k]+=any(c['target_key']==target for c in distinct[:k])
            for k in recall:
                recall[k]+=any(c['target_key']==target for c in pool[:k])
        policy_result=decision(row['original'],ordered,policy)
        accepted=policy_result['policy_eligible']
        safe_correct=correct and not row['safety_case']
        eligible+=accepted
        wrong+=accepted and not safe_correct
        eligible_correct+=accepted and safe_correct
        per_case.append(dict(id=row['id'],target=target,top=distinct[0]['target_key'] if distinct else None,
            retrieved=retrieved,correct=correct,error_type=row['error_type'],
            policy_eligible=accepted,unsafe_eligible=accepted and not safe_correct,
            reasons=policy_result['abstention_reasons']))
    total=len(rows)
    divide=lambda a,b:a/b if b else None
    return dict(total_cases=total,known_target_cases=n_known,retrieved_known_cases=n_retrieved,
        candidate_recall={f'@{k}':divide(v,n_known) for k,v in recall.items()},
        top_accuracy={f'@{k}':divide(v,n_known) for k,v in hits.items()},
        ranking_top1_given_retrieved=divide(conditional_correct,n_retrieved),
        end_to_end_top1_accuracy=divide(hits[1],n_known),
        simulated_policy=dict(eligible_count=eligible,wrong_count=wrong,
            wrong_auto_accept_rate_all_inputs=divide(wrong,total),
            error_rate_among_accepted=divide(wrong,eligible),
            abstention_rate=divide(total-eligible,total),coverage=divide(eligible,total),
            accuracy_among_auto_accepted=divide(eligible_correct,eligible),
            end_to_end_correct_acceptance_rate=divide(eligible_correct,total)),
        actual_application_policy=dict(auto_accept_enabled=False,wrong_auto_accept_rate=0.0,
            abstention_rate=1.0,coverage=0.0,accuracy_among_auto_accepted=None,
            note='Every inferred candidate requires human confirmation; zero errors is not proof of model quality.'),
        cases=per_case)
