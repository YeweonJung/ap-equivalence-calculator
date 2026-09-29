"""Product-specific oral bridges, not direct LAI CMD/MED/ED95 factors."""
import re
import json
from pathlib import Path

BRIDGE_LABEL = '경구 대응용량 기반 추정 (LAI 직접 환산 아님)'
LABELS = {key: f'https://www.medicines.org.uk/emc/product/{value}/smpc' for key, value in
          {'PP1M': '7652', 'PP3M': '7230', 'PP6M': '13307', 'OLZ_PAMOATE': '15651',
           'RIS_ISM': '13777', 'ARI_2M': '15678'}.items()}
PAL_ORAL = {'PP1M': {25: 3, 50: 3, 75: 6, 100: 9, 150: 12},
            'PP3M': {175: 3, 263: 6, 350: 9, 525: 12}, 'PP6M': {700: 9, 1000: 12}}
OLZ_ORAL = {(150, 14): 10, (300, 28): 10, (210, 14): 15, (405, 28): 15, (300, 14): 20}
LABELS.update({
    'RIS_UZEDY': 'https://www.uzedy.com/globalassets/uzedy/prescribing-information.pdf',
    'RIS_PERSERIS': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a4f21b1a-5691-4b14-a56d-651962d06f39',
    'RIS_MICROSPHERES': 'https://www.jnjlabels.com/package-insert/product-monograph/prescribing-information/RISPERDAL%20CONSTA-pi.pdf',
})
# Product label oral-dose correspondence; not direct LAI equivalence factors.
RIS_SC_ORAL = {
    'RIS_UZEDY': {(50, 30): 2, (75, 30): 3, (100, 30): 4, (125, 30): 5,
                  (100, 60): 2, (150, 60): 3, (200, 60): 4, (250, 60): 5},
    'RIS_PERSERIS': {(90, 30): 3, (120, 30): 4},
}
PRODUCTS = {'xeplion': ('paliperidone', 'PP1M'), 'trevicta': ('paliperidone', 'PP3M'),
            'byannli': ('paliperidone', 'PP6M'), 'zypadhera': ('olanzapine', 'OLZ_PAMOATE'),
            'okedi': ('risperidone', 'RIS_ISM'), 'maintena': ('aripiprazole', 'ARI_1M')}
PRODUCTS.update({'sustenna': ('paliperidone', 'PP1M'), 'trinza': ('paliperidone', 'PP3M'),
                 'hafyera': ('paliperidone', 'PP6M'), '서스티나': ('paliperidone', 'PP1M'),
                 '트린자': ('paliperidone', 'PP3M'), '하피에라': ('paliperidone', 'PP6M'),
                 'aristada': ('aripiprazole', 'ARI_LAUROXIL'),
                 'asimtufii': ('aripiprazole', 'ARI_2M')})
PRODUCTS.update({'uzedy': ('risperidone', 'RIS_UZEDY'),
                 'perseris': ('risperidone', 'RIS_PERSERIS'),
                 'consta': ('risperidone', 'RIS_MICROSPHERES')})
LEGACY_PRODUCTS = PRODUCTS.copy()

# Explicit spelling aliases only: never fuzzy-match a product or infer its interval.
_PRODUCT_NAMES = {
    'sustenna': ['invega sustenna', '인베가 서스티나'],
    'trinza': ['invega trinza', '인베가 트린자'],
    'hafyera': ['invega hafyera'],
    'maintena': ['abilify maintena', '아빌리파이 메인테나', '메인테나'],
    'asimtufii': ['abilify asimtufii'],
    'consta': ['risperdal consta', '리스페달 콘스타', '콘스타'],
}
for _product, _names in _PRODUCT_NAMES.items():
    for _name in _names:
        for _variant in {_name, _name.replace(' ', ''), _name.replace(' ', '-')}:
            PRODUCTS[_variant] = PRODUCTS[_product]
# Korean prescription exports commonly append the dosage-form suffix.
for _name, _identity in list(PRODUCTS.items()):
    if re.search('[가-힣]', _name):
        for _suffix in ('주', '주사', ' 주', ' 주사'):
            PRODUCTS[_name + _suffix] = _identity
# Load the reviewed catalog once; requests never search the web or call AI.
NAME_CATALOG = json.loads((Path(__file__).resolve().parents[1] /
                           'lookup/injection_product_names.json').read_text(encoding='utf-8'))
NAME_EVIDENCE = {}
REVIEW_PROFILES = set()
for _record in NAME_CATALOG:
    if _record['policy'] == 'review':
        REVIEW_PROFILES.add(_record['profile'])
    for _name in _record['aliases']:
        _variants = {_name, _name.replace(' ', ''), _name.replace(' ', '-')}
        for _variant in sorted(_variants):
            _suffixes = ('', '주', '주사', ' 주', ' 주사') if re.search('[가-힣]', _variant) else (('',) if re.search(r'(?:injection|inj\.?)$', _variant) else ('', ' injection', ' inj', ' inj.'))
            for _suffix in _suffixes:
                _alias = _variant + _suffix
                _identity = (_record['drug'], _record['profile'])
                if _alias in PRODUCTS and PRODUCTS[_alias] != _identity:
                    raise ValueError('Conflicting injection product alias: ' + _alias)
                PRODUCTS[_alias] = _identity
                NAME_EVIDENCE[_alias] = _record
PRODUCT_RE = (r'(?<![\w])(?:' + '|'.join(re.escape(name) for name in
              sorted(PRODUCTS, key=len, reverse=True)) + r')(?![a-z가-힣])')
PRODUCT_PATTERN = re.compile(PRODUCT_RE, re.I)


def product_evidence(text):
    records = [NAME_EVIDENCE[m.group().lower()] for m in PRODUCT_PATTERN.finditer(text)
               if m.group().lower() in NAME_EVIDENCE]
    if not records:
        return {}
    evidence = dict(recognized_product='; '.join(dict.fromkeys(r['product'] for r in records)),
                    product_name_source='; '.join(dict.fromkeys(r['source'] for r in records)),
                    product_name_checked_on='2026-09-28')
    profiles = {r['profile'] for r in records}
    if len(profiles) == 1:
        evidence['lai_profile'] = next(iter(profiles))
    return evidence


def profile_for(text, drug, dose):
    profiles = set(m.group().upper() for m in re.finditer(r'\bPP[136]M\b', text, re.I))
    if profiles and drug != 'paliperidone':
        raise ValueError('확인바람: PP 제형과 약물 성분이 서로 다릅니다.')
    for match in PRODUCT_PATTERN.finditer(text):
        expected, profile = PRODUCTS[match.group().lower()]
        if drug != expected:
            raise ValueError('확인바람: 약물 성분과 제품명이 서로 다릅니다.')
        profiles.add(profile)
    if len(profiles) > 1:
        raise ValueError('확인바람: 서로 다른 LAI 제품이 함께 입력되었습니다.')
    profile = next(iter(profiles), '')
    if drug == 'aripiprazole' and dose in (720, 960):
        if profile and profile != 'ARI_2M':
            raise ValueError('확인바람: 720/960mg은 2개월 제형을 확인해 주세요.')
        profile = 'ARI_2M'
    return profile


def interval_days(text, profile):
    # Whole numeric tokens prevent 1.5 months being read as 5 months.
    number = r'(?<![\d.+-])([+-]?(?:\d+(?:\.\d+)?|\.\d+))(?![\d.])'
    intervals = []
    for pattern, unit in [(r'\bq\s*' + number + r'\s*(?:d|days?)(?![a-z])', 'day'),
                          (r'\bq\s*' + number + r'\s*(?:w|wk|weeks?)(?![a-z])', 'week'),
                          (r'\bq\s*' + number + r'\s*(?:mo|months?)(?![a-z])', 'month'),
                          (number + r'\s*개월', 'month'), (number + r'\s*주\s*(?:마다|간격)', 'week'),
                          (r'\bevery\s+' + number + r'\s+days?\b', 'day'),
                          (r'\bevery\s+' + number + r'\s+weeks?\b', 'week'),
                          (r'\bevery\s+' + number + r'\s+months?\b', 'month')]:
        for match in re.finditer(pattern, text, re.I):
            value = float(match[1])
            if not value.is_integer() or value <= 0:
                raise ValueError('확인바람: 소수·음수·0 투여간격은 자동 환산하지 않습니다.')
            intervals.append((int(value), unit))
    if re.search(r'\bmonthly\b|매월', text, re.I):
        intervals.append((1, 'month'))
    if re.search(r'\bweekly\b|매주', text, re.I):
        intervals.append((1, 'week'))
    if profile.startswith('PP'):
        intervals.append((int(profile[2]), 'month'))
    elif profile == 'RIS_ISM':
        intervals.append((28, 'day'))
    days = [56 if profile == 'ARI_2M' and n == 2 and u == 'month' else n * {'day': 1, 'week': 7, 'month': 30}[u] for n, u in intervals]
    if not days or len(set(days)) != 1:
        raise ValueError('확인바람: 주사 투여간격이 없거나 서로 다릅니다. PP1M, q4w 등으로 명시해 주세요.')
    note = ''
    if any(u == 'month' for _, u in intervals):
        note = '; 2개월=56일 제품 기준' if profile == 'ARI_2M' else '; 1개월=30일 연구 기준'
    return days[0], note


def oral_bridge(drug, dose, days, profile):
    oral, source = None, ''
    if drug == 'paliperidone':
        if profile not in PAL_ORAL or dose not in PAL_ORAL[profile]:
            raise ValueError('확인바람: PP 제형과 paliperidone 활성성분 용량을 확인해 주세요. 에스터 용량을 추정하지 않습니다.')
        oral = PAL_ORAL[profile][dose]
        source = '; '.join(dict.fromkeys([LABELS[profile], LABELS['PP1M']]))
    elif drug == 'olanzapine':
        if (dose, days) not in OLZ_ORAL:
            raise ValueError('확인바람: olanzapine pamoate 유지요법 용량·간격을 확인해 주세요.')
        profile = 'OLZ_PAMOATE'
        oral, source = OLZ_ORAL[(dose, days)], LABELS[profile]
    elif drug == 'aripiprazole':
        if profile == 'ARI_LAUROXIL':
            from services.lai_mass import ARI_SOURCE
            mapping = {(300, 30): 10, (450, 30): 15, (600, 42): 15, (724, 60): 15,
                       (600, 30): None}
            if (dose, days) not in mapping:
                raise ValueError('확인바람: Aristada 표시용량과 유지 투여간격을 확인해 주세요.')
            return dict(lai_profile=profile, oral_equivalent_mg=mapping[(dose, days)], oral_bridge_source=ARI_SOURCE)
        if not ((dose in (300, 400) and days in (28, 30)) or (dose in (720, 960) and days == 56)):
            raise ValueError('확인바람: aripiprazole LAI 제형·용량·간격을 확인해 주세요.')
        profile = profile or 'ARI_1M'
    elif drug == 'risperidone':
        if profile in RIS_SC_ORAL:
            if (dose, days) not in RIS_SC_ORAL[profile]:
                raise ValueError('확인바람: 피하 주사 제품별 유지용량과 투여간격을 확인해 주세요.')
            oral, source = RIS_SC_ORAL[profile][dose, days], LABELS[profile]
        elif profile == 'RIS_ISM' and dose in (75, 100) and days == 28:
            # 100mg corresponds to oral >=4mg, not a single value.
            if dose == 75:
                oral, source = 3, LABELS[profile]
        elif profile in ('', 'RIS_MICROSPHERES') and dose in (12.5, 25, 37.5, 50) and days == 14:
            profile = 'RIS_MICROSPHERES'
            source = LABELS[profile]
        else:
            raise ValueError('확인바람: risperidone LAI 제품명·용량·간격을 확인해 주세요.')
    return dict(lai_profile=profile, oral_equivalent_mg=oral, oral_bridge_source=source)


def convert_injection(frame, method, target):
    if method == 'DDD':
        # Preserve depot DDD; re-express its reference without an oral bridge.
        from services.converter import convert_drug
        return convert_drug('chlorpromazine', frame['injection_cpz_ddd'], 'DDD', target)
    if frame.get('oral_equivalent_mg') is None:
        raise LookupError('검증된 단일 경구 대응용량 없음')
    from services.converter import convert_drug
    return convert_drug(frame['drug'], frame['oral_equivalent_mg'], method, target)


def bridge_info_rows():
    rows = []
    for profile, mapping in RIS_SC_ORAL.items():
        for (dose, days), oral in mapping.items():
            rows.append(dict(method='oral bridge', drug='risperidone', profile=profile,
                             dose_mg=dose, interval_days=days, oral_equivalent_mg=oral,
                             basis=BRIDGE_LABEL, source=LABELS[profile]))
    for profile, mapping in PAL_ORAL.items():
        for dose, oral in mapping.items():
            rows.append(dict(method='oral bridge', drug='paliperidone', profile=profile,
                             dose_mg=dose, interval_days=int(profile[2])*30, oral_equivalent_mg=oral,
                             basis=BRIDGE_LABEL, source='; '.join(dict.fromkeys([LABELS[profile], LABELS['PP1M']]))))
    for (dose, days), oral in OLZ_ORAL.items():
        rows.append(dict(method='oral bridge', drug='olanzapine', profile='OLZ_PAMOATE', dose_mg=dose,
                         interval_days=days, oral_equivalent_mg=oral, basis=BRIDGE_LABEL + '; 2개월 이후 유지요법', source=LABELS['OLZ_PAMOATE']))
    rows.append(dict(method='oral bridge', drug='risperidone', profile='RIS_ISM', dose_mg=75,
                     interval_days=28, oral_equivalent_mg=3, basis=BRIDGE_LABEL, source=LABELS['RIS_ISM']))
    return rows
