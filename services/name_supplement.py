"""Name recognition beyond the core alias table, using public sources only (no AI).

Exact names come from lookup/external_names.json (Wikidata labels in all languages for ATC
N05A/N05B/N05C/N06A/N03A/N04A/N06B/N07B/C07AA ingredients, RxNorm brand names, and every
product in the KHIDI national reimbursement list), plus researcher-reviewed additions in
lookup/name_supplement.json. Validation prescriptions are never used to add names.

Unrecognized words are then tried, in order:
  1. Korean product names (dosage-form suffix removed) from the KHIDI list;
  2. spelling correction: a Latin (accents removed) or Hangul (compared as jamo) word one or two
     letters from exactly one ingredient, every other ingredient at least two letters further;
     a truncated Latin ingredient name that begins exactly one ingredient;
  3. romanized Korean product names: a Latin word whose sound key matches exactly one Korean
     product (loanword spelling rules reversed: 스리반 ~ slivan, 큐로켈 ~ qrokel).
Steps 2 and 3 always leave a review warning with the original spelling.
"""
import csv
import json
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'lookup/name_supplement.json').read_text(encoding='utf-8'))
_external_path = ROOT / 'lookup/external_names.json'
EXTERNAL = json.loads(_external_path.read_text(encoding='utf-8')) if _external_path.exists() else {
    'multilingual': {}, 'brands': {}, 'korean_products': {}, 'ingredient_class': {}, 'antipsychotics_without_factor': []}
CLASS_LABELS = CATALOG['classes']

with open(ROOT / 'lookup/drug_alias.csv', encoding='utf-8-sig') as _f:
    _CORE = {unicodedata.normalize('NFKC', r['alias']).casefold().strip(): r['standard_name'].casefold().strip()
             for r in csv.DictReader(_f)}
with open(ROOT / 'lookup/master_lookup.csv', encoding='utf-8-sig') as _f:
    FACTOR_DRUGS = {r['source_drug'] for r in csv.DictReader(_f)}
ANTIPSYCHOTICS = FACTOR_DRUGS | set(EXTERNAL['antipsychotics_without_factor'])
OTHER_CLASSES = {k: v for k, v in EXTERNAL['ingredient_class'].items() if k not in ANTIPSYCHOTICS}

AP_ALIASES, OTHER_ALIASES, SOURCES = {}, {}, {}


def _add(alias, target, source):
    alias = unicodedata.normalize('NFKC', alias).casefold().strip()
    if not target or len(re.findall(r'[^\W\d_]', alias)) < 2 or (alias in _CORE and _CORE[alias] != target) or alias in AP_ALIASES or alias in OTHER_ALIASES:
        return
    if not re.search(r'[^\x00-ɏ]', alias) and len(alias) < 4:
        return  # short Latin labels (codes, abbreviations) are too ambiguous
    if target in ANTIPSYCHOTICS:
        AP_ALIASES[alias] = target
    else:
        OTHER_ALIASES[alias] = target
        OTHER_CLASSES.setdefault(target, 'other_non_antipsychotic')
    SOURCES[alias] = source


for _entry in CATALOG['entries']:
    for _alias in _entry['alias']:
        _add(_alias, _entry['ingredient'], _entry['source'])
        if _entry['class'] != 'antipsychotic':
            OTHER_CLASSES[_entry['ingredient']] = _entry['class']
for _name in ANTIPSYCHOTICS - FACTOR_DRUGS:
    _add(_name, _name, 'Wikidata ATC N05A')
for _name in OTHER_CLASSES:
    if re.fullmatch(r'[a-z][a-z \-]+', _name):
        _add(_name, _name, 'Wikidata ATC / KHIDI 주성분명')
for _alias, _target in EXTERNAL['multilingual'].items():
    _add(_alias, _target, 'Wikidata 다국어 표기')
for _alias, _target in EXTERNAL['brands'].items():
    _add(_alias, _target, 'RxNorm 상품명')
PRODUCTS = {k: v for k, v in EXTERNAL['korean_products'].items() if v and re.search('[a-z]', v)}
AP_COMBINATIONS = frozenset(EXTERNAL.get('antipsychotic_combinations', []))
for _target in set(PRODUCTS.values()) - ANTIPSYCHOTICS:
    OTHER_CLASSES.setdefault(_target, 'other_non_antipsychotic')
    if _target not in OTHER_ALIASES and _target not in _CORE:
        OTHER_ALIASES[_target] = _target


def fold(value):
    """Accent-free lowercase (rispéridone -> risperidone); used for non-Hangul words only."""
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


def jamo(value):
    """Hangul syllables to conjoining jamo so one wrong consonant/vowel costs one edit."""
    return unicodedata.normalize('NFD', value)


# Dosage-form words written straight after a Korean, Chinese or Japanese name.
FORM_SUFFIX = re.compile(r'(?:서방정|서방캡슐|오디정|구강붕해정|장용정|연질캡슐|캡슐|정|주사|주|시럽|액|'
                         r'片|胶囊|注射液|缓释片|錠|カプセル|細粒)$')


def distance(a, b, limit):
    """Optimal string alignment distance (adjacent transposition = 1); limit + 1 when larger."""
    from rapidfuzz.distance import OSA
    return OSA.distance(a, b, score_cutoff=limit)


# ---- sound keys for Latin spellings of Korean product names (국립국어원 외래어 표기 규칙의 역방향)
_INITIAL = 'k k n t t r m p p s s _ j j j k t p _'.split()
_VOWEL = 'a e a e o e o e o wa we we o u wo we wi u _ i i'.split()
_FINAL = ['', 'k', 'k', 'ks', 'n', 'nj', 'n', 't', 'r', 'rk', 'rm', 'rp', 'rs', 'rt', 'rp', 'r',
          'm', 'p', 'ps', 's', 's', 'nk', 'j', 'j', 'k', 't', 'p', '']


def hangul_key(word):
    out = []
    for ch in word:
        code = ord(ch) - 0xAC00
        if not 0 <= code < 11172:
            continue
        out += [_INITIAL[code // 588].strip('_'), _VOWEL[(code % 588) // 28].strip('_'), _FINAL[code % 28]]
    return _squeeze(''.join(out))


def latin_key(word):
    w = fold(word)
    if not re.fullmatch('[a-z]+', w):
        return ''
    w = re.sub(r'c(?=[eiy])', 's', w)  # soft c before the silent final e is removed
    w = re.sub(r'e$', '', w) if len(w) > 4 else w
    w = re.sub(r'^x', 'j', w)
    w = re.sub(r'y(?:e?o|ou)(?=ng)', 'o', w)  # young/yeong/yong = 영/용 (ㅕ·ㅛ keyed as o)
    w = re.sub(r'(?<![aeiou])y(?=[aeiou])', '', w)  # y-glide: the Hangul key drops it too (ㅑ = a, ㅠ = u)
    w = re.sub(r'qu(?=[aeiouy])', 'k', w)  # qu + vowel = /k(w)/ (seroquel); qu + consonant and bare q = 큐 (qurokel, qrokel)
    w = w.replace('qu', 'ku').replace('q', 'ku')
    for a, b in (('ph', 'p'), ('th', 't'), ('ck', 'k'), ('x', 'ks'), ('ee', 'i'),
                 ('oo', 'u'), ('ou', 'u'), ('ai', 'e'), ('ay', 'e'), ('ei', 'e')):
        w = w.replace(a, b)
    w = re.sub(r'ch(?=[lr])', 'k', w).replace('ch', 'j')
    w = re.sub(r'c(?=[eiy])', 's', w).replace('c', 'k')
    w = w.translate(str.maketrans('bvfdgzly', 'ppptkjri')).replace('h', '')
    return _squeeze(w)


def _squeeze(key):
    return re.sub(r'(.)\1+', r'\1', key)


_POOL = None


def _pool():
    """Latin and Hangul correction targets plus sound keys of Korean product names."""
    global _POOL
    if _POOL is None:
        from services.parser import alias_map
        from services.name_distance import BRANDS
        from services.lai_support import PRODUCTS as LAI_PRODUCTS
        latin, hangul, sound = {}, {}, defaultdict(set)
        for alias, drug in alias_map.items():
            if re.fullmatch('[a-z]{5,}', alias) and (alias == drug or alias in BRANDS or alias in SOURCES or alias in LAI_PRODUCTS):
                latin[alias] = (alias, drug)
            elif re.fullmatch('[가-힣]{3,}', alias):
                hangul[jamo(FORM_SUFFIX.sub('', alias))] = (alias, drug)
        for stem, drug in PRODUCTS.items():
            if re.fullmatch('[가-힣]{3,}', stem):
                hangul.setdefault(jamo(stem), (stem, drug))
                key = hangul_key(stem)
                if len(key) >= 5:
                    sound[key].add((stem, drug))
        _POOL = _buckets(latin), _buckets(hangul), sound
    return _POOL


def _buckets(pool):
    by_length = defaultdict(list)
    for key, value in pool.items():
        by_length[len(key)].append((key, value))
    return by_length


def _nearest(token, pool, allowed):
    best = {}
    candidates = (entry for n in range(len(token) - allowed - 2, len(token) + allowed + 3) for entry in pool.get(n, ()))
    for key, (alias, drug) in candidates:
        d = distance(token, key, allowed + 2)
        if d <= allowed + 2 and (drug not in best or (d, alias != drug) < (best[drug][0], best[drug][1] != drug)):
            best[drug] = (d, alias)
    if not best:
        return None
    ranked = sorted(best.items(), key=lambda x: (x[1][0], x[1][1]))
    drug, (d, alias) = ranked[0]
    # Unique nearest ingredient, and every other ingredient at least two edits further away.
    if d > allowed or (len(ranked) > 1 and ranked[1][1][0] < d + 2):
        return None
    return alias, drug, d


def _prefix(token, latin):
    """A truncated Latin name (quetia, halope) that begins exactly one ingredient's own name."""
    drugs = {drug for n, entries in latin.items() if n > len(token)
             for alias, (_, drug) in entries if alias == drug and alias.startswith(token)}
    return (next(iter(drugs)), next(iter(drugs)), len(next(iter(drugs))) - len(token)) if len(drugs) == 1 else None


def _sound(token, sound):
    """Romanized Korean product: the sound key must match exactly and name one ingredient."""
    key = latin_key(token)
    entries = sound.get(key, set()) if len(key) >= 5 else set()
    drugs = {drug for _, drug in entries}
    return (min(stem for stem, _ in entries), drugs.pop(), 0) if len(drugs) == 1 else None


def product_name(text):
    """Exact KHIDI Korean product name at a word: (start, end, word, product, ingredient)."""
    name = re.split(r'[+-]?(?:\d|\.\d)', text, maxsplit=1)[0]
    for word in re.finditer(r'[가-힣A-Za-z]{2,}', name):
        stem = FORM_SUFFIX.sub('', word.group()).casefold()
        if stem in PRODUCTS:
            return word.start(), word.end(), word.group(), stem, PRODUCTS[stem]
    return None


@lru_cache(maxsize=20000)
def spelling_correction(text):
    """Return (start, end, original word, corrected alias, ingredient, edits, kind) or None.

    kind is 'spelling', 'prefix' or 'romanized_product'; exactly one word may resolve.
    """
    latin, hangul, sound = _pool()
    name = re.split(r'[+-]?(?:\d|\.\d)', text, maxsplit=1)[0]
    # A product name written as two Latin words (Young proma = 영프로마) is matched as one word
    # first, so the second word alone is not expanded to a different ingredient (proma → promazine).
    for pair in re.finditer(r'(?<![^\W\d_])(?=([A-Za-z]{2,})\s+([A-Za-z]{2,})(?![^\W\d_]))', name):
        hit = _sound(pair.group(1) + pair.group(2), sound)
        if hit:
            raw = name[pair.start(1):pair.end(2)]
            return (pair.start(1), pair.end(2), raw) + hit + ('romanized_product',)
    found = []
    for word in re.finditer(r'[^\W\d_]{2,}', name):
        raw = word.group()
        hit, kind = None, 'spelling'
        if re.search('[가-힣]', raw):
            token = jamo(FORM_SUFFIX.sub('', raw))
            if len(raw) >= 3:
                hit = _nearest(token, hangul, 1 if len(token) <= 9 else 2)
        else:
            token = fold(raw)
            if re.fullmatch('[a-z]{5,}', token):
                hit = _nearest(token, latin, 1 if len(token) <= 8 else 2)
                if not hit:
                    hit, kind = _prefix(token, latin), 'prefix'
                if not hit:
                    hit, kind = _sound(raw, sound), 'romanized_product'
        if hit:
            found.append((word.start(), word.end(), raw) + hit + (kind,))
    return found[0] if len(found) == 1 else None


# ---- closed-world rule (user decision 2026-10-29)
# A name found in none of the sources above, and not close to any antipsychotic name, is treated
# as a non-antipsychotic: contribution 0 with review flag c. Names close to an antipsychotic stay held.
UNLISTED = 'unlisted_non_antipsychotic'
OTHER_CLASSES[UNLISTED] = 'unlisted'
CLASS_LABELS.setdefault('unlisted', '사전 외 약물 (0 처리)')
NOT_DRUG_WORDS = set('''tab tabs tablet tablets cap caps capsule capsules po oral daily morning evening night bedtime
    before after meal meals with and the dose doses last taken med from inj injection syrup solution sr xr cr er ir od
    disp hcl hydrochloride sodium potassium acid 경구 복용 하루 마지막 주사 정 캡슐 아침 점심 저녁 취침 전 후 식후 식전
    매일 투여 처방 중단 시작 용량 서방'''.split())
_AP_WORDS = None
# WHO INN stems of antipsychotics (Stem Book): -apine, -peridone, -piprazole, -perone, -peridol, -pride, -tixol/-tixene, -spirone.
AP_STEMS = re.compile(r'(?:apine?|peridone?|piprazole?|perone|peridol|sulpride?|tixol|thixol|tixene|thixene|serine?|spirone)$')
# The same stems as written in Korean (-핀 = -pine, -리돈 = -ridone, -돌 = -peridol, -프라졸 = -prazole, -틱센/-틱솔).
AP_STEMS_KO = re.compile(r'(?:핀|필|리돈|리도|돌|프라졸|피프라졸|틱센|틱솔|설프라이드|설피리드)$')


def _ap_words():
    global _AP_WORDS
    if _AP_WORDS is None:
        from services.parser import alias_map
        latin = sorted({fold(a) for a, d in alias_map.items() if d in ANTIPSYCHOTICS and re.fullmatch('[a-z]{3,}', fold(a))})
        hangul = sorted({jamo(FORM_SUFFIX.sub('', a)) for a, d in alias_map.items()
                         if d in ANTIPSYCHOTICS and re.fullmatch('[가-힣]{2,}', a)} |
                        {jamo(s) for s, d in PRODUCTS.items() if d in ANTIPSYCHOTICS and re.fullmatch('[가-힣]{2,}', s)})
        _AP_WORDS = latin, hangul
    return _AP_WORDS


def drug_words(text):
    """Words of the name part that could be a drug name (annotation words removed)."""
    name = re.split(r'[+-]?(?:\d|\.\d)', text, maxsplit=1)[0]
    return [w for w in re.findall(r'[^\W\d_]{2,}', name) if w.casefold() not in NOT_DRUG_WORDS]


@lru_cache(maxsize=20000)
def near_antipsychotic(text):
    """True when a name word is close to (1/2/3 edits for ≤5/≤8/longer letters), or a prefix of, an antipsychotic name."""
    from rapidfuzz import process
    from rapidfuzz.distance import OSA
    latin, hangul = _ap_words()
    words = drug_words(text)
    if any(FORM_SUFFIX.sub('', w.casefold()) in AP_COMBINATIONS for w in words) or \
            any(c in fold(text) for c in AP_COMBINATIONS if len(c) >= 5):
        return True  # combination products containing an antipsychotic are never counted as 0
    for word in words:
        korean = re.search('[가-힣]', word)
        if AP_STEMS.search(fold(word)) or (korean and AP_STEMS_KO.search(FORM_SUFFIX.sub('', re.sub('[^가-힣]', '', word)))):
            return True
        if korean:
            token, pool = jamo(FORM_SUFFIX.sub('', re.sub('[^가-힣]', '', word))), hangul
        else:
            token, pool = fold(word), latin
        if len(token) >= 3 and any(a.startswith(token) or (len(a) >= 3 and token.startswith(a)) for a in pool):
            return True
        # Hangul syllables carry 2-3 jamo each, so allow more jamo edits than Latin letters.
        cutoff = (3 if len(token) <= 9 else 4) if korean else 1 if len(token) <= 5 else 2 if len(token) <= 8 else 3
        if process.extractOne(token, pool, scorer=OSA.distance, score_cutoff=cutoff) is not None:
            return True
        if korean and len(token) >= 4:
            from rapidfuzz import fuzz  # heavy Hangul misspellings (리쓰페리도오온) keep most jamo in order
            if process.extractOne(token, pool, scorer=fuzz.ratio, score_cutoff=70) is not None:
                return True
    return False
