"""Summary, medication detail, review items and a complete per-medication audit."""
from pathlib import Path
from xlsxwriter import Workbook
from services.result_summary import METHOD_ORDER, value_column
from services.result_notes import with_result_notes
from services.excel_tables import write_table
from services.output_overview import patient_overview, add_xlsxwriter

AUDIT_COLUMNS = [
    'sheet', 'source_row', 'medication_column', 'patient', 'original', 'parsed',
    'dose_mg', 'daily_dose_mg', 'frequency', 'match_type', 'match_score', 'needs_review',
    'warning', 'unavailable_methods', 'name_candidates', 'input_dose_mg',
    'active_moiety_mg', 'dose_basis', 'mass_source', 'source_start', 'source_end',
    'drug_class', 'dose', 'unit', 'unit_candidates', 'unit_assumed', 'interval_days',
    'conversion_basis', 'conversion_source', 'lai_profile', 'oral_equivalent_mg',
    'oral_bridge_source', 'route', 'formulation', 'interval', 'status', 'status_message',
    'source_text',
    'recognized_product', 'product_name_source', 'product_name_checked_on',
]


def export_results(audit_rows, error_rows, directory, summary_rows=None, patient_rows=None, patient_checks=None):
    output_file = Path(directory) / 'result.xlsx'
    display_rows = with_result_notes(patient_rows or [], audit_rows, error_rows, patient_checks or [])
    columns = ['patient', 'original', '약물', 'daily_dose_mg'] + [value_column(m) for m in METHOD_ORDER] + [
        '환산 근거', 'sheet', 'source_row', 'medication_column', 'source_start', 'source_end', 'status', 'dose_mg', 'frequency']
    if len(summary_rows or []) != len(audit_rows):
        raise ValueError('Medication rows and source evidence do not match.')
    medications = ({**audit, **summary} for summary, audit in zip(summary_rows or [], audit_rows))
    reviews = list(error_rows)
    existing = {(r.get('sheet'), r.get('source_row'), r.get('medication_column'), r.get('original')) for r in reviews}
    for row in audit_rows:
        reason = row.get('warning') or ''
        if row.get('unavailable_methods'):
            reason = '; '.join(filter(None, [reason, '환산 계수 또는 제형별 근거 없음: ' + row['unavailable_methods']]))
        key = (row.get('sheet'), row.get('source_row'), row.get('medication_column'), row.get('original'))
        if reason and key not in existing:
            reviews.append({**row, 'error': reason})
            existing.add(key)
    review_columns = ['patient', 'original', 'error', 'sheet', 'source_row', 'medication_column']
    with Workbook(output_file, {'constant_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False}) as wb:
        add_xlsxwriter(wb, *patient_overview(display_rows, audit_rows, patient_checks or []), dated=False)
        write_table(wb, 'MedicationResults', columns, medications)
        write_table(wb, 'Review', review_columns, reviews)
        write_table(wb, 'AuditTrail', AUDIT_COLUMNS, audit_rows)
    return output_file
