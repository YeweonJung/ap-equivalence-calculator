"""Dictionary-wide deterministic synthetic stress set, separate from frozen test.

No filtering based on retrieval results. Ambiguous source labels remain visible.
Unknown means intentionally unregistered synthetic name, not a medical assertion.
"""
import hashlib
import json
import sys
import unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.name_dictionary import records, normalize_name, name_and_suffix
from services.candidate_retrieval import has_hangul, retrieval_name


def build():
    selected = {}
    for record in sorted(records(), key=lambda r: (len(r['alias']), r['alias'])):
        selected.setdefault((record['target_key'], has_hangul(record['alias'])), record)
    rows = []

    def add(record, kind, name, safety=False):
        rows.append(dict(original=name + ' 1mg QD', origin_alias=record['alias'] if record else '',
            target_key=record['target_key'] if record else None, error_type=kind,
            safety_case=safety, synthetic=True, split='stress',
            provenance='dictionary-derived synthetic; never actual prescription'))

    for record in selected.values():
        word = record['alias']
        korean = has_hangul(word)
        i = max(1, len(word) // 2)
        replacement = '나' if korean else 'x'
        # Compound errors are constructed without consulting either generator.
        add(record, 'delete_replace', replacement + word[1:i] + word[i+1:])
        transposed = word[:i] + word[i+1] + word[i] + word[i+2:] if i+1 < len(word) else word
        add(record, 'insert_transpose', transposed[:1] + replacement + transposed[1:])
        add(record, 'space_typo', word[:i] + ' ' + replacement + word[i+1:])
        add(record, 'deletion', word[:i] + word[i+1:])
        add(record, 'insertion', word[:i] + replacement + word[i:])
        add(record, 'transposition', transposed)
        if korean:
            for length in (2, 3, 4):
                if len(word) >= length:
                    add(record, f'short_hangul_{length}', word[:length])
            jamo = list(unicodedata.normalize('NFD', word))
            for label, lower, upper in [('consonant', '\u1100', '\u1112'),
                                        ('vowel', '\u1161', '\u1175'),
                                        ('final', '\u11a8', '\u11c2')]:
                pos = next((j for j, c in enumerate(jamo) if lower <= c <= upper), None)
                altered = list(jamo)
                if pos is not None:
                    altered[pos] = lower if altered[pos] != lower else chr(ord(lower) + 1)
                elif label == 'final':
                    pos = next(j for j, c in enumerate(jamo) if '\u1161' <= c <= '\u1175') + 1
                    altered.insert(pos, lower)
                else:
                    continue
                add(record, 'hangul_' + label, unicodedata.normalize('NFC', ''.join(altered)))
            # Two independent jamo changes in different syllables.
            altered = list(jamo)
            positions = [j for j, c in enumerate(jamo) if '\u1161' <= c <= '\u1175'][:2]
            for j in positions:
                altered[j] = '\u1162' if altered[j] != '\u1162' else '\u1161'
            add(record, 'hangul_two_vowels', unicodedata.normalize('NFC', ''.join(altered)))
            pos = next(j for j, c in enumerate(jamo) if '\u1161' <= c <= '\u1175')
            add(record, 'hangul_jamo_missing', unicodedata.normalize('NFC', ''.join(jamo[:pos] + jamo[pos+1:])))
        else:
            for keys in ('qwertyuiop', 'asdfghjkl', 'zxcvbnm'):
                if word[i] in keys:
                    neighbor = keys[(keys.index(word[i]) + 1) % len(keys)]
                    add(record, 'english_keyboard', word[:i] + neighbor + word[i+1:])
                    break
            add(record, 'english_duplicate', word[:i] + word[i] + word[i:])
            add(record, 'english_multiple', 'x' + word[1:i] + 'z' + word[i+1:])
        for formulation in ('XR', 'ER', 'LAI', 'depot', 'oral', 'injection'):
            conflict = ((formulation in ('LAI', 'depot', 'injection') and record['route'] == 'oral')
                        or (formulation == 'oral' and record['route'] == 'injection'))
            add(record, 'formulation_' + formulation, word + ' ' + formulation, conflict)
        if record['kind'] == 'product':
            add(record, 'product_formulation_typo', word[:i] + word[i+1:] + ' injeciton', True)

    # Explicit close names, both registered, retain their actual distinct targets.
    for record in records():
        if record['alias'] in ('clozapine', 'olanzapine', 'risperidone', 'paliperidone', 'zotepine', 'loxapine'):
            add(record, 'similar_registered_names', record['alias'])
    registered = {normalize_name(r['alias']) for r in records()}
    unknowns = ('neurozapine', 'calmperidone', 'serotapine', 'novaprazole', 'veloperidone',
                'zotapine', 'risperidonex', 'olanzapix', 'clozapix', 'paliperidonex',
                '뉴로자핀', '세로피돈', '노바피돈', '리세돈', '조나핀', '로가핀',
                '지나돈', '로핀', '조핀', '지돈', '가핀', '노돈', '자핀',
                'qxzjxqzx', 'zzqxxjjq', '가나다라마바')
    for word in unknowns:
        if normalize_name(word) in registered:
            raise ValueError('Stress unknown unexpectedly registered: ' + word)
        add(None, 'unknown_random' if word in unknowns[-3:] else 'unknown_drug_like', word, True)
    # Intentionally retain source ambiguity instead of deleting hard examples.
    targets = {}
    for row in rows:
        key = retrieval_name(name_and_suffix(row['original'])[0])
        targets.setdefault(key, set()).add(row['target_key'])
    seen, result = set(), []
    for row in rows:
        key = (row['original'], row['target_key'], row['error_type'])
        if key in seen:
            continue
        seen.add(key)
        row['ambiguous'] = len(targets[retrieval_name(name_and_suffix(row['original'])[0])]) > 1
        row['id'] = f'stress-{len(result):05d}'
        result.append(row)
    return result


def main():
    out = ROOT / 'data/candidate_retrieval'
    destination = out / 'stress.jsonl'
    if destination.exists():
        raise RuntimeError('Stress set already frozen; do not regenerate after evaluation')
    rows = build()
    content = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows)
    destination.write_text(content, encoding='utf-8', newline='\n')
    metadata = dict(count=len(rows), sha256=hashlib.sha256(content.encode()).hexdigest(),
        known=sum(r['target_key'] is not None for r in rows),
        ambiguous=sum(r['ambiguous'] for r in rows),
        by_error_type={t: sum(r['error_type'] == t for r in rows) for t in sorted({r['error_type'] for r in rows})},
        seed=None, algorithm='deterministic shortest alias per target and script; fixed position corruption',
        threshold_selection_use=False, patient_data=False,
        note='Not independent clinical ground truth; ambiguous source labels and intentionally unregistered near-typos retained')
    (out / 'stress_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
