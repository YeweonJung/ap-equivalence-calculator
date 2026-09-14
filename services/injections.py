"""WHO route-specific DDD equivalents; never reuse oral factors for depots."""
import math
import re

DEPOT_DDD = {'paliperidone': 2.5, 'aripiprazole': 13.3, 'risperidone': 2.7}
SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AX&showdescription=yes'
CPZ_SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AA01'


def injection_values(frame):
    text = frame['original']
    drug, dose = frame['drug'], frame['dose_mg']
    if drug not in DEPOT_DDD or dose is None or not math.isfinite(dose) or dose <= 0:
        raise ValueError('확인바람: 지원 주사제와 양의 투여용량이 필요합니다.')
    if re.search(r'loading|initiat|초회|부하|day\s*[18]\b|PRN', text, re.I):
        raise ValueError('확인바람: 초기·부하·필요시 주사는 유지요법 DDD로 환산하지 않습니다.')
    if not re.search(r'(?<![a-z])(?:LAI|PP[136]M|depot)(?![a-z0-9])|지속형|데포', text, re.I):
        raise ValueError('확인바람: 지속형 주사제 여부를 명시해 주세요.')
    intervals = []
    for match in re.finditer(r'(?<![a-z])PP([136])M(?![a-z0-9])', text, re.I):
        intervals.append(int(match[1]) * 30)
    for pattern, multiplier in [(r'(?<![a-z])q\s*(\d+)\s*(?:d|days?)(?![a-z])', 1),
                                (r'(?<![a-z])q\s*(\d+)\s*(?:w|wk|weeks?)(?![a-z])', 7),
                                (r'(?<![a-z])q\s*(\d+)\s*(?:mo|months?)(?![a-z])', 30),
                                (r'(\d+)\s*개월', 30), (r'(\d+)\s*주\s*(?:마다|간격)', 7),
                                (r'every\s+(\d+)\s+days?', 1),
                                (r'every\s+(\d+)\s+weeks?', 7),
                                (r'every\s+(\d+)\s+months?', 30)]:
        intervals.extend(int(m[1]) * multiplier for m in re.finditer(pattern, text, re.I))
    if re.search(r'\bmonthly\b|매월', text, re.I):
        intervals.append(30)
    if re.search(r'\bweekly\b|매주', text, re.I):
        intervals.append(7)
    if not intervals or len(set(intervals)) != 1 or intervals[0] <= 0:
        raise ValueError('확인바람: 주사 투여간격이 없거나 서로 다릅니다. PP1M, q4w 등으로 명시해 주세요.')
    warning = '확인바람: 유지요법 주사제 DDD 환산'
    if drug == 'paliperidone':
        # WHO defines the dose as active paliperidone, not palmitate ester mass.
        if re.search(r'palmitate|팔미테이트', text, re.I):
            raise ValueError('확인바람: palmitate 질량을 paliperidone 활성성분 mg으로 확인해 주세요.')
        warning += '; paliperidone 활성성분 mg 기준'
    if any(re.search(p, text, re.I) for p in [r'PP[136]M', r'개월', r'month', r'\d+\s*mo', r'매월']):
        warning += '; 1개월=30일 기준'
    days = intervals[0]
    daily = dose / days
    return dict(interval_days=days, daily_dose_mg=daily,
                injection_cpz_ddd=daily / DEPOT_DDD[drug] * 300,
                conversion_basis='WHO depot DDD', conversion_source=SOURCE,
                warning=warning, needs_review=True)
