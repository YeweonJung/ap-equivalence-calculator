"""Generate synthetic-only inputs; split by ingredient BEFORE any corruption.

Run from any directory: python scripts/make_typo_examples.py
All products/aliases for one ingredient stay in one split. The shared dictionary
is a reference vocabulary, not labeled test training data.
"""
import hashlib
import json
import random
import re
import sys
import unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.name_dictionary import records, dictionary_version, normalize_name, name_and_suffix

KEY_ROWS = ('qwertyuiop','asdfghjkl','zxcvbnm')


def variants(alias, rng):
    word = alias
    if len(word)<3:
        return
    i = rng.randrange(1,len(word)-1)
    char = word[i]
    yield 'normal',word
    yield 'deletion',word[:i]+word[i+1:]
    yield 'insertion',word[:i]+('x' if char.isascii() else '가')+word[i:]
    yield 'duplication',word[:i]+char+word[i:]
    yield 'substitution',word[:i]+('z' if char!='z' and char.isascii() else '나')+word[i+1:]
    yield 'transposition',word[:i]+word[i+1]+word[i]+word[i+2:]
    for row in KEY_ROWS:
        if char in row:
            j=row.index(char)
            yield 'keyboard_neighbor',word[:i]+row[j-1 if j else 1]+word[i+1:]
            break
    yield 'case',word.upper()
    yield 'space',word[:i]+' '+word[i:]
    yield 'hyphen',word[:i]+'-'+word[i:]
    if re.search('[가-힣]',word):
        # Change one vowel jamo then recompose to syllables (no pretrained language model).
        letters=list(unicodedata.normalize('NFD',word))
        pos=next((j for j,c in enumerate(letters) if '\u1161'<=c<='\u1175'),None)
        if pos is not None:
            letters[pos]='\u1162' if letters[pos]!='\u1162' else '\u1161'
            yield 'hangul_jamo',unicodedata.normalize('NFC',''.join(letters))
    yield 'mixed_formulation',word+' XR'


def build_dataset(config):
    rng=random.Random(config['seed'])
    drugs=sorted({r['drug'] for r in records()})
    rng.shuffle(drugs)
    a=int(len(drugs)*config['split_ratios'][0])
    b=a+int(len(drugs)*config['split_ratios'][1])
    groups={drug:('train' if i<a else 'validation' if i<b else 'test') for i,drug in enumerate(drugs)}
    rows=[]
    for record in records():
        for kind,word in variants(record['alias'],rng):
            suffix=' 1mg QD' if record['route']!='injection' else ' 1mg LAI q4w'
            # This is a name benchmark, not evidence that any synthetic dose is appropriate.
            original=word+suffix
            rows.append(dict(original=original,origin_alias=record['alias'],origin_drug=record['drug'],
                target_key=record['target_key'],error_type=kind,split=groups[record['drug']],
                safety_case=False,synthetic=True))
        if record['route']!='unknown':
            opposite=' oral tablet' if record['route']=='injection' else ' LAI injection'
            rows.append(dict(original=record['alias']+opposite+' 1mg',origin_alias=record['alias'],
                origin_drug=record['drug'],target_key=record['target_key'],error_type='formulation_conflict',
                split=groups[record['drug']],safety_case=True,synthetic=True))
    # Remove ambiguous generated spellings with conflicting targets, not arbitrary relabeling.
    targets={}
    for row in rows:
        key=normalize_name(name_and_suffix(row['original'])[0])
        targets.setdefault(key,set()).add(row['target_key'])
    removed=sum(len(targets[normalize_name(name_and_suffix(row['original'])[0])])>1 for row in rows)
    rows=[r for r in rows if len(targets[normalize_name(name_and_suffix(r['original'])[0])])==1]
    seen=set()
    unique=[]
    for row in rows:
        key=(row['original'],row['target_key'])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    for split in ('train','validation','test'):
        # Unique unknowns per split; no patient strings or clinical records are used.
        for i in range(20):
            unknown=''.join(rng.choice('xzqj') for _ in range(9))
            unique.append(dict(original=unknown+' 1mg QD',origin_alias='',origin_drug='unknown_'+split,
                target_key=None,error_type='unknown',split=split,safety_case=True,synthetic=True))
        unique.append(dict(original='qx 1mg QD',origin_alias='',origin_drug='unknown_'+split,
            target_key=None,error_type='short',split=split,safety_case=True,synthetic=True))
    # Disallow even identical safety inputs across split boundaries.
    duplicates={}
    for row in unique:
        duplicates.setdefault(row['original'],set()).add(row['split'])
    unique=[r for r in unique if len(duplicates[r['original']])==1]
    for i,row in enumerate(unique):
        row['id']=f'synthetic-{i:05d}'
    return unique,groups,removed


def main():
    config=json.loads((ROOT/'models/name_ranker/config.json').read_text())
    rows,groups,removed=build_dataset(config)
    directory=ROOT/'data/name_ranker'
    directory.mkdir(parents=True,exist_ok=True)
    content=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows)
    (directory/'synthetic.jsonl').write_text(content,encoding='utf-8',newline='\n')
    metadata=dict(dataset_version=config['dataset_version'],seed=config['seed'],
        dictionary_version=dictionary_version(),sha256=hashlib.sha256(content.encode()).hexdigest(),
        example_count=len(rows),split_by_ingredient=groups,ambiguous_generated_rows_removed=removed,
        provenance='existing local alias dictionary + deterministic synthetic corruptions',
        clinical_validation=False,counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')})
    (directory/'dataset_metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(metadata['counts']), 'total',len(rows),'ambiguous removed',removed)


if __name__=='__main__':
    main()
