"""Product-specific oral bridges, not direct LAI CMD/MED/ED95 factors."""
import re

BRIDGE_LABEL = '경구 대응용량 기반 추정 (LAI 직접 환산 아님)'
LABELS = {key: f'https://www.medicines.org.uk/emc/product/{value}/smpc' for key, value in
          {'PP1M': '7652', 'PP3M': '7230', 'PP6M': '13307', 'OLZ_PAMOATE': '15651',
           'RIS_ISM': '13777', 'ARI_2M': '15678'}.items()}
PAL_ORAL = {'PP1M': {25: 3, 50: 3, 75: 6, 100: 9, 150: 12},
            'PP3M': {175: 3, 263: 6, 350: 9, 525: 12}, 'PP6M': {700: 9, 1000: 12}}
OLZ_ORAL = {(150, 14): 10, (300, 28): 10, (210, 14): 15, (405, 28): 15, (300, 14): 20}
PRODUCTS = {'xeplion': ('paliperidone', 'PP1M'), 'trevicta': ('paliperidone', 'PP3M'),
            'byannli': ('paliperidone', 'PP6M'), 'zypadhera': ('olanzapine', 'OLZ_PAMOATE'),
            'okedi': ('risperidone', 'RIS_ISM'), 'maintena': ('aripiprazole', 'ARI_1M')}
PRODUCTS.update({'sustenna': ('paliperidone', 'PP1M'), 'trinza': ('paliperidone', 'PP3M'),
                 'hafyera': ('paliperidone', 'PP6M'), '서스티나': ('paliperidone', 'PP1M'),
                 '트린자': ('paliperidone', 'PP3M'), '하피에라': ('paliperidone', 'PP6M'),
                 'aristada': ('aripiprazole', 'ARI_LAUROXIL'),
                 'asimtufii': ('aripiprazole', 'ARI_2M')})
PRODUCT_RE = r'\b(?:' + '|'.join(PRODUCTS) + r')\b'


def profile_for(text, drug, dose):
    profiles = set(m.group().upper() for m in re.finditer(r'\bPP[136]M\b', text, re.I))
    if profiles and drug != 'paliperidone':
        raise ValueError('확인바람: PP 제형과 약물 성분이 서로 다릅니다.')
    for match in re.finditer(PRODUCT_RE, text, re.I):
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
        if profile == 'RIS_ISM' and dose in (75, 100) and days == 28:
            # 100mg corresponds to oral >=4mg, not a single value.
            if dose == 75:
                oral, source = 3, LABELS[profile]
        elif not profile and dose in (12.5, 25, 37.5, 50) and days == 14:
            profile = 'RIS_MICROSPHERES'
        else:
            raise ValueError('확인바람: risperidone LAI 제품명·용량·간격을 확인해 주세요.')
    return dict(lai_profile=profile, oral_equivalent_mg=oral, oral_bridge_source=source)


def convert_injection(frame, method, target):
    if method == 'DDD' and target == 'chlorpromazine':
        return frame['injection_cpz_ddd']
    if frame.get('oral_equivalent_mg') is None:
        raise LookupError('검증된 단일 경구 대응용량 없음')
    from services.converter import convert_drug
    return convert_drug(frame['drug'], frame['oral_equivalent_mg'], method, target)


def bridge_info_rows():
    rows = []
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
