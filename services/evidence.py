"""Traceable coefficient metadata; evidence design is not a GRADE rating."""
import csv
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026.10.19-evidence-1'
GRADE_NOTE = '정식 GRADE 평가 미실시. 연구 설계를 A~D 등급으로 대체하지 않음.'
COMMON_LIMIT = '연구용 노출 비교값; 임상적 효과·안전성·교체 처방의 동등성을 보장하지 않음'
METHODS = {
    'CMD': ('https://pubmed.ncbi.nlm.nih.gov/25841041/', '2015', '가변용량 임상시험 평균용량', '가변용량 시험의 약물·환자 범위에 한정'),
    'MED': ('https://pubmed.ncbi.nlm.nih.gov/24493852/', '2014', '고정용량 위약대조시험 최소유효용량', '최소 유효용량이며 평균·최적·최대 유효용량과 다름'),
    'ED95': ('https://pubmed.ncbi.nlm.nih.gov/31838873/', '2020', '용량반응 메타분석', '급성기 시험 기반; 개인의 최적 용량이 아님; 저자 TUM 계산기 값(amisulpride는 TUM 값이 없어 논문 537mg 유지)'),
    'DDD': ('https://pmc.ncbi.nlm.nih.gov/articles/PMC4960429/', '2016', 'WHO 약물사용 통계 단위', '권장·처방·임상적 등가 용량이 아님; 경구와 depot DDD 구분'),
    'CPZ_FGA': ('https://pubmed.ncbi.nlm.nih.gov/4156792/', '1974', '역사적 경구 CPZ 비교', '등록된 1세대 약물 범위에 한정'),
    'WOODS': ('https://pubmed.ncbi.nlm.nih.gov/12823080/', '2003', '최소유효용량 기반 CPZ 비교', '원표의 제한된 약물 범위; 미등록 약물 외삽 금지'),
    'GARDNER': ('https://doi.org/10.1176/appi.ajp.2009.09060802', '2010', '국제 전문가 합의 중앙값', '시험 기반 동등성 검증과 구분; 원표 명칭별 중앙값 사용'),
    'CMD_DIRECT': ('https://pubmed.ncbi.nlm.nih.gov/25841041/', '2015', 'CMD 직접 비교 비율', 'CMD와 같은 연구의 비교 분석; 독립된 검증 자료가 아님'),
    'CMD_INDIRECT': ('https://pubmed.ncbi.nlm.nih.gov/25841041/', '2015', 'CMD 직접·간접 비교 비율', 'CMD와 같은 연구의 비교 분석; 독립된 검증 자료가 아님'),
}
METADATA_COLUMNS = ['evidence_source', 'evidence_grade', 'table_version', 'exclusion_conditions']


def method_info():
    return [dict(method=m, source=v[0], publication_year=v[1], evidence_type=v[2],
                 evidence_grade='not_assessed', grade_note=GRADE_NOTE,
                 limitation=v[3], common_limit=COMMON_LIMIT) for m, v in METHODS.items()]


def pair_metadata(method, source, target, anchors):
    info = METHODS[method]
    rows = [anchors[(method, drug)] for drug in (source, target) if (method, drug) in anchors]
    provenance = '; '.join(dict.fromkeys(f"{r['source']} [{r['table']}; {r['version']}]" for r in rows)) or info[0]
    origin = 'anchors:' + ','.join(sorted({r['version'] for r in rows})) if rows else 'legacy-import-preserved'
    conditions = [COMMON_LIMIT, info[3], '경구 계수: LAI 평균 주사량에 직접 적용 금지', '계수 부재는 0이 아님; 방법 간 자동 대체 금지']
    if 'clozapine' in (source, target):
        conditions.append('clozapine: 치료저항성·수용체 특성으로 단순 임상 비교에 한계')
    if {'aripiprazole', 'brexpiprazole', 'cariprazine'} & {source, target}:
        conditions.append('부분작용제: 동일 D2 점유율을 동일 임상 효과로 해석하지 않음')
    return dict(evidence_source=provenance, evidence_grade='not_assessed',
                table_version=f'{method}:{origin}; metadata:{VERSION}',
                exclusion_conditions='; '.join(conditions))


@lru_cache(maxsize=1)
def evidence_index():
    with (ROOT / 'lookup/master_lookup.csv').open(encoding='utf-8-sig', newline='') as stream:
        return {(r['method_id'], r['source_drug'], r['target_drug']):
                {k: r[k] for k in METADATA_COLUMNS} for r in csv.DictReader(stream)}


def conversion_evidence(frame, method, target, available):
    drug = frame.get('drug') or frame.get('parsed')
    result = dict(method=method, source_drug=drug, target_drug=target,
                  available=bool(available), evidence_grade='not_assessed', grade_note=GRADE_NOTE,
                  method_source=METHODS[method][0], evidence_type=METHODS[method][2])
    if frame.get('status') == 'non_target':
        return dict(result, available=True, evidence_type='excluded_non_target', evidence_grade='not_applicable',
                    grade_note='환산 대상 외: 등급 미적용',
                    evidence_source=frame.get('exclusion_basis', ''), calculation_basis='환산 대상 외; 기여값 0')
    result.update(evidence_index().get((method, drug, target), {}))
    if frame.get('route') == 'injection':
        result['calculation_basis'] = 'route_specific_DDD' if method == 'DDD' else 'label_oral_bridge_estimate'
        if method == 'DDD':
            # The ingredient's oral DDD is NOT the coefficient used by a depot.
            result.update(evidence_source=frame.get('conversion_source', ''),
                          table_version=VERSION + '; route-specific depot DDD',
                          exclusion_conditions='제품·유지용량·투여간격·질량기준 확인 필수; 초기·부하·PRN 제외')
            result['reference_scale_evidence'] = evidence_index().get(('DDD', 'chlorpromazine', target), {})
        result.update(product_source=frame.get('product_name_source', ''),
                      mass_source=frame.get('mass_source', ''), oral_bridge_source=frame.get('oral_bridge_source', ''),
                      interval_days=frame.get('interval_days'), dose_basis=frame.get('dose_basis'),
                      active_moiety_mg=frame.get('active_moiety_mg'),
                      month_assumption='월 표기는 30일; WHO 규칙이 아닌 앱 연구 가정. q4w는 28일.')
    else:
        result['calculation_basis'] = 'oral_method_coefficient'
    if not available:
        result['unavailable_reason'] = '계수·제형별 근거 또는 입력 확정 부족; 다른 방법으로 자동 대체하지 않음'
    return result


def attach_evidence(item, methods):
    from services.converter import DEFAULT_TARGETS
    for conversion in item.get('conversions', []):
        conversion['evidence'] = conversion_evidence(item, conversion['method'], conversion['target'], conversion['value'] is not None)
    by_method = {c['method']: c['evidence'] for c in item.get('conversions', [])}
    item['factor_evidence'] = json.dumps([by_method[m] if m in by_method else
        conversion_evidence(item, m, DEFAULT_TARGETS[m], False) for m in methods], ensure_ascii=False)
    item['match_confidence_basis'] = ('unresolved' if not item.get('drug') else
                                    'review_required' if item.get('needs_review') else 'dictionary_and_input_rules')
    return item


def dated_evidence(record, methods):
    from services.converter import DEFAULT_TARGETS, convert_drug
    from services.lai_support import convert_injection
    frame = record.get('injection_frame') or dict(drug=record['canonical'], route='oral',
                                                 status=record['kind'], daily_dose_mg=record['daily_mg'])
    output = []
    for method in methods:
        available = False
        if not record['issues'] and record['kind'] == 'ready':
            try:
                if record.get('injection_frame'):
                    convert_injection(frame, method, DEFAULT_TARGETS[method])
                else:
                    convert_drug(record['canonical'], record['daily_mg'], method)
                available = True
            except (LookupError, ValueError):
                pass
        output.append(conversion_evidence(frame, method, DEFAULT_TARGETS[method], available))
    return json.dumps(output, ensure_ascii=False)
