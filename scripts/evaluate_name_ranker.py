"""Frozen test comparison; never adjusts fitted weights or score thresholds."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.name_ranker import read_ranker
from services.drug_suggestions import baseline_suggestions
from scripts.ranker_experiment import load_rows,evaluate


def main():
    directory=ROOT/'models/name_ranker'
    config=json.loads((directory/'config.json').read_text())
    ranker=read_ranker(directory)
    if ranker['metadata']['dataset_sha256']!=hashlib.sha256((ROOT/'data/name_ranker/synthetic.jsonl').read_bytes()).hexdigest():
        raise ValueError('Evaluation data changed since training')
    rows=[r for r in load_rows(ROOT) if r['split']=='test']
    baseline=evaluate(rows,None,config['baseline_policy'])
    legacy=evaluate(rows,None,config['baseline_policy'],generator=baseline_suggestions)
    learned=evaluate(rows,ranker,ranker['metadata']['policy'])
    # No test-driven threshold adjustment or automatic promotion.
    improved=learned['top_accuracy']['@1']>baseline['top_accuracy']['@1']
    safer=learned['simulated_policy']['wrong_count']<=baseline['simulated_policy']['wrong_count']
    report=dict(dataset='synthetic-only held-out ingredients',clinical_validation=False,
        ranking_target='ingredient + LAI product profile; duplicate aliases collapse only for ranking metrics',
        denominator_notes={'top_accuracy':'all known-target inputs; retrieval misses count as failures',
            'candidate_recall':'known-target inputs; K counts raw alias candidates',
            'ranking_top1_given_retrieved':'known-target inputs whose target is actually retrieved',
            'simulated_policy':'all inputs, including unknown and formulation conflicts; NOT enabled in app'},
        baseline=baseline,legacy_baseline=legacy,ml=learned,
        production_decision=dict(enabled=False,synthetic_top1_improved=improved,
            synthetic_policy_no_worse=safer,reason='Retain baseline: synthetic results alone do not authorize production promotion.'))
    # Error strata prevent normal/case-only examples concealing true typo performance.
    report['by_error_type']={}
    for kind in sorted({r['error_type'] for r in rows}):
        selected=[r for r in rows if r['error_type']==kind]
        report['by_error_type'][kind]={}
        for name,model,policy in [('baseline',None,config['baseline_policy']),('ml',ranker,ranker['metadata']['policy'])]:
            metrics=evaluate(selected,model,policy)
            metrics.pop('cases')
            report['by_error_type'][kind][name]=metrics
    (ROOT/'data/name_ranker/evaluation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    metadata=ranker['metadata']
    metadata['evaluation_metrics']['test']={key:{k:v for k,v in report[key].items() if k!='cases'} for key in ('legacy_baseline','baseline','ml')}
    metadata['production_decision']=report['production_decision']
    (directory/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(metadata['evaluation_metrics']['test'],indent=2))


if __name__=='__main__':
    main()
