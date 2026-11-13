"""Label-strength lookup: never infer ester mass from a molecular-weight ratio."""
import re

PALMITATE = {
    'PP1M': {39: 25, 78: 50, 117: 75, 156: 100, 234: 150},
    'PP3M': {273: 175, 410: 263, 546: 350, 819: 525},
    'PP6M': {1092: 700, 1560: 1000},
}
LAUROXIL = {441: 300, 662: 450, 882: 600, 1064: 724}
# Korean ingredient fields give aripiprazole monohydrate mass (MFDS/health.kr, checked 2026-11-13).
ARI_MONOHYDRATE = {312: 300, 416: 400, 748.8: 720, 998.4: 960}
# Korean listings of Invega Trinza/Hafyera name only the prefilled-syringe volume (health.kr/HIRA, checked 2026-11-13).
FILL_VOLUME = {'PP3M': {0.875: 175, 1.315: 263, 1.75: 350, 2.625: 525}, 'PP6M': {3.5: 700, 5.0: 1000}}
_FILL_PRODUCT = {'PP3M': r'trinza|트린자|trevicta', 'PP6M': r'hafyera|하피에라|byannli'}


def fill_volume_strength(text):
    """'인베가트린자주사 (1.75mL)' -> add '350mg' when no mg strength is written; unknown volumes are left alone."""
    if re.search(r'\d\s*(?:mg|㎎)', text, re.I):
        return text
    for profile, pattern in _FILL_PRODUCT.items():
        if re.search(pattern, text, re.I):
            match = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*ml\b', text, re.I)
            if match and float(match[1]) in FILL_VOLUME[profile]:
                return text + f' {FILL_VOLUME[profile][float(match[1])]}mg'
    return text
PAL_SOURCE = 'https://www.jnjlabels.com/package-insert/product-monograph/prescribing-information/INVEGA%20SUSTENNA-pi.pdf'
ARI_SOURCE = 'https://labeling.alkermes.com/uspi_aristada.pdf'


def normalize_mass(text, drug, dose, profile):
    active, basis, source = dose, 'active moiety mg', ''
    ester = bool(re.search(r'palmitate|팔미테이트|염\s*질량', text, re.I))
    active_mark = bool(re.search(r'active\s*(?:moiety)?|활성성분|mg\s*eq', text, re.I))
    if ester and active_mark:
        raise ValueError('확인바람: 활성성분과 염 질량 표시가 충돌합니다.')
    if drug == 'paliperidone':
        # No product written: the once-monthly table (the only one whose strengths are then assumed).
        mapping = PALMITATE.get(profile, {}) if profile else PALMITATE['PP1M']
        brand = bool(re.search(r'sustenna|trinza|hafyera|erzofri|서스티나|트린자|하피에라', text, re.I))
        if ester and not profile and dose not in mapping and dose in mapping.values():
            # "paliperidone palmitate 150 mg" is how label strengths (mg eq.) are usually written.
            return dict(input_dose_mg=dose, active_moiety_mg=dose, mass_source=PAL_SOURCE,
                        dose_basis='palmitate 표기이나 질량표에 없고 표시 용량(mg eq.)과 같아 활성성분 mg으로 해석')
        if ester or (brand and dose in mapping and not active_mark):
            if dose not in mapping:
                raise ValueError('확인바람: 해당 PP 제형의 palmitate 질량표에 없는 용량입니다.')
            active, basis, source = mapping[dose], 'paliperidone palmitate mg -> active moiety mg', PAL_SOURCE
            if profile != 'PP1M':
                product = 'TRINZA' if profile == 'PP3M' else 'HAFYERA'
                source = PAL_SOURCE.replace('SUSTENNA', product)
    elif drug == 'aripiprazole' and profile != 'ARI_LAUROXIL' and dose in ARI_MONOHYDRATE and (
            ester or re.search(r'monohydrate|일수화물|水和物', text, re.I) or profile in ('ARI_1M', 'ARI_2M')):
        active, basis, source = ARI_MONOHYDRATE[dose], 'aripiprazole monohydrate mg -> aripiprazole mg', 'https://nedrug.mfds.go.kr/'
    elif profile == 'ARI_LAUROXIL':
        if active_mark or dose not in LAUROXIL:
            raise ValueError('확인바람: Aristada는 등록된 lauroxil 표시량으로 입력해 주세요.')
        active, basis, source = LAUROXIL[dose], 'aripiprazole lauroxil mg -> active moiety mg', ARI_SOURCE
    return dict(input_dose_mg=dose, active_moiety_mg=active, dose_basis=basis, mass_source=source)
