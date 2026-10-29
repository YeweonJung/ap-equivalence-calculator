"""Build lookup/external_names.json from public sources only (never from validation data).

Sources
  Wikidata  every item with an ATC code (P267) in the classes below: labels and aliases in all languages
  RxNorm    brand names (TTY=BN) of those ingredients (NLM RxNav REST API)
  KHIDI     national reimbursement product list (2026-04-01, 21,876 products): Korean product names

Usage: python scripts/build_external_names.py <khidi.xlsx> [--out lookup/external_names.json]
"""
import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AGENT = 'ap-equivalence-calculator/1.0 (research; dictionary build)'
CACHE = None
# ATC prefixes chosen before looking at any prescription data.
ATC_CLASSES = {
    'N05A': 'antipsychotic', 'N05B': 'anxiolytic', 'N05C': 'anxiolytic', 'N06A': 'antidepressant',
    'N03A': 'mood_stabilizer', 'N04A': 'side_effect_management', 'N06B': 'stimulant',
    'N07B': 'opioid_antagonist', 'C07AA': 'side_effect_management',
}
# Lithium (N05AN01) is in N05A but is a mood stabilizer in every conversion source.
NOT_ANTIPSYCHOTIC = {'lithium'}
SALTS = re.compile(r'\b(?:hydrochloride|dihydrochloride|hcl|fumarate|hemifumarate|tartrate|maleate|mesylate|mesilate|besylate|'
                   r'citrate|hydrate|monohydrate|dihydrate|sesquihydrate|sulfate|sulphate|acetate|bromide|hydrobromide|'
                   r'succinate|oxalate|phosphate|napadisylate|decanoate|enanthate|palmitate|pamoate|lauroxil|'
                   r'sodium|potassium|calcium|magnesium|carbonate|anhydrous|extended|micronized)\b')
SYNONYMS = {'divalproex': 'valproate', 'valproic acid': 'valproate', 'sodium valproate': 'valproate',
            'lithium carbonate': 'lithium', 'escitalopram oxalate': 'escitalopram',
            'periciazine': 'pericyazine'}  # master_lookup spelling


def get(url, data=None, accept='application/json'):
    headers = {'User-Agent': AGENT, 'Accept': accept}
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            if attempt == 5 or exc.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(65 if exc.code == 429 else 5 * (attempt + 1))
        except OSError:
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))


def base_name(value):
    value = unicodedata.normalize('NFKC', str(value)).casefold().strip()
    value = re.sub(r'\s*\(.*\)\s*$', '', value)  # Wikidata disambiguation notes
    value = re.sub(r'^(?:\((?:rs|r|s|z|e|±|\+|-)\)-|[dl]-)', '', value)  # stereo prefixes
    value = re.sub(r'\s+', ' ', SALTS.sub(' ', value)).strip(' -,')
    return SYNONYMS.get(value, value)


def wikidata():
    query = """SELECT ?item ?atc ?en ?label WHERE {
      ?item wdt:P267 ?atc . FILTER(%s)
      ?item rdfs:label ?en . FILTER(LANG(?en) = "en")
      { ?item rdfs:label ?label } UNION { ?item skos:altLabel ?label } }""" % ' || '.join(
        f'STRSTARTS(?atc, "{p}")' for p in ATC_CLASSES)
    cache = Path(CACHE) / 'wikidata_atc.json' if CACHE else None
    if cache and cache.exists():
        rows = json.loads(cache.read_text(encoding='utf-8'))
    else:
        rows = get('https://query.wikidata.org/sparql', data=urllib.parse.urlencode({'query': query}).encode(),
                   accept='application/sparql-results+json')['results']['bindings']
        if cache:
            cache.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    items = defaultdict(lambda: {'atc': set(), 'labels': set()})
    for r in rows:
        if len(r['atc']['value']) != 7:
            continue  # class items such as 'antipsychotics' are not substances
        name = base_name(r['en']['value'])
        if not re.search('[a-z]', name):
            continue
        item = items[name]
        item['atc'].add(r['atc']['value'])
        item['labels'].add(r['label']['value'])
    return items


def drug_class(atc_codes, name):
    if name in NOT_ANTIPSYCHOTIC:
        return 'mood_stabilizer'
    for prefix, cls in sorted(ATC_CLASSES.items(), key=lambda x: -len(x[0])):
        if any(code.startswith(prefix) for code in sorted(atc_codes)):
            return cls
    return 'other_non_antipsychotic'


def rxnorm_brands(name):
    """Brands of single-ingredient branded drugs (SBD 'x 10 MG Oral Tablet [Brand]'); combinations excluded."""
    cache = Path(CACHE) / 'rxnorm' / (hashlib.sha1(name.encode()).hexdigest() + '.json') if CACHE else None
    if cache and cache.exists():
        saved = json.loads(cache.read_text(encoding='utf-8'))
        if isinstance(saved, dict):
            return set(saved['single']), set(saved['combination'])
    single, combination = _rxnorm_brands(name)
    if cache:
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps({'single': sorted(single), 'combination': sorted(combination)}), encoding='utf-8')
    return single, combination


def _rxnorm_brands(name):
    try:
        found = get('https://rxnav.nlm.nih.gov/REST/rxcui.json?' + urllib.parse.urlencode({'name': name}))
    except urllib.error.HTTPError:
        return set(), set()  # names RxNav cannot parse (e.g. with slashes) have no RxNorm brand
    ids = found.get('idGroup', {}).get('rxnormId', [])
    brands, combinations = set(), set()
    for rxcui in ids[:1]:
        related = get(f'https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?tty=SBD')
        for group in related.get('relatedGroup', {}).get('conceptGroup', []) or []:
            for concept in group.get('conceptProperties', []) or []:
                m = re.fullmatch(r'(.*)\[(.+)\]', concept['name'])
                if m and ' / ' not in m.group(1):
                    brands.add(m.group(2).strip())
                elif m:
                    combinations.add(m.group(2).strip())
    time.sleep(0.06)
    return brands, combinations


FORMS = re.compile(r'(?:서방정|서방캡슐|오디정|구강붕해정|장용정|연질캡슐|필름코팅정|츄정|정|캡슐|시럽|현탁액|액|주사|주|산|과립|세립|패취|패치|크림|연고|겔|좌제|점안액|흡입)')


def khidi(path, antipsychotics, wiki_class):
    import pandas as pd
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.replace('\n', '') for c in df.columns]
    stems = defaultdict(set)
    route = defaultdict(set)
    combos = set()
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        names = [s.strip() for s in re.split(r',\s*(?=[a-z])', str(row['주성분명']).casefold())]
        bases = []
        for n in names:
            m = re.search(r'\(as ([a-z][a-z \-]+?)\s{2,}', n)
            bases.append(base_name(m.group(1) if m else re.split(r'\s{2,}|\s+[\d.]+(?:mg|g|mcg|μg|iu)', n)[0]))
        aps = [b for b in bases if any(a == b or a in b.split() for a in antipsychotics)]
        product = unicodedata.normalize('NFKC', str(row['제품명']))
        head = re.split(r'[\d(_/]', product, maxsplit=1)[0]
        stem = FORMS.split(head, maxsplit=1)[0].strip() if FORMS.search(head) else head.strip()
        if aps:
            if len(set(aps)) != 1 or len(bases) != 1:
                if len(stem) >= 2:
                    combos.add(stem.casefold())
                continue  # combination products with an antipsychotic are never mapped
            target = next(a for a in antipsychotics if a == aps[0] or a in aps[0].split())
        else:
            target = bases[0]  # non-antipsychotic (combination: first ingredient, contribution 0 either way)
        product = unicodedata.normalize('NFKC', str(row['제품명']))
        head = re.split(r'[\d(_/]', product, maxsplit=1)[0]
        stem = FORMS.split(head, maxsplit=1)[0].strip() if FORMS.search(head) else head.strip()
        company = re.sub(r'\(주\)|㈜|주식회사|\s', '', str(row['업체명']))[:2]
        for s in {stem, stem[len(company):] if company and stem.startswith(company) else stem}:
            if len(s) >= 2 and re.fullmatch(r'[가-힣A-Za-z]+', s):
                stems[s.casefold()].add(target)
                route[s.casefold()].add(row['투여'])
    out, classes = {}, {}
    for s, targets in stems.items():
        if len(targets) != 1:
            continue
        target = next(iter(targets))
        if target in antipsychotics and route[s] != {'내복'}:
            continue  # injectable/other-route antipsychotic names stay with the reviewed LAI catalog
        if not re.search('[a-z]', target):
            continue
        out[s] = target
        if target not in antipsychotics:
            classes[target] = wiki_class.get(target, 'other_non_antipsychotic')
    return out, classes, hashlib.sha256(Path(path).read_bytes()).hexdigest(), len(df), combos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('khidi')
    parser.add_argument('--out', default=str(ROOT / 'lookup/external_names.json'))
    parser.add_argument('--cache', help='folder to keep raw API responses for reproducibility')
    args = parser.parse_args()
    global CACHE
    CACHE = args.cache
    from services.converter import lookup
    factor_drugs = set(lookup.source_drug)
    items = wikidata()
    # Use the app's existing ingredient spelling when Wikidata's English label differs slightly
    # (benzatropine -> benztropine, periciazine -> pericyazine).
    from rapidfuzz.distance import OSA
    catalog = json.loads((ROOT / 'lookup/companion_medications.json').read_text(encoding='utf-8'))
    antidepressants = json.loads((ROOT / 'lookup/antidepressant_names.json').read_text(encoding='utf-8'))
    known = factor_drugs | {r['ingredient'] for r in catalog['drugs']} | {r['ingredient'] for r in antidepressants['drugs']}
    renamed = {}
    for name in list(items):
        close = [k for k in known if k != name and k[0] == name[0] and OSA.distance(k, name) <= 2]
        if name not in known and len(close) == 1:
            renamed[name] = close[0]
    for old, new in renamed.items():
        target = items[new] if new in items else items.setdefault(new, {'atc': set(), 'labels': set()})
        target['atc'] |= items[old]['atc']; target['labels'] |= items[old]['labels'] | {old}
        del items[old]
    SYNONYMS.update(renamed)
    wiki_class = {name: drug_class(v['atc'], name) for name, v in items.items()}
    antipsychotics = factor_drugs | {n for n, c in wiki_class.items() if c == 'antipsychotic'}
    labels = defaultdict(set)
    for name, v in items.items():
        for label in v['labels']:
            key = unicodedata.normalize('NFKC', label).casefold().strip()
            if len(key) >= 3 or re.search(r'[^\x00-ɏ]', key) and len(key) >= 2:
                labels[key].add(name)
    multilingual = {k: next(iter(v)) for k, v in labels.items() if len(v) == 1 and k != next(iter(v))}
    brands, combos = defaultdict(set), set()
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:  # RxNav allows 20 requests per second
        for name, (found, combination) in zip(sorted(items), pool.map(rxnorm_brands, sorted(items))):
            for b in found:
                brands[unicodedata.normalize('NFKC', b).casefold()].add(name)
            if name in antipsychotics:
                combos |= {unicodedata.normalize('NFKC', b).casefold() for b in combination}
    rx = {k: next(iter(v)) for k, v in brands.items() if len(v) == 1 and len(k) >= 3}
    products, product_classes, sha, n, khidi_combos = khidi(args.khidi, antipsychotics, wiki_class)
    payload = {
        'built_on': date.today().isoformat(),
        'policy': 'Public sources only; validation prescriptions (Pusan, Jeonbuk, Seoul) are never used to add names.',
        'sources': {
            'wikidata': {'url': 'https://query.wikidata.org/', 'selection': 'ATC (P267) prefixes ' + ', '.join(ATC_CLASSES),
                         'items': len(items)},
            'rxnorm': {'url': 'https://rxnav.nlm.nih.gov/REST/', 'selection': 'TTY=BN brands of the Wikidata ingredients'},
            'khidi': {'url': 'https://www.khidi.or.kr/board/view?linkId=48942231&menuId=MENU01869',
                      'snapshot_date': '2026-04-01', 'sha256': sha, 'products': n},
        },
        'antipsychotics_without_factor': sorted(antipsychotics - factor_drugs),
        'ingredient_class': dict(sorted((k, v) for k, v in {**{k: v for k, v in wiki_class.items() if v != 'antipsychotic'},
                                                            **product_classes}.items() if re.search('[a-z]', k))),
        'multilingual': dict(sorted(multilingual.items())),
        'brands': dict(sorted(rx.items())),
        'korean_products': dict(sorted(products.items())),
        # Brands of combination products that contain an antipsychotic: always held, never counted as 0.
        'antipsychotic_combinations': sorted((combos | khidi_combos) - set(rx) - set(products)),
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print({k: len(v) for k, v in payload.items() if isinstance(v, (dict, list))})


if __name__ == '__main__':
    main()
