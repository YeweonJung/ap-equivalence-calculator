"""Label-strength lookup: never infer ester mass from a molecular-weight ratio."""
import re

PALMITATE = {
    'PP1M': {39: 25, 78: 50, 117: 75, 156: 100, 234: 150},
    'PP3M': {273: 175, 410: 263, 546: 350, 819: 525},
    'PP6M': {1092: 700, 1560: 1000},
}
LAUROXIL = {441: 300, 662: 450, 882: 600, 1064: 724}
PAL_SOURCE = 'https://www.jnjlabels.com/package-insert/product-monograph/prescribing-information/INVEGA%20SUSTENNA-pi.pdf'
ARI_SOURCE = 'https://labeling.alkermes.com/uspi_aristada.pdf'


def normalize_mass(text, drug, dose, profile):
    active, basis, source = dose, 'active moiety mg', ''
    ester = bool(re.search(r'palmitate|팔미테이트|염\s*질량', text, re.I))
    active_mark = bool(re.search(r'active\s*(?:moiety)?|활성성분|mg\s*eq', text, re.I))
    if ester and active_mark:
        raise ValueError('확인바람: 활성성분과 염 질량 표시가 충돌합니다.')
    if drug == 'paliperidone':
        mapping = PALMITATE.get(profile, {})
        brand = bool(re.search(r'sustenna|trinza|hafyera|서스티나|트린자|하피에라', text, re.I))
        if ester or (brand and dose in mapping and not active_mark):
            if dose not in mapping:
                raise ValueError('확인바람: 해당 PP 제형의 palmitate 질량표에 없는 용량입니다.')
            active, basis, source = mapping[dose], 'paliperidone palmitate mg -> active moiety mg', PAL_SOURCE
            if profile != 'PP1M':
                product = 'TRINZA' if profile == 'PP3M' else 'HAFYERA'
                source = PAL_SOURCE.replace('SUSTENNA', product)
    elif profile == 'ARI_LAUROXIL':
        if active_mark or dose not in LAUROXIL:
            raise ValueError('확인바람: Aristada는 등록된 lauroxil 표시량으로 입력해 주세요.')
        active, basis, source = LAUROXIL[dose], 'aripiprazole lauroxil mg -> active moiety mg', ARI_SOURCE
    return dict(input_dose_mg=dose, active_moiety_mg=active, dose_basis=basis, mass_source=source)
