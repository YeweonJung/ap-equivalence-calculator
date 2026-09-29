"""Fast row-wise workbook tables; values remain literal and formats are reused."""
import math

WRAPPED = {'recognized_product', 'product_name_source', 'original', 'source_text', 'warning', 'error', '환산 근거', 'conversion_basis',
           'conversion_source', 'oral_bridge_source', 'mass_source', 'unavailable_methods',
           'name_candidates', 'unit_candidates', 'issues', 'adjustments', '확인할 내용', '확인할 사항', '원문 약물', '원문 제품'}


def safe_value(value, column):
    # Keep the existing export convention for prescription text; IDs remain exact.
    if isinstance(value, str) and column not in ('patient', 'patient_id', '환자 ID') and value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def text_height(value, width):
    lines = sum(max(1, math.ceil(sum(2 if ord(c) > 127 else 1 for c in line) / max(1, width - 2)))
                for line in str(value or '').split('\n'))
    return min(409, max(22, lines * 17 + 4))


def write_table(workbook, name, columns, rows, widths=None, labels=None):
    sheet = workbook.add_worksheet(name)
    header = workbook.add_format({'bold': True, 'font_color': '#222222', 'bg_color': '#EEEEEE',
                                  'align': 'left', 'valign': 'vcenter', 'text_wrap': True})
    plain = workbook.add_format({'valign': 'top'})
    wrapped = workbook.add_format({'valign': 'top', 'text_wrap': True})
    number = workbook.add_format({'valign': 'top', 'num_format': 'General' if name == 'AuditTrail' else '0.00'})
    requested_widths = widths
    widths, formats = [], []
    for i, column in enumerate(columns):
        width = 55 if column in WRAPPED else 22 if column in ('parsed', '약물') else 20
        if column in ('patient', 'patient_id', '환자 ID'): width = 18
        if column == 'original': width = 45
        numeric = 'mg/day' in column or '환산값' in column or column in ('daily_dose_mg', 'dose_mg', 'input_dose_mg', 'active_moiety_mg', 'oral_equivalent_mg')
        if numeric: width = 18
        if requested_widths: width = requested_widths[i]
        widths.append(width)
        formats.append(wrapped if column in WRAPPED else number if numeric else plain)
        sheet.set_column(i, i, width, formats[-1])
    headings = [labels.get(c, c) for c in columns] if labels else columns
    sheet.set_row(0, max(text_height(h, widths[i]) for i, h in enumerate(headings)))
    sheet.write_row(0, 0, headings, header)
    wrapped_indices = [i for i, c in enumerate(columns) if c in WRAPPED]
    count = 0
    for count, row in enumerate(rows, 1):
        values = [safe_value(row.get(c), c) for c in columns]
        sheet.set_row(count, max((text_height(values[i], widths[i]) for i in wrapped_indices), default=22))
        for i, value in enumerate(values):
            if value is None:
                continue
            if columns[i] in ('patient', 'patient_id', '환자 ID'):
                sheet.write_string(count, i, str(value), formats[i])
            else:
                sheet.write(count, i, value, formats[i])
    sheet.autofilter(0, 0, count, len(columns) - 1)
    sheet.hide_gridlines(0)
    sheet.set_zoom(100)
    return sheet
