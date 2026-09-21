"""Future official-data import boundary. No network calls, scraping or alias merging."""
import json
import os
from datetime import datetime,timezone
from pathlib import Path

SOURCES={
    'mfds':{'catalog_url':'https://data.mfds.go.kr/','key_environment_variable':'MFDS_API_KEY'},
    'rxnorm':{'catalog_url':'https://www.nlm.nih.gov/research/umls/rxnorm/index.html',
              'key_environment_variable':None},
}


def credentials_for(source):
    variable=SOURCES[source]['key_environment_variable']
    if variable and not os.getenv(variable):
        raise ValueError(f'Configure {variable} outside source control after API approval')
    return os.getenv(variable) if variable else None


def stage_reviewed_records(records,*,source,version,usage_note,directory):
    """Persist allowlisted source records separately; caller first checks source terms.

    Input schema is intentionally NOT a vendor response schema. A future adapter must
    validate official field mappings before invoking this, without copying API keys.
    """
    if source not in SOURCES or not version or not usage_note:
        raise ValueError('Source, version, and reviewed license/usage note are required')
    accepted=[]
    fields={'source_id','product_name','ingredient_name','formulation'}
    for record in records:
        if set(record)-fields or not record.get('source_id') or not record.get('ingredient_name'):
            raise ValueError('Unexpected source fields')
        accepted.append({key:str(record.get(key,'')) for key in sorted(fields)})
    payload=dict(source=source,retrieved_at=datetime.now(timezone.utc).isoformat(),version=version,
        usage_note=usage_note,catalog_url=SOURCES[source]['catalog_url'],records=accepted,
        status='staged_not_merged')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(source+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
    with path.open('x',encoding='utf-8') as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2)
    return path
