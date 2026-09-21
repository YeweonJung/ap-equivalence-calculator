"""Train on training ingredients; tune abstention ONLY on validation ingredients."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from services.name_dictionary import records,registry,dictionary_version,normalize_name,name_and_suffix
from services.name_features import FEATURE_NAMES,FEATURE_VERSION,extract_features
from services.name_ranker import rank_candidates
from services.drug_suggestions import generate_candidates
from scripts.ranker_experiment import load_rows,evaluate


def training_pairs(rows,config):
    dictionary=registry()
    output=[]
    for row in rows:
        name,_=name_and_suffix(row['original'])
        query=normalize_name(name)
        nearest=sorted(records(),key=lambda c:(-SequenceMatcher(None,query,normalize_name(c['alias']),autojunk=False).ratio(),c['alias']))
        negatives=[c for c in nearest if c['target_key']!=row['target_key']][:config['hard_negatives']]
        pool=generate_candidates(row['original'],config['candidate_k'])
        candidates={c['alias']:dictionary[c['alias']] for c in pool+negatives}
        # Training can include labeled positives absent from retrieval. Test retrieval never does.
        if row['origin_alias']:
            candidates[row['origin_alias']]=dictionary[row['origin_alias']]
        for candidate in candidates.values():
            label=int(candidate['target_key']==row['target_key'] and not row['safety_case'])
            output.append(dict(case_id=row['id'],candidate=candidate['alias'],label=label,
                features=extract_features(row['original'],candidate)))
    return output


def main():
    directory=ROOT/'models/name_ranker'
    config=json.loads((directory/'config.json').read_text())
    rows=load_rows(ROOT)
    dataset=json.loads((ROOT/'data/name_ranker/dataset_metadata.json').read_text(encoding='utf-8'))
    data_raw=(ROOT/'data/name_ranker/synthetic.jsonl').read_bytes()
    if dataset['dictionary_version']!=dictionary_version() or dataset['sha256']!=hashlib.sha256(data_raw).hexdigest():
        raise ValueError('Regenerate dataset: dictionary/content changed')
    train=[r for r in rows if r['split']=='train']
    validation=[r for r in rows if r['split']=='validation']
    for left,right in [('train','validation'),('train','test'),('validation','test')]:
        assert not ({r['origin_drug'] for r in rows if r['split']==left} & {r['origin_drug'] for r in rows if r['split']==right})
    pairs=training_pairs(train,config)
    x=[[p['features'][name] for name in FEATURE_NAMES] for p in pairs]
    y=[p['label'] for p in pairs]
    scaler=StandardScaler().fit(x)
    classifier=LogisticRegression(random_state=config['seed'],**config['logistic']).fit(scaler.transform(x),y)
    artifact=dict(coefficients=classifier.coef_[0].tolist(),intercept=float(classifier.intercept_[0]),
        mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist())
    # Export JSON parameters, no pickle loading and no sklearn dependency in the web app.
    policy=dict(config['baseline_policy'])
    ranker=dict(model=artifact,metadata=dict(policy=policy))
    rankings={}
    for row in validation:
        pool=generate_candidates(row['original'],config['candidate_k'])
        rankings[row['id']]=(pool,rank_candidates(row['original'],pool,ranker))
    best=None
    trials=[]
    for threshold in config['threshold_grid']:
        for margin in config['margin_grid']:
            candidate_policy=dict(policy,threshold=threshold,margin_threshold=margin)
            metric=evaluate(validation,ranker,candidate_policy,rankings)['simulated_policy']
            trials.append(dict(threshold=threshold,margin=margin,**metric))
            if metric['wrong_count']<=config['max_validation_errors'] and metric['eligible_count']>=config['min_validation_eligible']:
                key=(metric['eligible_count'],threshold,margin)
                if best is None or key>best[0]:
                    best=(key,candidate_policy)
    policy=best[1] if best else dict(policy,threshold=1.0,margin_threshold=max(config['margin_grid']))
    ranker['metadata']['policy']=policy
    metrics=evaluate(validation,ranker,policy,rankings)
    metrics.pop('cases')
    model_raw=(json.dumps(artifact,indent=2)+'\n').encode()
    metadata=dict(model_version=config['model_version'],training_date=datetime.now(timezone.utc).isoformat(),
        training_dataset_version=dataset['dataset_version'],dataset_sha256=dataset['sha256'],
        number_of_training_examples=len(train),number_of_training_pairs=len(pairs),
        positive_pairs=sum(y),negative_pairs=len(y)-sum(y),feature_list=list(FEATURE_NAMES),feature_version=FEATURE_VERSION,
        algorithm='StandardScaler + LogisticRegression (pointwise candidate scoring)',
        hyperparameters=config['logistic'],random_seed=config['seed'],policy=policy,
        threshold=policy['threshold'],margin_threshold=policy['margin_threshold'],
        policy_selection='Validation ingredients only; maximize eligible count subject to configured error limit',
        dictionary_version=dictionary_version(),model_sha256=hashlib.sha256(model_raw).hexdigest(),
        evaluation_metrics={'validation':metrics},production_enabled=False,
        automatic_confirmation_enabled=False,clinical_validation=False,
        calibration='uncalibrated; scores are not clinical probabilities',
        dependency_versions={'python':platform.python_version(),'scikit-learn':sklearn.__version__},
        test_data_used_in_fit_or_threshold_selection=False)
    (directory/'model.json').write_bytes(model_raw)
    (directory/'metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    output=ROOT/'data/name_ranker'
    (output/'training_pairs.jsonl').write_text(''.join(json.dumps(p,sort_keys=True)+'\n' for p in pairs),encoding='utf-8')
    (output/'validation_policy_search.json').write_text(json.dumps(trials,indent=2),encoding='utf-8')
    print(json.dumps(dict(training_inputs=len(train),pairs=len(pairs),positive=sum(y),policy=policy),indent=2))


if __name__=='__main__':
    main()
