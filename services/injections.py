"""WHO route-specific DDD equivalents; never reuse oral factors for depots."""
import math
import re
from services.lai_support import PRODUCT_RE, BRIDGE_LABEL, profile_for, interval_days, oral_bridge
from services.lai_mass import normalize_mass

OLZ_SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AH03'

DEPOT_DDD = {'paliperidone': 2.5, 'aripiprazole': 13.3, 'risperidone': 2.7, 'olanzapine': 10}
SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AX&showdescription=yes'
CPZ_SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AA01'


def injection_values(frame):
    text = frame['original']
    drug, dose = frame['drug'], frame['dose_mg']
    if re.search(r'(?:mg|㎎)\s*/\s*(?:ml|mL|cc)|농도', text, re.I):
        raise ValueError('확인바람: 농도(mg/mL)는 주사 총용량(mg)이 아닙니다. 총용량을 입력해 주세요.')
    if drug not in DEPOT_DDD or dose is None or not math.isfinite(dose) or dose <= 0:
        raise ValueError('확인바람: 지원 주사제와 양의 투여용량이 필요합니다.')
    if re.search(r'loading|initiat|initio|초회|초기|부하|누락|재시작|missed|restart|day\s*[18]\b|PRN', text, re.I):
        raise ValueError('확인바람: 초기·부하·필요시 주사는 유지요법 DDD로 환산하지 않습니다.')
    if re.search(r'\b(?:QD|BID|TID|QID|QHS|QAM|QOD|daily|q\d+h)\b|매일|1일|하루', text, re.I):
        raise ValueError('확인바람: LAI 투여간격과 일일 복용빈도가 함께 입력되었습니다.')
    if re.search(r'subcutaneous|\bSC\b', text, re.I):
        raise ValueError('확인바람: 에스터 질량 또는 피하 제형은 자동 환산 범위 밖입니다.')
    if not re.search(r'(?<![a-z])(?:LAI|PP[136]M|depot)(?![a-z0-9])|지속형|데포|' + PRODUCT_RE, text, re.I):
        raise ValueError('확인바람: 지속형 주사제 여부를 명시해 주세요.')
    profile = profile_for(text, drug, dose)
    if re.search(r'lauroxil', text, re.I) and profile != 'ARI_LAUROXIL':
        raise ValueError('확인바람: lauroxil은 Aristada 제품명을 명시해 주세요.')
    mass = normalize_mass(text, drug, dose, profile)
    dose = mass['active_moiety_mg']
    days, interval_note = interval_days(text, profile)
    bridge = oral_bridge(drug, dose, days, profile)
    warning = '확인바람: 유지요법 주사제 DDD 환산' + interval_note
    if drug == 'paliperidone':
        warning += '; paliperidone 활성성분 mg 기준'
    if mass['mass_source']:
        warning += f"; 표시량 {mass['input_dose_mg']:g}mg → 활성성분 {dose:g}mg (표시기준 확인)"
    if bridge['oral_equivalent_mg'] is not None:
        warning += '; ' + BRIDGE_LABEL
        if drug == 'olanzapine':
            warning += '; 2개월 이후 유지요법 기준'
    else:
        warning += '; 단일 경구 대응용량 근거 없음: DDD 외 빈칸'
    daily = dose / days
    return dict(interval_days=days, daily_dose_mg=daily, **mass,
                injection_cpz_ddd=daily / DEPOT_DDD[drug] * 300,
                conversion_basis='WHO depot DDD', conversion_source=OLZ_SOURCE if drug == 'olanzapine' else SOURCE, **bridge,
                warning=warning, needs_review=True)
