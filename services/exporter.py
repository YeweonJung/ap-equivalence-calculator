"""Summary, medication detail, review items and a complete per-medication audit."""
from pathlib import Path
from xlsxwriter import Workbook
from services.result_summary import METHOD_ORDER, value_column
from services.result_notes import with_result_notes
from services.excel_tables import write_table
from services.output_overview import patient_overview, add_xlsxwriter
from services.exclusions import INGREDIENTS, item_exclusion_basis, review_fields
from services.result_status import decorate, COLUMNS, HEADERS, add_legend

AUDIT_COLUMNS = [
    'sheet', 'source_row', 'medication_column', 'patient', 'original', 'parsed',
    'dose_mg', 'daily_dose_mg', 'frequency', 'match_type', 'match_score', 'calculation_limited',
    'warning', 'calculation_note', 'unavailable_methods', 'name_candidates', 'input_dose_mg',
    'active_moiety_mg', 'dose_basis', 'mass_source', 'source_start', 'source_end',
    'drug_class', 'exclusion_basis', 'dose', 'unit', 'unit_candidates', 'unit_assumed', 'interval_days',
    'conversion_basis', 'conversion_source', 'lai_profile', 'oral_equivalent_mg',
    'oral_bridge_source', 'route', 'formulation', 'interval', 'status', 'status_message',
    'source_text',
    'recognized_product', 'product_name_source', 'product_name_checked_on',
    'factor_evidence', 'match_confidence_basis',
]


def export_results(audit_rows, error_rows, directory, summary_rows=None, patient_rows=None, patient_checks=None, base_method=None):
    output_file = Path(directory) / 'result.xlsx'
    audit_rows = [decorate({**r, 'calculation_limited': r.get('needs_review', False)}) for r in audit_rows]
    error_rows = [decorate(r) for r in error_rows]
    display_rows = with_result_notes(patient_rows or [], audit_rows, error_rows, patient_checks or [])
    columns = ['patient', 'original', '약물'] + COLUMNS + ['daily_dose_mg'] + [value_column(m) for m in METHOD_ORDER] + [
        '환산 근거', 'sheet', 'source_row', 'medication_column', 'source_start', 'source_end', 'status', 'dose_mg', 'frequency']
    if len(summary_rows or []) != len(audit_rows):
        raise ValueError('Medication rows and source evidence do not match.')
    medications = ({**audit, **summary} for summary, audit in zip(summary_rows or [], audit_rows))
    reviews = [r for r in error_rows if r['review_required']]
    existing = {(r.get('sheet'), r.get('source_row'), r.get('medication_column'), r.get('original')) for r in reviews}
    for row in audit_rows:
        # Review is an action queue. Normal exclusions and partial method
        # coverage remain visible in MedicationResults and AuditTrail.
        reason = (row.get('error') or row.get('warning') or row.get('status_message') or '입력 오류') if row['review_required'] else ''
        prn = bool(row.get('prn_excluded'))
        excluded = row.get('status') == 'non_target' and (row.get('parsed') in INGREDIENTS or prn)
        if excluded and reason:
            reason = '; '.join(filter(None, [item_exclusion_basis({'drug': row['parsed'], 'prn_excluded': prn}), reason]))
        key = (row.get('sheet'), row.get('source_row'), row.get('medication_column'), row.get('original'))
        if reason and key not in existing:
            reviews.append({**row, 'error': reason, **(review_fields(row['parsed'], prn) if excluded else {})})
            existing.add(key)
    review_columns = ['patient', 'original'] + COLUMNS + ['recognized_drug', 'drug_group', 'calculation', 'equivalent_contribution', 'error', 'sheet', 'source_row', 'medication_column']
    with Workbook(output_file, {'constant_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False}) as wb:
        from services.supplemented import append_frame_sheets
        append_frame_sheets(wb, audit_rows, patient_rows or [], patient_checks or [], base_method)
        add_xlsxwriter(wb, *patient_overview(display_rows, audit_rows, patient_checks or []), dated=False)
        write_table(wb, 'MedicationResults', columns, medications, labels=HEADERS)
        write_table(wb, 'Review', review_columns, reviews, labels={**HEADERS, 'patient': '환자 ID', 'original': '원문 약물', 'recognized_drug': '인식 성분', 'drug_group': '약물 분류', 'calculation': '계산 처리', 'equivalent_contribution': '항정신병약 환산 기여값', 'error': '확인할 내용', 'sheet': '원본 시트', 'source_row': '원본 행', 'medication_column': '원본 열'})
        # Preserve information-only records without a medication frame (e.g. a
        # missing ID or unrecognized sheet columns) outside the Review queue.
        audit_keys = {(r.get('sheet'), r.get('source_row'), r.get('medication_column'), r.get('original')) for r in audit_rows}
        extra = [r for r in error_rows if (r.get('sheet'), r.get('source_row'), r.get('medication_column'), r.get('original')) not in audit_keys]
        write_table(wb, 'AuditTrail', COLUMNS + AUDIT_COLUMNS + ['error'], audit_rows + extra,
                    labels={**HEADERS, 'calculation_limited': '입력 가정·제한'})
        add_legend(wb)
    return output_file
