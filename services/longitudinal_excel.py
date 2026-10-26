from services.exclusions import INGREDIENTS as EXCLUDED_INGREDIENTS, CLASSES, exclusion_label, exclusion_basis, review_fields
"""Compact, streaming Excel output for date-aware prescriptions."""
import csv
import io
import json
import math
from itertools import groupby

from xlsxwriter import Workbook

from services.result_summary import PATIENT_METHOD_ORDER, TARGETS
from services.result_status import classify, combine, COLUMNS, HEADERS, add_legend, display_value

MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
FILENAME = 'AP_equivalence_results.xlsx'
REASONS = {
    'overlapping_orders': '처방기간 중첩', 'same_day_multiple_orders': '같은 날 여러 처방',
    'duplicate_candidate': '동일 처방 반복', 'invalid_date': '처방일 확인',
    'invalid_days': '처방일수 확인', 'invalid_daily_tablets': '하루 정 수 확인',
    'missing_patient': '환자 ID 누락', 'unknown_drug': '약물명 확인',
    'unresolved_drug': '약물 확인', 'ingredient_conflict': '성분 불일치',
    'strength_conflict': '함량 불일치', 'strength_missing': '함량 누락',
    'product_strength_missing': '제품 함량 확인', 'release_form_conflict': '서방 여부 불일치',
    'oral_solid_unconfirmed': '경구 정제·캡슐 여부 확인',
    'unsupported_route': '경피제·패치는 제형별 환산 근거 확인 필요',
    'injection_requires_review': '주사제 투여 정보 확인', 'variable_schedule': '복용 일정 확인',
    'missing_factor': '환산 계수 없음',
    'injection_quantity_ambiguous': '주사 수량 확인: 하루 정 수를 주사 용량에 곱하지 않음',
}


def reason_text(codes):
    return ' · '.join(REASONS.get(c, c) for c in sorted(set(codes)) if c)


def export_excel(records, results, details, metadata):
    out = io.BytesIO()
    wb = Workbook(out, {'constant_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False})
    from services.output_overview import dated_overview, add_xlsxwriter
    date_label = '처방일' if metadata.get('policy') == 'prescription_date' else '기준일'
    from services.supplemented import append_dated_sheets
    append_dated_sheets(wb, details, results, date_label, metadata.get('base_method'), records)
    overview_sheet = wb.add_worksheet('Results')
    overview_codes = {}
    wb.set_properties({'title': '환자별 날짜별 약물 환산 결과', 'comments': json.dumps(metadata, ensure_ascii=False)})
    methods_present = {r['method'] for r in results}
    methods = [m for m in PATIENT_METHOD_ORDER if m in methods_present]
    method_headers = [f'{m} ({TARGETS[m]} mg/day)' for m in methods]
    header_format = wb.add_format({'bold': True, 'font_color': '#222222', 'bg_color': '#EEEEEE', 'text_wrap': True, 'valign': 'vcenter'})
    number_format = wb.add_format({'num_format': '0.00'})
    plain_format = wb.add_format({'valign': 'top'})
    wrap_format = wb.add_format({'text_wrap': True, 'valign': 'top'})
    from services.excel_tables import text_height
    row_numbers = {}
    wrapped_columns = {}

    def append(ws, values):
        height = max((text_height(values[i], 48) for i in wrapped_columns[ws]), default=22)
        ws.set_row(row_numbers[ws], height)
        ws.write_row(row_numbers[ws], 0, values)
        row_numbers[ws] += 1

    def sheet(name, headers, explanation):
        ws = wb.add_worksheet(name)
        wrapped_columns[ws] = []
        for i, label in enumerate(headers):
            width = 23 if 'mg/day' in label else 48 if label in ('상태설명', '확인할 내용', '원문 약물', '원문 제품') else 20
            wrap = label in ('상태설명', '확인할 내용', '원문 약물', '원문 제품')
            ws.set_column(i, i, width, wrap_format if wrap else number_format if 'mg/day' in label else plain_format)
            if wrap:
                wrapped_columns[ws].append(i)
        ws.set_row(0, 36)
        ws.write_row(0, 0, headers, header_format)
        row_numbers[ws] = 1
        return ws

    detail_headers = ['patient_id', date_label, '원문 약물', '성분'] + [HEADERS[c] for c in COLUMNS] + ['일일용량 (mg/day)'] + method_headers + ['결과 상태', '확인할 내용', '원본 시트', '원본 행', '원본 처방일', '처방일수', '하루 정 수', '원문 제품', '기간 조정']
    detail_sheet = sheet('MedicationResults', detail_headers, '환자·기준일·원본 처방당 한 행입니다. 환산법은 가로 열로 표시합니다. 원본 시트와 행 번호로 입력 자료를 찾을 수 있습니다.')
    review_headers = ['patient_id', '처방일', '원문 약물', '확인할 내용', '원문 제품', '원본 시트', '원본 행', '처방일수', '하루 정 수', '중복 원본 행', '인식 성분', '약물 분류', '계산 처리', '항정신병약 환산 기여값'] + [HEADERS[c] for c in COLUMNS]
    review_sheet = sheet('Review', review_headers, '확인이 필요한 원본 처방만 모았습니다. 날짜별 오류나 방법별 누락은 MedicationResults에서 확인하세요. ID가 없는 처방은 임의로 합산하지 않습니다.')
    source = {(r['source_sheet'], r['source_row']): r for r in records}
    issues = {(r['source_sheet'], r['source_row']): set(r['issues']) for r in records if r['issues']}
    audit_issues = {key: set(flags) for key, flags in issues.items()}
    details.seek(0)
    text = io.TextIOWrapper(details, encoding='utf-8-sig', newline='')
    detail_count = 1
    try:
        for _, group in groupby(csv.DictReader(text), key=lambda r: (r['patient_id'], r['reference_date'], r['source_sheet'], r['source_row'])):
            batch = list(group)
            first = batch[0]
            key = (first['source_sheet'], int(first['source_row']))
            original = source[key]
            flags = {c for r in batch for c in r['reasons'].split(';') if c}
            codes = classify(original, flags)
            overview_key = (first['patient_id'], first['reference_date'])
            overview_codes[overview_key] = combine(overview_codes.get(overview_key, {}), codes)
            if flags:
                issues.setdefault(key, set()).update(flags)
            if flags:
                audit_issues.setdefault(key, set()).update(flags)
            missing = [r['method'] for r in batch if 'missing_factor' in r['reasons'].split(';')]
            note = (exclusion_basis(first['canonical']) + '. ' if first['status'] == 'non_target' else '') + reason_text(flags) + (': ' + ', '.join(missing) if missing else '')
            note = '; '.join(filter(None, [note, original.get('injection_error'), original.get('injection_frame', {}).get('calculation_note')]))
            values = {r['method']: float(r['equivalent_mg']) if r['equivalent_mg'] else None for r in batch}
            append(detail_sheet, [first['patient_id'], first['reference_date'], original['drug'], first['canonical']] + [display_value(codes[c], c) for c in COLUMNS] + [original['daily_mg']] +
                   [values.get(m) for m in methods] + [codes['status_label'] if codes['status_code'] else '계산 완료', note, *key, original['date'], original['days'], original['daily'], original['product'], '새 처방으로 대체 가정' if first['adjustments'] else ''])
            detail_count += 1
    finally:
        text.detach()
    review_count = 1
    for r in records:
        key = (r['source_sheet'], r['source_row'])
        excluded = r['kind'] == 'non_target' and r['canonical'] in EXCLUDED_INGREDIENTS
        codes = classify(r, issues.get(key, ()))
        if codes['review_required']:
            info = review_fields(r['canonical']) if excluded else {}
            note = '; '.join(filter(None, [exclusion_basis(r['canonical']) if excluded else '', reason_text(issues.get(key, set()))]))
            note = '; '.join(filter(None, [note, r.get('injection_error')]))
            append(review_sheet, [r['patient'], r['date'], r['drug'], note, r['product'], *key, r['days'], r['daily'], r['duplicate_of'],
                                  info.get('recognized_drug'), info.get('drug_group'), info.get('calculation'), info.get('equivalent_contribution')] + [display_value(codes[c], c) for c in COLUMNS])
            review_count += 1
    for ws, headers, count in [(detail_sheet, detail_headers, detail_count), (review_sheet, review_headers, review_count)]:
        ws.autofilter(0, 0, count - 1, len(headers) - 1)
    # Include every source prescription, including non-target and invalid rows
    # that do not produce a patient/date detail row.
    from services.excel_tables import write_table
    from datetime import timedelta
    audit_columns = ['patient_id', 'source_sheet', 'source_row', 'drug', 'product',
                     'prescription_date', 'days', 'daily_tablets', 'canonical',
                     'formulation', 'strength_mg', 'daily_mg', 'kind', 'drug_class', 'exclusion_basis', 'issues',
                     'adjustments', 'duplicate_of', 'original_end', 'effective_end', 'injection_evidence', 'injection_error', 'factor_evidence', 'unavailable_methods']
    def audit_rows():
        for r in records:
            from services.evidence import dated_evidence
            evidence = dated_evidence(r, methods)
            def last_day(end):
                return (end - timedelta(days=1)).isoformat() if end else None
            yield dict(patient_id=r['patient'], source_sheet=r['source_sheet'], source_row=r['source_row'],
                       drug=r['drug'], product=r['product'], prescription_date=r['date'], days=r['days'],
                       daily_tablets=r['daily'], canonical=r['canonical'], formulation=r['formulation'],
                       strength_mg=r['strength_mg'], daily_mg=r['daily_mg'], kind=r['kind'],
                       drug_class=CLASSES.get(r['canonical'], ''),
                       exclusion_basis=exclusion_basis(r['canonical']) if r['canonical'] in EXCLUDED_INGREDIENTS and r['kind'] == 'non_target' else '',
                       issues=';'.join(sorted(audit_issues.get((r['source_sheet'], r['source_row']), set()))),
                       adjustments=';'.join(r['adjustments']), duplicate_of=r['duplicate_of'],
                       original_end=last_day(r['end']), effective_end=last_day(r['effective_end']),
                       injection_evidence=json.dumps(r['injection_frame'], ensure_ascii=False) if r.get('injection_frame') else '',
                       injection_error=r.get('injection_error', ''), factor_evidence=evidence,
                       unavailable_methods=';'.join(e['method'] for e in json.loads(evidence) if not e['available']) if r['kind'] != 'non_target' else '',
                       **classify(r, audit_issues.get((r['source_sheet'], r['source_row']), ())))
    write_table(wb, 'AuditTrail', COLUMNS + audit_columns, audit_rows(), labels=HEADERS)
    add_xlsxwriter(wb, *dated_overview(results, overview_codes), date_label=date_label, worksheet=overview_sheet)
    add_legend(wb)
    wb.close()
    out.seek(0)
    return out
