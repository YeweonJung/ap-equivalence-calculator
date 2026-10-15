"""Validate explicit LAI source fields without using days-supply as an interval."""
from services.injections import injection_values
from services.lai_mass import normalize_mass
from services.lai_support import profile_for, product_evidence
from services.parser import DOSE_RE, _dose_to_mg


def prepare_injection(drug_text, product_text, canonical):
    text = ' '.join(filter(None, (drug_text, product_text)))
    amounts = []
    for raw in (drug_text, product_text):
        doses = list(DOSE_RE.finditer(raw))
        if len(doses) > 1:
            raise ValueError('확인바람: 원본 필드에 여러 주사 용량이 있습니다.')
        if doses:
            match = doses[0]
            amounts.append((raw, _dose_to_mg(float(match['dose']), match['unit'])))
    if not amounts:
        raise ValueError('확인바람: 단위가 명시된 주사 총용량이 필요합니다.')
    dose = amounts[0][1]
    profile = profile_for(text, canonical, dose)
    same_label_dose = len({amount for _, amount in amounts}) == 1
    normalized = [normalize_mass(text if same_label_dose else raw, canonical, amount, profile)['active_moiety_mg']
                  for raw, amount in amounts]
    if len(set(normalized)) != 1:
        raise ValueError('확인바람: 성분 필드와 제품 필드의 주사 총용량이 다릅니다.')
    # Use the dose-bearing field's mass notation; other text supplies the
    # product/route/interval and is still checked for conflicts by injection_values.
    frame = dict(original=text, drug=canonical, dose_mg=dose, route='injection',
                 status='ready', match_type='exact', **product_evidence(text))
    frame.update(injection_values(frame))
    if frame['active_moiety_mg'] != normalized[0]:
        raise ValueError('확인바람: 두 필드의 주사 표시량 기준이 서로 다릅니다.')
    return frame
