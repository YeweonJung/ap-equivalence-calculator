"""Build lookup/world_names.json: multilingual generic and product names, public reference sources only.

Never uses the validation prescriptions (Pusan, Jeonbuk, Seoul) or any other prescription data.

Sources (raw downloads are cached outside the repo, see --cache)
  Wikidata  every item with an ATC code (P267): labels + aliases in ko/en/ja/zh*/fr/ar/mul
  KEGG      KEGG DRUG (rest.kegg.jp): English + Japanese generic names, Japanese product names (商品名,
            後発品), US product names, ATC codes, KEGG antipsychotic drug group DG03200
  MHLW      Japanese NHI price list (薬価基準収載品目リスト, 内用薬/注射薬/外用薬): every product name (品名)
  RxNorm    branded drug names (SBD) of each ingredient (rxnav.nlm.nih.gov REST)
  BDPM      French public medicines database (CIS_bdpm + CIS_COMPO_bdpm): every product denomination
  EMA       EMA medicines list (centrally authorised human medicines)
  TFDA      Taiwan FDA drug licence open data (InfoId 36): 中文品名 / 英文品名 / 主成分略述
  HK        Hong Kong Drug Office list of registered pharmaceutical products (XML)
  DPD       Health Canada Drug Product Database (API: drugproduct + activeingredient)
  SFDA      Saudi FDA drugs list (public web table, English trade names)

Usage: python scripts/build_world_names.py [--cache DIR] [--out lookup/world_names.json] [--skip SOURCE ...]
"""
import argparse
import csv
import hashlib
import html
import importlib.util
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = '/tmp/claude-1000/-home-jyo52622/988f45ae-e23a-4173-87e7-24f128d1da02/scratchpad/world_names_cache'
AGENT = 'drug-dictionary-builder/1.0 (research; public reference data)'
CACHE = Path(DEFAULT_CACHE)
TODAY = date.today().isoformat()

_spec = importlib.util.spec_from_file_location('ben', ROOT / 'scripts/build_external_names.py')
ben = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ben)

# ---------------------------------------------------------------- download helpers

def fetch(url, name, data=None, accept='*/*', refresh=False, pause=0.0):
    """Return bytes of url, cached at CACHE/raw/name."""
    path = CACHE / 'raw' / name
    if path.exists() and not refresh:
        return path.read_bytes()
    headers = {'User-Agent': AGENT, 'Accept': accept}
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                body = b''
                break
            if attempt == 5 or exc.code not in (403, 429, 500, 502, 503, 504):
                raise
            time.sleep(30 if exc.code == 429 else 5 * (attempt + 1))
        except OSError:
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    if pause:
        time.sleep(pause)
    return body


def decode(raw):
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return raw.decode('cp1252')


# ---------------------------------------------------------------- normalisation

def norm(value):
    value = unicodedata.normalize('NFKC', str(value)).replace('®', '').replace('™', '').replace('©', '')
    value = re.sub(r'\s+', ' ', value.casefold()).strip(' \t-–—,;:.·/\\"\'`')
    return value


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))


MORE_SALTS = re.compile(r'\b(?:hemihydrate|trihydrate|pentahydrate|tetrahydrate|dimesylate|lactate|embonate|benzoate|'
                        r'nitrate|chloride|bitartrate|dipropionate|propionate|valerate|furoate|disodium|monosodium|'
                        r'dimaleate|hyclate|tosylate|esylate|camsylate|napsylate|hydrogen|sulfonate|edisylate|'
                        r'hydroiodide|methylbromide|methylsulfate|acetonide|fosamil|medoxomil|cilexetil|axetil|'
                        r'pivoxil|proxetil|hexetil|mofetil|etabonate|cypionate|undecanoate|isethionate|gluconate|'
                        r'lysine|arginine|meglumine|trometamol|tromethamine|olamine|erbumine|tert-butylamine|'
                        r'base|eq to|equivalent to|as|usp|bp|ep|jp|inn|ban|usan|dcf)\b')
GENERIC_CHEM = {'oxide', 'chloride', 'hydroxide', 'sulfate', 'sulphate', 'acid', 'citrate', 'phosphate', 'acetate',
                'carbonate', 'bicarbonate', 'lactate', 'gluconate', 'iodide', 'fluoride', 'nitrate', 'salt', 'water',
                'dibasic', 'monobasic', 'tribasic', 'anhydrous', 'hydrous', 'dried', 'light', 'heavy', 'hydroxide'}


def ingredient_key(value):
    """Lookup key for an ingredient string (salts and hydrates removed, accents folded)."""
    v = norm(value)
    v = re.sub(r'\[.*?\]', '', v)
    v = re.sub(r'\((?:jan|jp\d*|usp|inn|usan|ban|nf|tn|dcf|jan/usp/inn|[a-z]{2,4}(?:/[a-z]{2,6})+)\)', '', v)
    base = ben.base_name(v)
    base = re.sub(r'\s+', ' ', MORE_SALTS.sub(' ', base)).strip(' -,')
    if len(re.findall('[a-z]', base)) < 4 or base in GENERIC_CHEM or base.split()[0] in GENERIC_CHEM:
        base = v.strip()
    if re.match(r'lithium\b', base):
        base = 'lithium'  # lithium salts (N05AN01) stay the app's mood stabilizer
    return fold(ben.SYNONYMS.get(base, base))


FR_SALT = re.compile(r"^(?:(?:mono|di|tri|hémi|hemi|sesqui)?(?:chlorhydrate|bromhydrate|maléate|maleate|fumarate|"
                     r"hémifumarate|palmitate|décanoate|decanoate|énantate|enantate|pamoate|embonate|mésilate|mesilate|"
                     r"bésilate|besilate|tartrate|citrate|sulfate|acétate|acetate|succinate|oxalate|phosphate|lactate|"
                     r"chlorure|nitrate|méthylsulfate|tosilate|bitartrate|valérate|propionate|dipropionate|benzoate|"
                     r"chlorhydrate monohydraté)) (?:de |d')")
FR_TAIL = re.compile(r"\b(?:monohydraté|monohydratée|dihydraté|trihydraté|hémihydraté|anhydre|sodique|potassique|calcique|"
                     r"magnésique|base|micronisée?|sel de sodium|sesquihydraté|hydraté|hydratée)\b")


def fr_ingredient_key(value):
    v = norm(value)
    v = FR_SALT.sub('', v)
    v = re.sub(r'\s+', ' ', FR_TAIL.sub(' ', v)).strip(' -,')
    return fold(v)


JA_SALT = re.compile(r'(?:塩酸塩|臭化水素酸塩|硫酸塩|マレイン酸塩|フマル酸塩|酒石酸塩|メシル酸塩|ベシル酸塩|クエン酸塩|'
                     r'リン酸塩|酢酸塩|コハク酸塩|シュウ酸塩|ナトリウム塩|カリウム塩|カルシウム塩|水和物|エステル|'
                     r'デカン酸|パルミチン酸|エナント酸|ナトリウム|カリウム|カルシウム|水和物)+$')
JA_SALT_PREFIX = re.compile(r'^(?:塩酸|硫酸|乳酸|酢酸|酒石酸|マレイン酸|フマル酸|臭化水素酸|リン酸|クエン酸|コハク酸|メシル酸)(?=..)')


def ja_ingredient_key(value):
    v = norm(value)
    v = re.sub(r'\s*\((?:jan|jp\d+|jan/usp|.*?)\)\s*', '', v)
    v2 = JA_SALT_PREFIX.sub('', JA_SALT.sub('', v))
    return v2 or v


# ---------------------------------------------------------------- dosage forms / generic words

LATIN_FORMS = set('''tab tabs tablet tablets tablette tabletten comprimé comprimés comprime comprimes compr cpr film filmtab
    filmtabs coated fc f.c. f/c cap caps capsule capsules gélule gélules gelule gelules softgel softgels inj inj. injection
    injections injectable injectables solution solutions soln sol susp suspension suspensions syrup syrups syr sirop drop
    drops gouttes cream creme crème oint ointment pommade gel gels patch patches transdermal transdermique dispositif
    ext extended release releasing prolonged prolongée prolongee modified delayed sustained retard sr xr er cr la xl xr
    mr pr dr ir od odt orodispersible orodispersibles disintegrating dispersible dispersibles chewable effervescent
    effervescents powder poudre pdr concentrate concentré conc infusion perfusion inf iv i.v. im i.m. sc s.c. vial vials
    ampoule ampoules amp amps pre-filled prefilled préremplie syringe syringes seringue pen stylo kit pack elixir liquid
    lozenge lozenges spray nasal inhal inhaler inhalation aerosol suppository suppositories supp suppositoire suppositoires
    enema eye ear granules granulés granule sachet sachets mg mcg µg μg ml g iu ui unit units u/ml mg/ml % w/v w/w
    buvable orale oral orally intramusculaire intraveineuse sous-cutanée cutanée usage pour for and with in of the de du
    des la le à a en et sans avec dans lyophilisat lyophilized lyophilised emulsion émulsion lotion shampoo shampooing
    collyre ophthalmic otic topical vaginal rectal sublingual buccal ovule ovules implant microspheres microsphères
    depot dépôt long-acting acting f.c f.c. fc. tabl tm b.p bp usp fine lp l.p l.p. film-coated pr. sol. inj
    gastro-resistant gastro-résistant enrobé enrobés pelliculé pelliculés sécable sécables'''.split())
JA_FORMS = ['持続性水懸筋注用', '持続性水懸筋注', '水懸筋注用', '水懸筋注', '筋注用', '筋注', '静注用', '静注', '皮下注',
            '注射液', '注射用', '注射剤', '点滴静注', '口腔内崩壊錠', 'ＯＤ錠', 'od錠', '徐放錠', '腸溶錠', '舌下錠',
            'フィルムコーティング錠', 'チュアブル錠', '配合錠', '配合顆粒', '配合散', '配合内用液', '配合', '錠', '細粒',
            '顆粒', 'ドライシロップ', 'シロップ', '散', 'カプセル', '内用液', '内服液', '経口液', '液', 'テープ', 'パップ',
            '貼付剤', '坐剤', '坐薬', '軟膏', 'クリーム', 'ゲル', 'ローション', '点眼液', '点鼻液', '吸入', '注', 'シリンジ',
            'キット', 'ゼリー', 'エアゾール', 'スプレー', 'ペン', '「']
ZH_FORMS = sorted(set('''持續性藥效膜衣錠 持續性藥效錠 持續性藥效膠囊 緩釋膜衣錠 緩釋錠 緩釋膠囊 長效注射懸浮液 長效注射懸液劑
    長效注射劑 長效注射液 注射懸浮液 注射懸液劑 注射懸液 凍晶注射劑 乾粉注射劑 注射用乾粉 注射劑 注射液 注射用 注射
    口溶錠 口崩錠 口溶膜 腸溶膜衣錠 腸溶錠 腸溶膠囊 糖衣錠 膜衣錠 舌下錠 發泡錠 咀嚼錠 錠劑 錠 軟膠囊 硬膠囊 膠囊劑 膠囊
    內服液劑 內服液 口服液 口服溶液 液劑 溶液劑 溶液 糖漿劑 糖漿 懸液劑 懸浮液 乳劑 散劑 細粒 顆粒劑 顆粒 乳膏 軟膏 凝膠
    貼片劑 貼片 貼布 點眼液 眼藥水 栓劑 吸入劑 噴霧劑 噴霧 片劑 片 胶囊 缓释片 注射液 口服液 颗粒 分散片 肠溶片
    滴劑 浸劑 酊劑 洗劑 液'''.split()), key=len, reverse=True)
GENERIC_WORDS = set('''tablet tablets tab tabs capsule capsules cap injection inj solution suspension syrup cream ointment
    gel patch drops powder hydrochloride hcl sodium potassium calcium magnesium maleate fumarate tartrate mesylate besylate
    citrate sulfate sulphate acetate phosphate decanoate palmitate enanthate pamoate monohydrate anhydrous base salt
    comprimé comprimés gélule gélules injectable sirop pommade chlorhydrate oral orale buvable retard depot dépôt forte
    plus mite junior adult adults child children kids baby infant pediatric paediatric generic generics extra strength
    regular original maximum rapid fast active relief cold cough night day sleep calm natural vitamin vitamins multi
    complete care pain allergy sinus flu nasal sore throat chest congestion sinus diet women men senior mineral minerals
    formula classic advanced ultra daily total balance health healthy protect protection clear fresh pure gold silver
    water oxygen air nitrogen alcohol ethanol placebo saline glucose dextrose sugar honey lemon cherry orange mint
    tylenol? 錠 錠剤 カプセル 細粒 散 注射液 注 液 シロップ 片 胶囊 注射液 錠劑 膠囊 注射劑 '''.split())
NOT_DRUG = set(w.casefold() for w in '''tab tabs tablet tablets cap caps capsule capsules po oral daily morning evening night
    bedtime before after meal meals with and the dose doses last taken med from inj injection syrup solution sr xr cr er ir od
    disp hcl hydrochloride sodium potassium acid 경구 복용 하루 마지막 주사 정 캡슐 아침 점심 저녁 취침 전 후 식후 식전
    매일 투여 처방 중단 시작 용량 서방'''.split())


def is_generic_word(alias):
    a = alias.strip()
    letters = re.findall(r'[^\W\d_]', a)
    if len(letters) < 2:
        return True
    if a in GENERIC_WORDS or a in NOT_DRUG or a in LATIN_FORMS or a in JA_FORMS or a in ZH_FORMS:
        return True
    toks = re.split(r'[\s/,+&-]+', a)
    if toks and all(t in LATIN_FORMS or t in GENERIC_WORDS or t in NOT_DRUG or re.fullmatch(r'[\d.%]*', t) or
                    MORE_SALTS.fullmatch(t) or ben.SALTS.fullmatch(t) for t in toks):
        return True
    if not re.search(r'[^\x00-ɏ]', a) and len(a) < 4:
        return True
    if len(a) > 60 or (len(a) > 25 and re.search(r'\d', a) and re.search(r'[(),\[\]]', a)):
        return True  # systematic chemical names
    return False


def latin_stem(name, keep_long=False):
    """Brand part of a Latin product name: words before the first strength, comma or dosage-form word."""
    n = norm(name)
    n = re.sub(r'\((?:previously|anciennement)\s+([^)]*)\)', '', n)
    n = re.sub(r'[“”"\'«»]([^“”"\'«»]{1,40})[“”"\'«»]', ' ', n)  # maker in quotes (TW "生達")
    n = re.split(r'\s*[“”"«»]', n, maxsplit=1)[0]  # unmatched quote: maker suffix
    n = re.split(r'[,(\[]|\s[-–]\s', n, maxsplit=1)[0]
    words = n.split()
    out = []
    for w in words:
        wc = w.strip('.;:')
        if re.match(r'^[\d.]', wc) or wc in LATIN_FORMS or re.fullmatch(r'\d+(?:\.\d+)?(?:mg|g|mcg|ml|%|iu|µg|μg)\S*', wc):
            break
        out.append(wc)
    stems = set()
    if out:
        stems.add(' '.join(out))
    if keep_long:
        long = ' '.join(w for w in re.split(r'\s+', re.split(r'\s\d|^\d', n, maxsplit=1)[0]) if w)
        if long and long != ' '.join(out) and len(long.split()) <= 4:
            stems.add(long.strip())
    return {s.strip(' -/&+') for s in stems if s.strip(' -/&+')}


def ja_variants(name):
    """Japanese product-name variants: brand stem, full name without strength/maker, space-free forms."""
    n = unicodedata.normalize('NFKC', str(name)).casefold().strip()
    n = re.sub(r'「[^」]*」', '', n)
    n = re.sub(r'\s*\([^)]*\)\s*$', '', n)  # KEGG maker
    full = re.sub(r'(?<![a-z])[\d.,]+\s*(?:mg|g|μg|µg|mcg|ml|l|%|単位|万単位|w/v%|mg/ml|ug)?(?:/\s*[\d.]*\s*(?:ml|g|l|錠|包))?', ' ', n)
    full = re.sub(r'(?:シリンジ|キット|分包|バイアル|ペン)\s*$', '', full)
    full = re.sub(r'\s+', ' ', full).strip(' ・-')
    out = {full, full.replace(' ', '')}
    idx = len(n)
    for f in JA_FORMS:
        i = n.find(f.casefold())
        if i > 0:
            idx = min(idx, i)
    m = re.search(r'\d', n)
    if m and m.start() > 0:
        idx = min(idx, m.start())
    stem = n[:idx].strip(' ・-')
    if stem:
        out |= {stem, stem.replace(' ', '')}
    return {v for v in out if v}


ZH_CUT = '''持續性 長效 膜衣錠 錠 膠囊 注射 肌肉 口溶 口崩 速溶 內服 液劑 懸浮 懸液 凍晶 糖漿 乳膏 軟膏 點眼 點鼻 栓劑 貼片 貼布
    噴霧 吸入 顆粒 散劑 腸溶 緩釋 舌下 發泡 咀嚼 溶液 外用 胶囊 缓释 注射液 片剂'''.split()


def zh_variants(name, form=''):
    n = unicodedata.normalize('NFKC', str(name)).casefold().strip()
    n = re.sub(r'[“”"「」『』][^“”"「」『』]{1,20}[“”"「」『』]', '', n)  # maker in quotes
    n = re.sub(r'[(（][^)）]*[)）]', '', n)
    n = re.split(r'[\d.]', n, maxsplit=1)[0].strip()
    n = re.sub(r'[a-z\s]+$', '', n).strip()  # trailing Latin strength units
    n = re.sub(r"^[^'’]{1,6}['’]\s*", '', n)  # maker prefix ending with an apostrophe
    out = {n} if re.search('[一-鿿]', n) else set()
    stem = n
    cut = [i for i in (n.find(f) for f in ZH_CUT) if i >= 2]
    if cut:
        out.add(n[:min(cut)].strip())
        stem = n[:min(cut)].strip()
    form = unicodedata.normalize('NFKC', form or '').strip()
    for _ in range(4):
        before = stem
        if form and stem.endswith(form) and len(stem) > len(form) + 1:
            stem = stem[:-len(form)]
        for f in ZH_FORMS:
            if stem.endswith(f) and len(stem) > len(f) + 1:
                stem = stem[:-len(f)]
                break
        if stem == before:
            break
    if re.search('[一-鿿]', stem) and len(stem) >= 2:
        out.add(stem)
    return out


def script_language(alias, default):
    if re.search('[가-힣]', alias):
        return 'ko'
    if re.search('[ぁ-ゟ゠-ヿ]', alias):
        return 'ja'
    if re.search('[؀-ۿ]', alias):
        return 'ar'
    if re.search('[一-鿿]', alias):
        return default if default in ('ja', 'zh') else 'zh'
    if re.search('[Ѐ-ӿͰ-Ͽ֐-׿ऀ-෿]', alias):
        return 'other'
    return default if default in ('en', 'fr') else 'en'


# ---------------------------------------------------------------- the app's existing names

def app_names():
    with open(ROOT / 'lookup/master_lookup.csv', encoding='utf-8-sig') as f:
        factor = {r['source_drug'] for r in csv.DictReader(f)}
    ext = json.loads((ROOT / 'lookup/external_names.json').read_text(encoding='utf-8'))
    aps = factor | set(ext['antipsychotics_without_factor'])
    with open(ROOT / 'lookup/drug_alias.csv', encoding='utf-8-sig') as f:
        core = {unicodedata.normalize('NFKC', r['alias']).casefold().strip(): r['standard_name'].casefold().strip()
                for r in csv.DictReader(f)}
    existing = {}
    for table in ('multilingual', 'brands', 'korean_products'):
        for a, t in ext.get(table, {}).items():
            existing.setdefault(unicodedata.normalize('NFKC', a).casefold().strip(), t)
    for a, t in core.items():
        existing[a] = t
    return aps, factor, ext, core, existing


# ---------------------------------------------------------------- sources

WD_LANGS = ['en', 'ko', 'ja', 'zh', 'zh-hans', 'zh-hant', 'zh-cn', 'zh-tw', 'zh-hk', 'zh-sg', 'zh-mo', 'zh-my', 'fr', 'ar', 'mul']


def wikidata():
    rows = []
    for letter in 'ABCDGHJLMNPRSV':
        q = """SELECT ?item ?atc ?label ?kind WHERE { ?item wdt:P267 ?atc . FILTER(STRSTARTS(?atc, "%s"))
          { ?item rdfs:label ?label . BIND("label" AS ?kind) } UNION { ?item skos:altLabel ?label . BIND("alt" AS ?kind) }
          FILTER(LANG(?label) IN (%s)) }""" % (letter, ', '.join(f'"{l}"' for l in WD_LANGS))
        raw = fetch('https://query.wikidata.org/sparql', f'wikidata/atc_{letter}.json',
                    data=urllib.parse.urlencode({'query': q}).encode(), accept='application/sparql-results+json', pause=1)
        for r in json.loads(raw)['results']['bindings']:
            rows.append((r['item']['value'].rsplit('/', 1)[1], r['atc']['value'], r['label']['value'],
                         r['label'].get('xml:lang', ''), r['kind']['value']))
    items = defaultdict(lambda: {'atc': set(), 'en': None, 'labels': set(), 'main': set()})
    for qid, atc, label, lang, kind in rows:
        it = items[qid]
        it['atc'].add(atc)
        it['labels'].add((label, lang))
        if kind == 'label':
            it['main'].add((label, lang))
        if lang == 'en' and kind == 'label':
            it['en'] = label
    return items, len(rows)


def kegg():
    lst = decode(fetch('https://rest.kegg.jp/list/drug_ja', 'kegg/list_drug_ja.txt'))
    ids = [line.split('\t')[0].split(':')[1] for line in lst.splitlines() if '\t' in line]
    batches = [ids[i:i + 10] for i in range(0, len(ids), 10)]

    def get(batch):
        return decode(fetch('https://rest.kegg.jp/get/' + '+'.join('dr_ja:' + i for i in batch),
                            f'kegg/get/{batch[0]}_{batch[-1]}.txt', pause=0.15))
    with ThreadPoolExecutor(max_workers=3) as pool:
        texts = list(pool.map(get, batches))
    entries = {}
    for text in texts:
        for block in text.split('\n///'):
            e = parse_kegg(block)
            if e:
                entries[e['id']] = e
    return entries


KEGG_LABELS = {'一般名': 'names', '商品名': 'jp', '米国の商品': 'us', '成分': 'comp', 'コード': 'code', 'クラス': 'class'}


def parse_kegg(block):
    lines = block.strip('\n').splitlines()
    if not lines or not lines[0].startswith('エントリ'):
        return None
    e = {'id': lines[0].split()[1], 'mixture': 'Mixture' in lines[0], 'names': [], 'jp': [], 'us': [], 'comp': [],
         'code': [], 'class': []}
    field = None
    for line in lines[1:]:
        if line[:1] not in (' ', '\t', ''):
            label, _, value = line.partition(' ')
            field = KEGG_LABELS.get(label)
            value = value.strip()
        else:
            value = re.sub(r'^\s+(?:後発品|GENERIC)\s{2,}', '', line).strip()
        if field and value:
            e[field].append(value)
    names = []
    for v in e['names']:
        names += [x.strip() for x in v.split(';') if x.strip()]
    e['names'] = names
    e['atc'] = sorted(set(re.findall(r'\b([A-Z]\d\d[A-Z]{2}\d\d)\b', ' '.join(e['code']))))
    e['antipsychotic_group'] = any('DG03200' in c for c in e['class'])
    e['comp_ids'] = re.findall(r'DR:(D\d{5})', ' '.join(e['comp']))
    return e


def rxnorm(name):
    raw = fetch('https://rxnav.nlm.nih.gov/REST/rxcui.json?' + urllib.parse.urlencode({'name': name, 'search': 0}),
                'rxnorm/' + hashlib.sha1(('id:' + name).encode()).hexdigest() + '.json', accept='application/json')
    try:
        ids = json.loads(raw or b'{}').get('idGroup', {}).get('rxnormId', [])
    except ValueError:
        return set(), set()
    single, combo = set(), set()
    for rxcui in ids[:1]:
        rel = json.loads(fetch(f'https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?tty=SBD+BPCK',
                               f'rxnorm/rel_{rxcui}.json', accept='application/json') or b'{}')
        for group in rel.get('relatedGroup', {}).get('conceptGroup', []) or []:
            for c in group.get('conceptProperties', []) or []:
                m = re.fullmatch(r'(.*)\[(.+)\]', c['name'])
                if m and ' / ' not in m.group(1) and not c['name'].startswith('{'):
                    single.add(m.group(2).strip())
                elif m:
                    combo.add(m.group(2).strip())
    return single, combo


def bdpm():
    base = 'https://base-donnees-publique.medicaments.gouv.fr/download/file/'
    cis = decode(fetch(base + 'CIS_bdpm.txt', 'bdpm/CIS_bdpm.txt'))
    compo = decode(fetch(base + 'CIS_COMPO_bdpm.txt', 'bdpm/CIS_COMPO_bdpm.txt'))
    subs = defaultdict(lambda: defaultdict(dict))  # cis -> link no -> nature -> name
    for line in compo.splitlines():
        p = line.split('\t')
        if len(p) >= 8:
            subs[p[0]][p[7].strip()][p[6].strip()] = p[3].strip()
    products = []
    for line in cis.splitlines():
        p = line.split('\t')
        if len(p) < 3:
            continue
        ings = [links.get('FT') or links.get('SA') for links in subs.get(p[0], {}).values()]
        products.append((p[1].strip(), [i for i in ings if i], p[2].strip()))
    return products


def ema():
    import pandas as pd
    raw = fetch('https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx', 'ema/medicines.xlsx')
    df = pd.read_excel(io.BytesIO(raw), header=8, dtype=str)
    df = df[df['Category'] == 'Human']
    out = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        name = str(row['Name of medicine'])
        inn = str(row['International non-proprietary name (INN) / common name'])
        names = [re.sub(r'\s*\(previously.*', '', name)] + re.findall(r'previously ([^)]*)\)', name)
        out.append((names, [s.strip() for s in re.split(r',|/| and ', inn) if s.strip() and s != 'nan'],
                    str(row.get('ATC code (human)', ''))))
    return out


def tfda():
    raw = fetch('https://data.fda.gov.tw/opendata/exportDataList.do?method=ExportData&InfoId=36&logType=2', 'tfda/36.zip')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode('utf-8-sig')
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        lic = row.get('許可證字號', '')
        if '中藥' in lic or '醫器' in lic or not row.get('主成分略述'):
            continue
        ings = [s.strip() for s in row['主成分略述'].split(';;') if s.strip()]
        out.append((row.get('中文品名', ''), row.get('英文品名', ''), list(dict.fromkeys(ings)), row.get('劑型', '')))
    return out


def hongkong():
    import xml.etree.ElementTree as ET
    root = ET.fromstring(fetch('https://www.drugoffice.gov.hk/eps/psi/DrugList.xml', 'hk/DrugList.xml'))
    return [(d.findtext('productName') or '', [a.text or '' for a in d.iter('activeIng')]) for d in root.iter('drug')]


def dpd():
    prods = json.loads(fetch('https://health-products.canada.ca/api/drug/drugproduct/?lang=en&type=json', 'dpd/drugproduct.json'))
    ais = json.loads(fetch('https://health-products.canada.ca/api/drug/activeingredient/?lang=en&type=json', 'dpd/activeingredient.json'))
    by = defaultdict(list)
    for a in ais:
        by[a['drug_code']].append(a['ingredient_name'])
    return [(p['brand_name'], list(dict.fromkeys(by.get(p['drug_code'], [])))) for p in prods if p.get('class_name') == 'Human']


def sfda():
    first = decode(fetch('https://www.sfda.gov.sa/en/drugs-list?page=0', 'sfda/page_0.html'))
    pages = max(int(x) for x in re.findall(r'page=(\d+)', first) or ['0'])
    out = []
    for i in range(pages + 1):
        text = first if i == 0 else decode(fetch(f'https://www.sfda.gov.sa/en/drugs-list?page={i}', f'sfda/page_{i}.html', pause=0.4))
        for tr in re.findall(r'<tr.*?</tr>', text, re.S):
            cells = [html.unescape(re.sub(r'<[^>]+>', ' ', c)).strip() for c in re.findall(r'<td.*?</td>', tr, re.S)]
            if len(cells) >= 2 and cells[0]:
                out.append((re.sub(r'\s+', ' ', cells[1]), [s.strip() for s in re.split(r',|\+| and ', cells[0]) if s.strip()]))
    return out, pages + 1


# ---------------------------------------------------------------- build

# Two app ingredients that are the same substance: names that resolve to both take the INN.
SAME_SUBSTANCE = {frozenset({'levomepromazine', 'methotrimeprazine'}): 'levomepromazine'}


def one(found):
    if not found:
        return None
    if len(found) == 1:
        return next(iter(found))
    return SAME_SUBSTANCE.get(frozenset(found))


class Builder:
    def __init__(self, aps, ext, existing):
        self.aps = aps
        self.ext = ext
        self.existing = existing
        self.index = defaultdict(set)      # ingredient key (Latin, folded) -> canonical
        self.ja_index = defaultdict(set)   # Japanese name key -> canonical
        self.atc = defaultdict(set)        # canonical -> ATC codes
        self.new_aps = {}                  # canonical antipsychotic unknown to the app -> evidence
        self.cand = defaultdict(lambda: defaultdict(set))  # alias -> tier -> {canonical}
        self.meta = {}                     # alias -> (source, language) of first entry
        self.combos = defaultdict(set)     # alias -> sources (combination product containing an antipsychotic)
        self.combo_parts = {}
        self.source_counts = Counter()
        self.source_aliases = defaultdict(set)
        self.overridden = []
        self.votes = defaultdict(Counter)
        for a, t in existing.items():
            if re.search('[a-z]', a):
                self.index[fold(a)].add(t)
        self.names = set(ext['ingredient_class']) | aps
        for name in self.names:
            self.index[fold(name)].add(name)

    # canonical name for a new ingredient string
    def canonical(self, raw):
        key = ingredient_key(raw)
        if key in self.names:
            return key
        found = self.index.get(key) or self.index.get(fold(norm(raw)))
        return one(found)

    def is_ap(self, c):
        return c in self.aps or c in self.new_aps

    def ap_in(self, text):
        t = fold(norm(text))
        return any(re.search(r'\b' + re.escape(a) + r'\b', t) for a in self.aps | set(self.new_aps))

    def add(self, alias, target, tier, source, lang):
        if not target:
            return
        a = norm(alias)
        if not a or is_generic_word(a):
            return
        self.cand[a][tier].add(target)
        self.votes[a][target] += 1
        self.source_aliases[source].add(a)
        if a not in self.meta:
            self.meta[a] = (source, script_language(a, lang))

    def add_combo(self, alias, parts, source):
        a = norm(alias)
        if a and not is_generic_word(a):
            self.combos[a].add(source)
            self.combo_parts.setdefault(a, sorted(parts))

    def product(self, names, ingredients, source, lang, variants=None):
        """Register product names for resolved ingredient strings (canonicals)."""
        ings = [i for i in ingredients if i]
        if not ings:
            return
        uniq = list(dict.fromkeys(ings))
        aliases = set()
        for n in names:
            aliases |= variants(n) if variants else latin_stem(n)
        if any(self.is_ap(i) for i in uniq):
            if len(uniq) > 1:
                for a in aliases:
                    self.add_combo(a, uniq, source)
                return
        target = uniq[0]
        for a in aliases:
            if self.named_after_other(a, target):
                continue  # a product named after another ingredient (data error or lab generic): skip
            self.add(a, target, 2, source, lang)
        self.source_counts[source] += 1

    def named_after_other(self, alias, target):
        words = fold(alias).split()
        for n in (3, 2, 1):
            if len(words) >= n:
                head = ' '.join(words[:n])
                hit = self.index.get(head)
                if head in self.names and head != target:
                    return True
                if hit and target not in hit and len(head) >= 5:
                    return True
                if hit and target in hit:
                    return False
        return False

    def resolve_alias(self):
        aliases, conflicts = {}, []
        for a, tiers in self.cand.items():
            if a in self.existing:
                tiers[0] = {self.existing[a]}  # the app's own alias always wins (never remapped)
            allt = set().union(*tiers.values())
            best = min(tiers)
            top = tiers[best]
            if len(top) > 1 and best <= 1.5:
                # generic-name labels that disagree (Wikidata mislabel): majority of independent labels, 2:1 at least
                ranked = self.votes[a].most_common()
                ranked = [(t, n) for t, n in ranked if t in top]
                if len(ranked) > 1 and ranked[0][1] >= 2 * ranked[1][1]:
                    self.overridden.append((a, ranked[0][0], {k: sorted(v) for k, v in sorted(tiers.items())}))
                    top = {ranked[0][0]}
            ap_involved = any(self.is_ap(t) for t in allt)
            # one ingredient at the most authoritative tier (0 app, 1 main generic label / official generic name,
            # 1.5 Wikidata alias, 2 product name). Product names that disagree and involve an antipsychotic are dropped.
            if len(top) > 1 or (ap_involved and len(allt) > 1 and best >= 2):
                conflicts.append((a, {k: sorted(v) for k, v in sorted(tiers.items())}))
                continue
            if ap_involved and len(allt) > 1:
                self.overridden.append((a, next(iter(top)), {k: sorted(v) for k, v in sorted(tiers.items())}))
            aliases[a] = next(iter(top))
        return aliases, conflicts


def main():
    global CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=DEFAULT_CACHE)
    ap.add_argument('--out', default=str(ROOT / 'lookup/world_names.json'))
    ap.add_argument('--skip', nargs='*', default=[], help='sources to skip: rxnorm sfda dpd ...')
    ap.add_argument('--wordfreq-path', default=str(Path(DEFAULT_CACHE).parent / 'pylib'),
                    help='folder with the wordfreq package (used only to drop everyday words such as "avant")')
    args = ap.parse_args()
    CACHE = Path(args.cache)
    CACHE.mkdir(parents=True, exist_ok=True)
    aps, factor, ext, core, existing = app_names()
    B = Builder(aps, ext, existing)
    sources = {}

    # ---- Wikidata: canonical ingredients + multilingual generic names
    items, nrows = wikidata()
    wd_canon = {}
    for qid, it in items.items():
        if not it['en']:
            continue
        en = norm(it['en'])
        en = re.sub(r'\s*\(.*\)\s*$', '', en)
        if re.search(r'\b(?:and|with|in combination|combinations?)\b|/|,|\+', en) or any(len(c) != 7 for c in it['atc']):
            # combination / class item: brands of combinations that contain an antipsychotic are kept as such
            if any(re.search(r'\b' + re.escape(a) + r'\b', fold(en)) for a in aps) or any(c.startswith('N06C') for c in it['atc']):
                for label, lang in it['labels']:
                    if lang != 'en' or norm(label) != en:
                        B.add_combo(label, [en], 'Wikidata')
            continue
        key = ingredient_key(en)
        c = B.canonical(en) or (key if re.fullmatch(r"[a-z][a-z0-9 '\-]+", key) else None)
        if not c:
            continue
        if c not in aps and any(x.startswith('N05A') for x in it['atc']):
            # the app's spelling of the same antipsychotic (tiotixene -> thiothixene), as in build_external_names
            from rapidfuzz.distance import OSA
            close = [a for a in aps if a[0] == c[0] and OSA.distance(a, c) <= 2]
            if len(close) == 1:
                c = close[0]
                B.index[key].add(c)
        wd_canon[qid] = c
        B.names.add(c)
        B.atc[c] |= it['atc']
    for qid, c in wd_canon.items():
        for label, lang in items[qid]['labels']:
            if lang in ('en', 'fr', 'mul') and re.fullmatch(r"[^\W\d_][\w '\-]+", fold(norm(label))):
                B.index[ingredient_key(label)].add(c)
            if lang == 'ja':
                B.ja_index[ja_ingredient_key(label)].add(c)
    # antipsychotics by ATC that the app does not know yet
    for c, codes in B.atc.items():
        if c not in aps and c != 'lithium' and any(x.startswith('N05A') and not x.startswith('N05AN') for x in codes):
            B.new_aps[c] = 'Wikidata ATC ' + ','.join(sorted(codes))
    for qid, c in wd_canon.items():
        for label, lang in items[qid]['labels']:
            l2 = 'zh' if lang.startswith('zh') else lang if lang in ('ko', 'ja', 'fr', 'ar', 'en') else 'other'
            B.add(label, c, 1 if (label, lang) in items[qid]['main'] else 1.5, 'Wikidata', l2)
        B.add(c, c, 1, 'Wikidata', 'en')
    sources['wikidata'] = {'url': 'https://query.wikidata.org/sparql', 'selection': 'all items with ATC code (P267); '
                           'labels+aliases in ' + ', '.join(WD_LANGS), 'count': len(wd_canon), 'rows': nrows, 'checked': TODAY}
    print('wikidata items', len(wd_canon), 'rows', nrows, flush=True)

    # ---- KEGG DRUG
    entries = kegg()
    kegg_canon = {}
    atc_to_canon = defaultdict(set)
    for c, codes in B.atc.items():
        for code in codes:
            atc_to_canon[code].add(c)
    for e in entries.values():
        if e['mixture']:
            continue
        en_names = [n for n in e['names'] if re.search('[A-Za-z]', n) and not re.search('[ぁ-ヿ一-鿿]', n) and '(TN)' not in n]
        c = None
        for n in en_names:
            c = B.canonical(n)
            if c:
                break
        if not c:
            hits = set().union(*(atc_to_canon.get(x, set()) for x in e['atc'])) if e['atc'] else set()
            if len(hits) == 1:
                c = next(iter(hits))
        if not c and en_names:
            key = ingredient_key(en_names[0])
            if re.fullmatch(r"[a-z][a-z0-9 '\-]+", key) and (e['atc'] or e['jp'] or e['us'] or e['antipsychotic_group']):
                c = key
        if not c:
            continue
        kegg_canon[e['id']] = c
        B.names.add(c)
        B.atc[c] |= set(e['atc'])
        if e['antipsychotic_group'] and c not in aps and c != 'lithium':
            B.new_aps.setdefault(c, f"KEGG DG03200 ({e['id']})")
    for e in entries.values():
        c = kegg_canon.get(e['id'])
        if not c:
            continue
        for n in e['names']:
            if '(TN)' in n:
                continue
            clean = re.sub(r'\s*\([^)]*\)\s*$', '', n)
            if re.search('[ぁ-ヿ一-鿿]', clean):
                B.ja_index[ja_ingredient_key(clean)].add(c)
            else:
                B.index[ingredient_key(clean)].add(c)
    # KEGG antipsychotic group drugs keep their class even when their English name was resolved first
    kegg_jp = Counter()
    for e in entries.values():
        if e['mixture']:
            parts = [kegg_canon.get(i) for i in e['comp_ids']]
            parts = [p for p in parts if p]
            if parts and any(B.is_ap(p) for p in parts) and len(set(parts)) > 1:
                for n in e['jp']:
                    for v in ja_variants(n):
                        B.add_combo(v, parts, 'KEGG')
                for n in e['us'] + [x for x in e['names'] if '(TN)' in x]:
                    for v in latin_stem(re.sub(r'\s*\([^)]*\)\s*$', '', n)):
                        B.add_combo(v, parts, 'KEGG')
                for n in e['names']:
                    if re.search('[ぁ-ヿ一-鿿]', n):
                        B.add_combo(re.sub(r'\s*\([^)]*\)\s*$', '', n), parts, 'KEGG')
            continue
        c = kegg_canon.get(e['id'])
        if not c:
            continue
        for n in e['names']:
            clean = re.sub(r'\s*\([^)]*\)\s*$', '', n).strip(' ;')
            if '(TN)' in n:
                for v in (ja_variants(clean) if re.search('[ぁ-ヿ一-鿿]', clean) else latin_stem(clean)):
                    B.add(v, c, 2, 'KEGG', 'ja' if re.search('[ぁ-ヿ一-鿿]', v) else 'en')
            else:
                B.add(clean, c, 1, 'KEGG', 'ja' if re.search('[ぁ-ヿ一-鿿]', clean) else 'en')
        for n in e['jp']:
            for v in ja_variants(n):
                B.add(v, c, 2, 'KEGG', 'ja')
                kegg_jp[c] += 1
        for n in e['us']:
            for v in latin_stem(re.sub(r'\s*\([^)]*\)\s*$', '', n)):
                B.add(v, c, 2, 'KEGG', 'en')
    sources['kegg'] = {'url': 'https://rest.kegg.jp/ (list/drug_ja, get/dr_ja:*)', 'selection':
                       'all KEGG DRUG entries: generic names (EN/JA), 商品名 incl. 後発品, US products, ATC; DG03200 antipsychotic group',
                       'count': len(kegg_canon), 'entries': len(entries), 'checked': TODAY}
    print('kegg entries', len(entries), 'resolved', len(kegg_canon), flush=True)

    def ja_resolve(name):
        name = unicodedata.normalize('NFKC', str(name))
        parts = [p for p in re.split(r'[・、]', re.sub(r'配合剤$|配合$', '', name)) if p]
        out = []
        for p in parts:
            k = norm(p)
            hit = B.ja_index.get(k) or B.ja_index.get(ja_ingredient_key(p))
            out.append(one(hit))
        return out

    # ---- MHLW NHI price list (Japan)
    if 'mhlw' not in args.skip:
        import pandas as pd
        n_rows = n_ok = 0
        page = decode(fetch('https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000078916.html', 'mhlw/index.html', refresh=True))
        top = re.search(r'href="(https://www\.mhlw\.go\.jp/topics/\d{4}/\d\d/tp\d+-01\.html)"', page)
        listing_url = top.group(1) if top else 'https://www.mhlw.go.jp/topics/2026/04/tp20260401-01.html'
        # current list + the April lists of earlier years (products since delisted still appear in old records)
        listings = [listing_url] + [f'https://www.mhlw.go.jp/topics/{y}/04/tp{y}0401-01.html' for y in range(2025, 2017, -1)]
        files = []
        for url in dict.fromkeys(listings):
            raw = fetch(url, 'mhlw/listing_' + re.sub(r'\W', '_', url.split('/topics/')[1]), refresh=url == listing_url)
            listing = raw.decode('shift_jis', 'replace') if raw else ''
            for kind in ('01', '02', '03'):
                links = re.findall(r'href="(/topics/\d{4}/\d\d/xls/tp\d+-01_%s\.xlsx?)"' % kind, listing)
                if links:
                    files.append('https://www.mhlw.go.jp' + links[0])
        for url in files:
            df = pd.read_excel(io.BytesIO(fetch(url, 'mhlw/' + url.rsplit('/', 1)[1])), dtype=str)
            df.columns = [str(c).replace('\n', '').strip() for c in df.columns]
            if '成分名' not in df or '品名' not in df:
                print('mhlw: unexpected columns', url, list(df.columns)[:10])
                continue
            for r in df[['成分名', '品名']].dropna().drop_duplicates().itertuples(index=False):
                n_rows += 1
                parts = ja_resolve(r[0])
                if not parts or None in parts:
                    continue
                n_ok += 1
                B.product([r[1]], parts, 'MHLW', 'ja', variants=ja_variants)
                for p in set(parts):
                    if len(parts) == 1:
                        B.add(r[0], p, 1, 'MHLW', 'ja')
        sources['mhlw'] = {'url': listing_url, 'files': files, 'selection':
                           '薬価基準収載品目リスト (内用薬, 注射薬, 外用薬): 品名 mapped through 成分名 (KEGG/Wikidata Japanese names)',
                           'count': n_ok, 'rows': n_rows, 'snapshots': sorted(set(re.findall(r'tp(\d{8})', ' '.join(files)))),
                           'checked': TODAY, 'note': 'MHLW (厚生労働省) official list; added in addition to the listed sources'}
        print('mhlw rows', n_rows, 'resolved', n_ok, flush=True)

    # ---- BDPM (France)
    if 'bdpm' not in args.skip:
        prods = bdpm()
        fr_index = defaultdict(set)
        for qid, c in wd_canon.items():
            for label, lang in items[qid]['labels']:
                if lang in ('fr', 'en', 'mul'):
                    fr_index[fr_ingredient_key(label)].add(c)
        def fr_resolve(s):
            k = fr_ingredient_key(s)
            hit = fr_index.get(k)
            if hit and len(hit) == 1:
                return next(iter(hit))
            return B.canonical(k) or B.canonical(s)
        ok = 0
        for name, ings, form in prods:
            parts = [fr_resolve(i) for i in ings]
            if not parts or None in parts:
                continue
            ok += 1
            B.product([name], parts, 'BDPM', 'fr')
            if len(set(parts)) == 1:
                for i in ings:
                    B.add(i, parts[0], 1, 'BDPM', 'fr')
                    B.add(fr_ingredient_key(i), parts[0], 1, 'BDPM', 'fr')
        sources['bdpm'] = {'url': 'https://base-donnees-publique.medicaments.gouv.fr/telechargement',
                           'selection': 'all CIS_bdpm denominations; substances from CIS_COMPO_bdpm (FT preferred over SA)',
                           'count': ok, 'rows': len(prods), 'checked': TODAY}
        print('bdpm', len(prods), ok, flush=True)

    # ---- EMA
    if 'ema' not in args.skip:
        ok = 0
        rows = ema()
        for names, inns, atc in rows:
            parts = [B.canonical(i) for i in inns]
            if not parts or None in parts:
                hits = atc_to_canon.get(atc.strip()) if atc and atc != 'nan' else None
                if hits and len(hits) == 1:
                    parts = [next(iter(hits))]
                else:
                    continue
            ok += 1
            B.product(names, parts, 'EMA', 'en')
        sources['ema'] = {'url': 'https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx',
                          'selection': 'human medicines (all statuses): Name of medicine via INN/common name',
                          'count': ok, 'rows': len(rows), 'checked': TODAY}
        print('ema', len(rows), ok, flush=True)

    # ---- TFDA (Taiwan)
    if 'tfda' not in args.skip:
        ok = 0
        rows = tfda()
        for zh, en, ings, form in rows:
            parts = [B.canonical(i) for i in ings]
            if not parts or None in parts:
                continue
            ok += 1
            B.product([zh], parts, 'TFDA', 'zh', variants=lambda n: zh_variants(n, form))
            B.product([en], parts, 'TFDA', 'en')
        sources['tfda'] = {'url': 'https://data.fda.gov.tw/opendata/exportDataList.do?method=ExportData&InfoId=36&logType=2',
                           'selection': '全部藥品許可證 (incl. cancelled), Chinese-medicine and device licences excluded; 中文品名+英文品名 via 主成分略述',
                           'count': ok, 'rows': len(rows), 'checked': TODAY}
        print('tfda', len(rows), ok, flush=True)

    # ---- Hong Kong
    if 'hk' not in args.skip:
        ok = 0
        rows = hongkong()
        for name, ings in rows:
            parts = [B.canonical(i) for i in ings]
            if not parts or None in parts:
                continue
            ok += 1
            B.product([name], parts, 'HK Drug Office', 'en')
        sources['hk_drug_office'] = {'url': 'https://www.drugoffice.gov.hk/eps/psi/DrugList.xml',
                                     'selection': 'all registered pharmaceutical products (English list)',
                                     'count': ok, 'rows': len(rows), 'checked': TODAY}
        print('hk', len(rows), ok, flush=True)

    # ---- Health Canada DPD
    if 'dpd' not in args.skip:
        ok = 0
        rows = dpd()
        for name, ings in rows:
            parts = []
            for i in ings:
                c = B.canonical(i) or B.canonical(re.sub(r'\(.*?\)', '', i)) or \
                    next((B.canonical(x) for x in re.findall(r'\((.*?)\)', i) if B.canonical(x)), None)
                parts.append(c)
            if not parts or None in parts:
                continue
            ok += 1
            B.product([name], parts, 'Health Canada DPD', 'en')
        sources['health_canada_dpd'] = {'url': 'https://health-products.canada.ca/api/drug/ (drugproduct, activeingredient)',
                                        'selection': 'human products, all statuses returned by the API', 'count': ok,
                                        'rows': len(rows), 'checked': TODAY}
        print('dpd', len(rows), ok, flush=True)

    # ---- SFDA
    if 'sfda' not in args.skip:
        ok = 0
        rows, pages = sfda()
        for name, ings in rows:
            parts = [B.canonical(i) for i in ings]
            if not parts or None in parts:
                continue
            ok += 1
            B.product([name], parts, 'SFDA', 'en')
        sources['sfda'] = {'url': 'https://www.sfda.gov.sa/en/drugs-list', 'selection': f'all {pages} pages of the public drugs list',
                           'count': ok, 'rows': len(rows), 'checked': TODAY}
        print('sfda', len(rows), ok, flush=True)

    # ---- RxNorm brands for every canonical ingredient
    if 'rxnorm' not in args.skip:
        names = sorted({c for c in set(B.atc) | aps | set(B.new_aps)})
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(rxnorm, names))
        ok = 0
        for name, (single, combo) in zip(names, results):
            for b in single:
                B.add(b, name, 2, 'RxNorm', 'en')
                ok += 1
            if B.is_ap(name):
                for b in combo:
                    B.add_combo(b, [name], 'RxNorm')
        sources['rxnorm'] = {'url': 'https://rxnav.nlm.nih.gov/REST/', 'selection':
                             'brand in brackets of SBD/BPCK concepts related to each ingredient (single-ingredient only; combinations with an antipsychotic listed separately)',
                             'count': ok, 'ingredients_queried': len(names), 'checked': TODAY}
        print('rxnorm', ok, flush=True)

    finish(B, sources, args, aps, factor, ext, core, existing)


def finish(B, sources, args, aps, factor, ext, core, existing):
    aliases, conflicts = B.resolve_alias()
    common = common_word_filter(args.wordfreq_path)
    dropped_common = []
    for a in list(aliases):
        tiers = B.cand[a]
        if min(tiers) >= 1.5 and common(a, B.meta[a][1]):
            dropped_common.append((a, aliases.pop(a)))
    # Two-character Chinese product stems of antipsychotics (樂果, 安神, 活潑) are ordinary words or fragments
    # inside other names; they are held for review instead of being matched. Longer forms (樂果膜衣錠) stay.
    short_cjk = {}
    for a in list(aliases):
        if B.is_ap(aliases[a]) and min(B.cand[a]) >= 2 and B.meta[a][1] == 'zh' and len(a) <= 2:
            short_cjk[a] = aliases.pop(a)
    report = {'conflict_ap_vs_other': [], 'conflict_other': 0, 'dropped_existing_ap_mismatch': [],
              'existing_nonap_now_ap': []}
    for a, tiers in conflicts:
        allt = set().union(*map(set, tiers.values()))
        if any(B.is_ap(t) for t in allt):
            report['conflict_ap_vs_other'].append((a, tiers))
        else:
            report['conflict_other'] += 1
    existing_ap = {a: t for a, t in existing.items() if t in aps}
    for a in list(aliases):
        t = aliases[a]
        if a in existing_ap and existing_ap[a] != t:
            report['dropped_existing_ap_mismatch'].append((a, t, existing_ap[a]))
            del aliases[a]
        elif a in existing and existing[a] != t and B.is_ap(t) and existing[a] not in aps:
            report['existing_nonap_now_ap'].append((a, t, existing[a]))
    # combination products: an alias that is a combination anywhere is never a single ingredient
    combos = {}
    for a, srcs in B.combos.items():
        if a in aliases and B.is_ap(aliases[a]):
            continue  # single-ingredient antipsychotic brand also sold in a combination: keep the single mapping
        aliases.pop(a, None)
        combos[a] = B.combo_parts.get(a, [])
    # ingredient classes (antipsychotics never listed)
    old = ext['ingredient_class']
    def cls(c):
        if c in old:
            return old[c]
        if c == 'lithium':
            return 'mood_stabilizer'
        return ben.drug_class(B.atc.get(c, set()), c)
    targets = set(aliases.values())
    ingredient_class = {c: cls(c) for c in sorted(targets) if not B.is_ap(c)}
    for c, v in list(ingredient_class.items()):
        if v == 'antipsychotic':
            B.new_aps.setdefault(c, 'ATC N05A')
            del ingredient_class[c]
    alias_source = {a: B.meta[a][0] for a in aliases}
    alias_language = {a: B.meta[a][1] for a in aliases}
    payload = {
        'built_on': TODAY,
        'policy': ('Public official/reference sources only (Wikidata, KEGG DRUG, MHLW NHI price list, RxNorm, BDPM, EMA, '
                   'Taiwan TFDA, Hong Kong Drug Office, Health Canada DPD, SFDA). Validation prescriptions (Pusan, Jeonbuk, '
                   'Seoul) and any other prescription data are never used. Aliases are NFKC-normalised lowercase.'),
        'sources': sources,
        'aliases': dict(sorted(aliases.items())),
        'alias_source': dict(sorted(alias_source.items())),
        'alias_language': dict(sorted(alias_language.items())),
        'ingredient_class': ingredient_class,
        'antipsychotics_not_in_app': dict(sorted(B.new_aps.items())),
        'antipsychotic_combinations': dict(sorted(combos.items())),
        'review': {
            'conflicts_dropped_ap_vs_other': {a: t for a, t in sorted(report['conflict_ap_vs_other'])},
            'existing_ap_alias_mismatch_dropped': sorted(report['dropped_existing_ap_mismatch']),
            'existing_nonap_alias_mapped_to_ap_here': sorted(report['existing_nonap_now_ap']),
            'dropped_common_words': dict(sorted(dropped_common)),
            'short_chinese_ap_product_stems_held': dict(sorted(short_cjk.items())),
            'ap_alias_kept_by_generic_name_over_product_or_alias': {a: [t, tiers] for a, t, tiers in sorted(B.overridden)},
        },
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    safety(payload, B, aps, report)


def common_word_filter(path):
    """True for a product/alias name that is an everyday word (wordfreq Zipf >= 3.6, e.g. 'avant', 'speed')."""
    if path and path not in sys.path:
        sys.path.insert(0, path)
    try:
        from wordfreq import zipf_frequency, get_frequency_dict, freq_to_zipf
    except ImportError:
        print('WARNING: wordfreq not installed; common-word filter skipped (pip install wordfreq)')
        return lambda a, lang: False
    ja = get_frequency_dict('ja')

    def common(alias, lang):
        if lang in ('en', 'fr') and re.fullmatch(r"[^\W\d_][\w']*", alias):
            return max(zipf_frequency(alias, 'en'), zipf_frequency(alias, 'fr')) >= 3.6
        if lang == 'ja' and alias in ja:
            return freq_to_zipf(ja[alias]) >= 3.6
        return False
    return common


CHECK_NAMES = ['ジプレキサ', '再普乐', '再普樂', 'リスパダール', '维思通', '理思必妥', 'エビリファイ', '安律凡', '博思清', 'セロクエル',
               '思瑞康', 'ゼプリオン', 'ロナセン', 'ルーラン', 'シクレスト', 'レキサルティ', 'ラツーダ', 'zyprexa', 'xeplion',
               'abilify maintena', 'risperdal consta', 'solian', 'leponex', 'haldol',
               # Japanese psychiatric products (coordinator list)
               'ジプレキサザイディス', 'リスパダールコンスタ', 'エビリファイ持続性水懸筋注用', 'ビプレッソ', 'ゼプリオンtri', 'インヴェガ',
               'ロナセンテープ', 'クロザリル', 'セレネース', 'ハロマンス', 'コントミン', 'ウインタミン', 'ヒルナミン', 'レボトミン',
               'ドグマチール', 'アビリット', 'ミラドール', 'グラマリール', 'バルネチール', 'エミレース', 'ノバミン', 'ピーゼットシー',
               'フルメジン', 'フルデカシン', 'オーラップ', 'ニューレプチル', 'クレミン', 'ロドピン', 'アキネトン', 'タスモリン', 'アーテン',
               'デパケン', 'リーマス', 'テグレトール', 'ラミクタール', 'レキソタン', 'デパス', 'ワイパックス', 'リボトリール', 'ランドセン',
               'マイスリー', 'ルネスタ', 'ベルソムラ', 'デエビゴ', 'ロゼレム', 'レンドルミン', 'サイレース']


def safety(p, B, aps, report):
    aliases = p['aliases']
    is_ap = lambda t: t in aps or t in p['antipsychotics_not_in_app']
    print('\n==== SAFETY CHECKS ====')
    # (1) one alias, one ingredient; AP vs other conflicts are dropped
    print(f"(1) aliases mapping to an antipsychotic AND something else across sources: {len(report['conflict_ap_vs_other'])} "
          f"dropped (listed in review.conflicts_dropped_ap_vs_other); non-AP conflicts dropped: {report['conflict_other']}")
    for a, t in sorted(report['conflict_ap_vs_other'])[:60]:
        print('    ', a, t)
    # (2) existing antipsychotic aliases never remapped
    print(f"(2) existing AP aliases (drug_alias.csv / external_names) remapped here -> dropped: {len(report['dropped_existing_ap_mismatch'])}")
    for x in report['dropped_existing_ap_mismatch'][:40]:
        print('    ', x)
    print(f"    existing NON-AP aliases that map to an antipsychotic here (review): {len(report['existing_nonap_now_ap'])}")
    for x in report['existing_nonap_now_ap'][:40]:
        print('    ', x)
    # (3) generic words
    bad = [a for a in aliases if is_generic_word(a)]
    print(f"(3) generic-word aliases remaining: {len(bad)} {bad[:20]}")
    # (4) per-antipsychotic counts by language
    print('(4) antipsychotic aliases per language (ko en ja zh fr ar other | ja product names from KEGG/MHLW)')
    per = defaultdict(Counter)
    jprod = Counter()
    for a, t in aliases.items():
        if is_ap(t):
            per[t][p['alias_language'][a]] += 1
            if p['alias_language'][a] == 'ja' and p['alias_source'][a] in ('KEGG', 'MHLW'):
                jprod[t] += 1
    for t in sorted(aps | set(p['antipsychotics_not_in_app'])):
        c = per[t]
        flag = '' if t in aps else '  [NOT IN APP]'
        print(f"    {t:22s} " + ' '.join(f"{l}={c[l]:<3d}" for l in ('ko', 'en', 'ja', 'zh', 'fr', 'ar', 'other')) +
              f" total={sum(c.values()):<4d} ja_products={jprod[t]:<3d}{flag}")
    # (5) explicit names
    print('(5) explicit names')
    missing = []
    for n in CHECK_NAMES:
        k = norm(n)
        if k in aliases:
            print(f'    OK   {n} -> {aliases[k]} ({p["alias_source"][k]})')
        elif k in p['antipsychotic_combinations']:
            print(f'    COMBO {n} -> {p["antipsychotic_combinations"][k]}')
        else:
            why = 'conflict' if k in p['review']['conflicts_dropped_ap_vs_other'] else \
                'candidate exists' if k in B.cand else 'not in any source'
            print(f'    MISS {n} ({why}; {dict(B.cand.get(k, {}))})')
            missing.append(n)
    lang = Counter(p['alias_language'].values())
    src = Counter(p['alias_source'].values())
    print('aliases', len(aliases), 'by language', dict(lang), 'by first source', dict(src))
    print('antipsychotics not in app:', p['antipsychotics_not_in_app'])
    print('ap combinations:', len(p['antipsychotic_combinations']))


if __name__ == '__main__':
    main()
