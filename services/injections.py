"""WHO route-specific DDD equivalents; never reuse oral factors for depots."""
import math
import re
import unicodedata
from services.lai_support import PRODUCT_RE, BRIDGE_LABEL, REVIEW_PROFILES, PP_BY_DAYS, PAL_ORAL, profile_for, interval_days, oral_bridge
from services.lai_mass import normalize_mass

OLZ_SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AH03'

DEPOT_DDD = {'paliperidone': 2.5, 'aripiprazole': 13.3, 'risperidone': 2.7, 'olanzapine': 10, 'haloperidol': 3.3}
HAL_SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AD01'
SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AX&showdescription=yes'
INTERVAL_TOKEN_RE = re.compile(r'\bq\s*\d|\d\s*(?:개월|주|일\s*(?:마다|간격))|\bevery\s+\d|\b(?:monthly|weekly)\b|매월|매주', re.I)
CPZ_SOURCE = 'https://atcddd.fhi.no/atc_ddd_index/?code=N05AA01'

# Product label: total mass followed by syringe volume, not a dose multiplier.
LABEL_VOLUME_RE = re.compile(
    r'(?:mg)\s*(?:/\s*|\(\s*|\s+)(?P<volume>\d+(?:\.\d+)?)\s*ml\b',
    re.I,
)


def injection_values(frame):
    text = unicodedata.normalize('NFKC', frame['original'])
    volume_match = LABEL_VOLUME_RE.search(text)
    volume_ml = float(volume_match['volume']) if volume_match else None
    drug, dose = frame['drug'], frame['dose_mg']
    profile = profile_for(text, drug, dose)
    if profile in REVIEW_PROFILES:
        raise ValueError('확인바람: 제품명·성분은 확인했으나 이 제품·제형의 환산은 지원하지 않습니다. 경구 또는 다른 주사제 계수를 적용하지 않습니다.')
    if re.search(r'(?:mg|㎎)\s*/\s*(?:ml|mL|cc)|농도', text, re.I):
        raise ValueError('확인바람: 농도(mg/mL)는 주사 총용량(mg)이 아닙니다. 총용량을 입력해 주세요.')
    if drug not in DEPOT_DDD or dose is None or not math.isfinite(dose) or dose <= 0:
        raise ValueError('확인바람: 지원 주사제와 양의 투여용량이 필요합니다.')
    if re.search(r'loading|initiat|initio|초회|초기|부하|누락|재시작|missed|restart|day\s*[18]\b|PRN', text, re.I):
        raise ValueError('확인바람: 초기·부하·필요시 주사는 유지요법 DDD로 환산하지 않습니다.')
    if re.search(r'\b(?:QD|BID|TID|QID|QHS|QAM|QOD|daily|q\d+h)\b|매일|(?<!\d)1일(?!\s*(?:간격|마다))|하루', text, re.I):
        raise ValueError('확인바람: LAI 투여간격과 일일 복용빈도가 함께 입력되었습니다.')
    profile = profile_for(text, drug, dose)
    if drug == 'haloperidol' and re.search(r'ester|염\s*질량|에스터', text, re.I):
        raise ValueError('확인바람: haloperidol base 표시량으로 입력해 주세요. 에스터 질량을 역산하지 않습니다.')
    is_sc = profile in ('RIS_UZEDY', 'RIS_PERSERIS', 'RIS_LONGAVO')
    if re.search(r'\b(?:oral|tablet|capsule|PO)\b|경구|정제|캡슐', text, re.I):
        raise ValueError('확인바람: 주사 제품명과 경구 투여 표기가 충돌합니다.')
    if re.search(r'\bIV\b|intravenous|정맥', text, re.I):
        raise ValueError('확인바람: 정맥 주사는 지속형 유지요법 환산 대상이 아닙니다.')
    if (is_sc and re.search(r'\bIM\b|intramuscular|근육', text, re.I)) or (
            not is_sc and re.search(r'subcutaneous|\bSC\b|피하', text, re.I)):
        raise ValueError('확인바람: 제품명과 주사 투여경로를 확인해 주세요.')
    # Ester salts are depot by definition; paliperidone and aripiprazole 300/400 mg exist only as long-acting injections.
    only_long_acting = drug == 'paliperidone' or (drug == 'aripiprazole' and dose in (300, 400))
    if not only_long_acting and not re.search(
            r'(?<![a-z])(?:LAI|PP[136]M|depot|palmitate|decanoate|enanthate|pamoate|lauroxil)(?![a-z0-9])|지속형|데포|' + PRODUCT_RE, text, re.I):
        raise ValueError('확인바람: 지속형 주사제 여부를 명시해 주세요.')
    profile = profile_for(text, drug, dose)
    if re.search(r'lauroxil', text, re.I) and profile != 'ARI_LAUROXIL':
        raise ValueError('확인바람: lauroxil은 Aristada 제품명을 명시해 주세요.')
    mass = normalize_mass(text, drug, dose, profile)
    dose = mass['active_moiety_mg']
    assumed_note = ''
    if not profile and not INTERVAL_TOKEN_RE.search(text):
        # Neither product nor interval recorded (2026-10-29 study rule): these strengths are once-monthly regimens.
        if drug == 'aripiprazole' and dose in (300, 400):
            profile, assumed_note = 'ARI_1M', '; 제품명·투여간격 기록 없음: aripiprazole 월 1회 제형으로 가정'
        elif drug == 'paliperidone' and dose in PAL_ORAL['PP1M']:
            profile, assumed_note = 'PP1M', '; 제품명·투여간격 기록 없음: paliperidone 월 1회(PP1M)로 가정'
        elif drug == 'paliperidone' and dose in PAL_ORAL['PP3M']:
            # 175/263/350/525 mg eq. exist only as the 3-monthly product, 700/1000 mg only as the 6-monthly one.
            profile, assumed_note = 'PP3M', '; 제품명·투여간격 기록 없음: 3개월 제형에만 있는 용량이라 PP3M으로 가정'
        elif drug == 'paliperidone' and dose in PAL_ORAL['PP6M']:
            profile, assumed_note = 'PP6M', '; 제품명·투여간격 기록 없음: 6개월 제형에만 있는 용량이라 PP6M으로 가정'
    days, interval_note = interval_days(text, profile)
    interval_note += assumed_note
    if drug == 'paliperidone' and not profile and days in PP_BY_DAYS:
        # Unbranded "paliperidone LAI q4w": written mg is active moiety (mass check above found no ester).
        profile = PP_BY_DAYS[days]
        interval_note += f'; 투여간격으로 {profile} 제형 판단'
    bridge = oral_bridge(drug, dose, days, profile)
    if bridge['oral_bridge_source'] and frame.get('product_name_source'):
        bridge['oral_bridge_source'] = '; '.join(dict.fromkeys(
            [frame['product_name_source'], bridge['oral_bridge_source']]))
    warning = '유지요법 주사제 DDD 환산' + interval_note
    if volume_ml is not None:
        warning += f'; 주사액 부피 {volume_ml:g}mL는 용량 계산에서 제외, 표시 용량 {frame["dose_mg"]:g}mg 사용'
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
    return dict(interval_days=days, daily_dose_mg=daily, injection_volume_ml=volume_ml, interval_assumed='가정' in interval_note, **mass,
                injection_cpz_ddd=daily / DEPOT_DDD[drug] * 300,
                conversion_basis='WHO depot DDD', conversion_source=OLZ_SOURCE if drug == 'olanzapine' else HAL_SOURCE if drug == 'haloperidol' else SOURCE, **bridge,
                calculation_note=warning, warning='', needs_review=False)
