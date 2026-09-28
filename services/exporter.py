import math
from pathlib import Path

import pandas as pd
from services.result_summary import METHOD_ORDER
from services.result_notes import with_result_notes
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _safe_excel_value(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _safe_frame(rows, columns):
    frame = pd.DataFrame(rows, columns=columns)
    for column in frame.columns:
        if column not in ('patient', 'patient_id'):
            frame[column] = frame[column].map(_safe_excel_value)
    return frame


def _format_worksheet(worksheet):
    header_fill = PatternFill("solid", fgColor="DCEBFF")
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="12233F")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    worksheet.row_dimensions[1].height = 30
    worksheet.freeze_panes = "D2" if worksheet.title == "Results" else "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    wrap_headers = {"original", "warning", "error", "reference", "환산 근거", "basis", "source", "conversion_basis", "conversion_source", "oral_bridge_source", "확인할 내용", "환산 완료 방법", "환산 불가 방법"}
    for column_index, cells in enumerate(worksheet.iter_cols(), start=1):
        header = str(cells[0].value or "")
        max_length = max((len(str(cell.value)) for cell in cells if cell.value is not None), default=0)
        worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 11), 55)
        if header == '결과 상태':
            worksheet.column_dimensions[get_column_letter(column_index)].width = 24
        for cell in cells[1:]:
            if header in ('patient', 'patient_id') and cell.value is not None:
                cell.value = str(cell.value)
                cell.data_type = 's'
            cell.alignment = Alignment(vertical="top", wrap_text=header in wrap_headers)

    headers = {cell.column: str(cell.value or "") for cell in worksheet[1]}
    for row_index in range(2, worksheet.max_row + 1):
        required_lines = 1
        for cell in worksheet[row_index]:
            if headers.get(cell.column) not in wrap_headers or cell.value is None:
                continue
            width = worksheet.column_dimensions[get_column_letter(cell.column)].width or 11
            line_count = sum(max(1, math.ceil(
                sum(2 if ord(c) > 127 else 1 for c in line) / max(int(width), 1)))
                for line in str(cell.value).split('\n'))
            required_lines = max(required_lines, line_count)
        height_limit = 409 if worksheet.title == 'Results' else 96
        worksheet.row_dimensions[row_index].height = min(max(18, required_lines * 16), height_limit)


def export_results(audit_rows, error_rows, directory, summary_rows=None, patient_rows=None, patient_checks=None):
    """Only the summary, medication evidence and actionable review rows are exported."""
    from services.output_overview import patient_overview, add_openpyxl
    from services.result_summary import value_column
    output_file = Path(directory) / "result.xlsx"
    display_rows = with_result_notes(patient_rows or [], audit_rows, error_rows, patient_checks or [])
    # Preserve one source location per medication, even when original text repeats.
    columns = ['patient', 'original', '약물', 'daily_dose_mg'] + [value_column(m) for m in METHOD_ORDER] + [
        '환산 근거', 'sheet', 'source_row', 'medication_column', 'source_start', 'source_end', 'status', 'dose_mg', 'frequency']
    medications = []
    if len(summary_rows or []) != len(audit_rows):
        raise ValueError('Medication rows and source evidence do not match.')
    for summary, audit in zip(summary_rows or [], audit_rows):
        medications.append({**audit, **summary})
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
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        _safe_frame(medications, columns).to_excel(writer, sheet_name='MedicationResults', index=False)
        _safe_frame(reviews, review_columns).to_excel(writer, sheet_name='Review', index=False)
        for worksheet in writer.book.worksheets:
            _format_worksheet(worksheet)
            worksheet.freeze_panes = 'B2'
            worksheet.sheet_view.showGridLines = False
            worksheet.sheet_view.zoomScale = 85
        sheet = writer.book['MedicationResults']
        sheet.column_dimensions['A'].width = 18
        sheet.column_dimensions['B'].width = 45
        sheet.column_dimensions['C'].width = 22
        for col in range(4, 5 + len(METHOD_ORDER)):
            sheet.column_dimensions[get_column_letter(col)].width = 18
            for cells in sheet.iter_rows(min_row=2, min_col=col, max_col=col):
                cells[0].number_format = '0.00'
        add_openpyxl(writer.book, *patient_overview(display_rows, audit_rows, patient_checks or []))
    return output_file
