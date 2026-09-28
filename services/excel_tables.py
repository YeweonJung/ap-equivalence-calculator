"""Fast row-wise workbook tables; values remain literal and formats are reused."""
import math

WRAPPED = {'original', 'source_text', 'warning', 'error', '환산 근거', 'conversion_basis',
           'conversion_source', 'oral_bridge_source', 'mass_source', 'unavailable_methods',
           'name_candidates', 'unit_candidates', 'issues', 'adjustments'}


def safe_value(value, column):
    # Keep the existing export convention for prescription text; IDs remain exact.
    if isinstance(value, str) and column not in ('patient', 'patient_id') and value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def write_table(workbook, name, columns, rows):
    sheet = workbook.add_worksheet(name)
    header = workbook.add_format({'bold': True, 'font_color': '#12233F', 'bg_color': '#DCEBFF',
                                  'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
    plain = workbook.add_format({'valign': 'top'})
    wrapped = workbook.add_format({'valign': 'top', 'text_wrap': True})
    number = workbook.add_format({'valign': 'top', 'num_format': 'General' if name == 'AuditTrail' else '0.00'})
    widths, formats = [], []
    for i, column in enumerate(columns):
        width = 55 if column in WRAPPED else 22 if column in ('parsed', '약물') else 20
        if column in ('patient', 'patient_id'): width = 18
        if column == 'original': width = 45
        numeric = '환산값' in column or column in ('daily_dose_mg', 'dose_mg', 'input_dose_mg', 'active_moiety_mg', 'oral_equivalent_mg')
        if numeric: width = 18
        widths.append(width)
        formats.append(wrapped if column in WRAPPED else number if numeric else plain)
        sheet.set_column(i, i, width, formats[-1])
    sheet.set_row(0, 42)
    sheet.write_row(0, 0, columns, header)
    wrapped_indices = [i for i, c in enumerate(columns) if c in WRAPPED]
    count = 0
    for count, row in enumerate(rows, 1):
        values = [safe_value(row.get(c), c) for c in columns]
        lines = max((sum(max(1, math.ceil(sum(2 if ord(c) > 127 else 1 for c in line) / widths[i]))
                         for line in str(values[i] or '').split('\n')) for i in wrapped_indices), default=1)
        sheet.set_row(count, min(max(18, lines * 16), 96))
        for i, value in enumerate(values):
            if value is None:
                continue
            if columns[i] in ('patient', 'patient_id'):
                sheet.write_string(count, i, str(value), formats[i])
            else:
                sheet.write(count, i, value, formats[i])
    sheet.freeze_panes(1, (4 if 'patient' in columns else 3) if name == 'AuditTrail' else 1)
    sheet.autofilter(0, 0, count, len(columns) - 1)
    sheet.hide_gridlines(2)
    sheet.set_zoom(85)
    return sheet
