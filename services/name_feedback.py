"""OFFLINE, opt-in review records. Never logs web requests or patient identifiers.

A reviewer must supply a de-identified name token, not a prescription. The helper
cannot prove that a token is not a person's name; explicit human review is required.
No feedback is automatically used in training.
"""
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from services.name_dictionary import registry,dictionary_version,normalize_name


def make_feedback(*,name_token,ranked_result,selected_alias,reviewer_verified_deidentified=False):
    if reviewer_verified_deidentified is not True:
        raise ValueError('Human verification of de-identification is required')
    if not isinstance(name_token,str) or not re.fullmatch(r'[a-zA-Z가-힣-]{3,40}',name_token):
        raise ValueError('Supply only a de-identified drug-name token, no prescription/identifier')
    candidates=ranked_result['candidates']
    registered=registry()
    if selected_alias not in registered or not any(c['alias']==selected_alias for c in candidates):
        raise ValueError('Selection must be a registered presented candidate')
    clean=[]
    for c in candidates:
        record=registered.get(c['alias'])
        if not record or c['drug']!=record['drug']:
            raise ValueError('Invalid candidate')
        clean.append(dict(alias=c['alias'],drug=c['drug'],ranking_score=c.get('ranking_score')))
    return dict(schema_version='1',original_input=name_token,candidate_list=clean,
        selected_drug=registered[selected_alias]['drug'],selected_alias=selected_alias,
        auto_or_manual='manual',timestamp=datetime.now(timezone.utc).isoformat(),
        model_version=ranked_result['model_version'],dictionary_version=dictionary_version(),
        reviewer_verified_deidentified=True,review_status='pending_second_review',eligible_for_training=False)


def append_feedback(path,record):
    """Caller chooses a PRIVATE local path. No endpoint invokes this function."""
    allowed={'schema_version','original_input','candidate_list','selected_drug','selected_alias',
        'auto_or_manual','timestamp','model_version','dictionary_version','reviewer_verified_deidentified',
        'review_status','eligible_for_training'}
    if set(record)!=allowed or record.get('eligible_for_training') is not False:
        raise ValueError('Only pending, allowlisted review records may be written')
    # Re-validate even caller-created dictionaries. This deliberately drops extra candidate keys.
    clean=make_feedback(name_token=record['original_input'],
        ranked_result={'candidates':record['candidate_list'],'model_version':record['model_version']},
        selected_alias=record['selected_alias'],reviewer_verified_deidentified=record['reviewer_verified_deidentified'])
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(clean,ensure_ascii=False)+'\n')
