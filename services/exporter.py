import math
from pathlib import Path

import pandas as pd
from services.result_summary import RESULT_COLUMNS, METHOD_ORDER, PATIENT_COLUMNS
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


DETAILED_COLUMNS = [
    "sheet", "source_row", "medication_column", "patient", "original", "drug", "dose_mg", "frequency",
    "daily_dose_mg", "method", "target_drug", "equivalent_dose_mg", "warning",
    "match_type", "match_score", "needs_review",
]
FRAME_COLUMNS = ["name_candidates", "input_dose_mg", "active_moiety_mg", "dose_basis", "mass_source", "source_start", "source_end", "drug_class", "dose", "unit", "unit_candidates", "unit_assumed", "interval_days", "conversion_basis", "conversion_source", "lai_profile", "oral_equivalent_mg", "oral_bridge_source", "route", "formulation", "interval", "status", "status_message"]
DETAILED_COLUMNS += FRAME_COLUMNS
AUDIT_COLUMNS = ["sheet", "source_row", "medication_column", "patient", "original", "parsed", "dose_mg", "daily_dose_mg", "frequency", "match_type", "match_score", "needs_review", "warning", "unavailable_methods"] + FRAME_COLUMNS
ERROR_COLUMNS = ["sheet", "source_row", "medication_column", "patient", "original", "error"] + FRAME_COLUMNS
METHOD_INFO = [
    {"method": "CMD_DIRECT", "basis": "Leucht 2015 Table 1 primary analysis: direct ratios (CMD sensitivity analysis); OLZ1", "reference": "https://doi.org/10.1093/schbul/sbv037"},
    {"method": "CMD_INDIRECT", "basis": "Leucht 2015 Table 1 primary analysis: direct and indirect ratios (CMD sensitivity analysis); OLZ1", "reference": "https://doi.org/10.1093/schbul/sbv037"},
    {"method": "WOODS", "basis": "Woods 2003 minimum effective doses; CPZ100 convention", "reference": "https://pubmed.ncbi.nlm.nih.gov/12823080/"},
    {"method": "GARDNER", "basis": "Gardner 2010 Table 1 oral median-dose ratios; CPZ600 = OLZ20", "reference": "https://doi.org/10.1176/appi.ajp.2009.09060802"},
    {"method": "CMD", "basis": "Classical mean dose method", "reference": "Leucht et al. 2015; PMID 25841041"},
    {"method": "MED", "basis": "Minimum effective dose method", "reference": "Leucht et al. 2014; PMID 24493852"},
    {"method": "ED95", "basis": "95% effective dose method", "reference": "Leucht et al. 2020; PMID 31838873"},
    {"method": "DDD", "basis": "WHO Defined Daily Dose", "reference": "WHO ATC/DDD methodology"},
    {"method": "CPZ_FGA", "basis": "Historical chlorpromazine equivalents", "reference": "Davis 1974; PMID 4156792"},
]


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

    wrap_headers = {"original", "warning", "error", "reference", "환산 근거", "basis", "source", "conversion_basis", "conversion_source", "oral_bridge_source"}
    for column_index, cells in enumerate(worksheet.iter_cols(), start=1):
        header = str(cells[0].value or "")
        max_length = max((len(str(cell.value)) for cell in cells if cell.value is not None), default=0)
        worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 11), 55)
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
            visual_length = sum(2 if ord(character) > 127 else 1 for character in str(cell.value))
            required_lines = max(required_lines, math.ceil(visual_length / max(int(width), 1)))
        worksheet.row_dimensions[row_index].height = min(max(18, required_lines * 16), 96)


def export_results(detailed_rows, audit_rows, error_rows, directory, total_rows=None, summary_rows=None, patient_rows=None, patient_checks=None):
    output_file = Path(directory) / "result.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        _safe_frame(patient_rows or [], PATIENT_COLUMNS).to_excel(writer, sheet_name="Results", index=False)
        _safe_frame(summary_rows or [], RESULT_COLUMNS).to_excel(writer, sheet_name="MedicationResults", index=False)
        check_columns = ['patient_id', 'method', 'target_drug', 'total_equivalent_dose_mg', 'partial_equivalent_dose_mg', 'converted_count', 'unresolved_count', 'excluded_count', 'status', 'needs_review']
        _safe_frame(patient_checks or [], check_columns).to_excel(writer, sheet_name="PatientChecks", index=False)
        _safe_frame(detailed_rows, DETAILED_COLUMNS).to_excel(
            writer, sheet_name="Detailed", index=False
        )
        _safe_frame(audit_rows, AUDIT_COLUMNS).to_excel(
            writer, sheet_name="AuditTrail", index=False
        )
        _safe_frame(error_rows, ERROR_COLUMNS).to_excel(
            writer, sheet_name="Errors", index=False
        )
        columns = ["sheet", "source_row", "medication_column", "patient", "original", "method", "target_drug", "total_equivalent_dose_mg", "partial_equivalent_dose_mg", "converted_count", "unresolved_count", "excluded_count", "status", "needs_review"]
        _safe_frame(total_rows or [], columns).to_excel(writer, sheet_name="CellTotals", index=False)
        pd.read_csv(Path(__file__).resolve().parents[1] / 'lookup/equivalence_anchors.csv').to_excel(writer, sheet_name='FactorSources', index=False)
        from services.release import metadata
        pd.DataFrame([metadata()]).to_excel(writer, sheet_name='VersionInfo', index=False)
        review_columns = ['sheet', 'source_row', 'medication_column', 'original', 'parsed',
                          'dose_mg', 'active_moiety_mg', 'oral_equivalent_mg', 'interval_days',
                          'dose_basis', 'warning', 'name_candidates', 'needs_review', 'status',
                          'reviewer_1', 'reviewer_1_decision', 'reviewer_2', 'reviewer_2_decision',
                          'adjudication', 'correction', 'review_date']
        _safe_frame(audit_rows, review_columns).to_excel(writer, sheet_name='ReviewQueue', index=False)
        pd.DataFrame(METHOD_INFO).to_excel(writer, sheet_name="MethodInfo", index=False)
        from services.injections import DEPOT_DDD, SOURCE, CPZ_SOURCE, OLZ_SOURCE
        from services.lai_support import bridge_info_rows
        pd.DataFrame([{"method": "DDD", "drug": drug, "route": "depot", "DDD_mg_per_day": value, "target": "chlorpromazine oral", "target_DDD_mg": 300, "source": OLZ_SOURCE if drug == "olanzapine" else SOURCE, "target_source": CPZ_SOURCE, "month_days": 30} for drug, value in DEPOT_DDD.items()] + bridge_info_rows()).to_excel(writer, sheet_name="InjectionInfo", index=False)
        for worksheet in writer.book.worksheets:
            _format_worksheet(worksheet)
        sheet = writer.book['MedicationResults']
        sheet.column_dimensions['A'].width = 20
        sheet.column_dimensions['B'].width = 55
        sheet.column_dimensions['C'].width = 22
        sheet.sheet_view.zoomScale = 75
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = 'landscape'
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.print_title_rows = '1:1'
        sheet.row_dimensions[1].height = 48
        for row in sheet.iter_rows(min_row=2):
            for cell in row[3:]:
                cell.number_format = '0.0000'
        for col in range(4, 4 + 2 * len(METHOD_ORDER)):
            sheet.column_dimensions[get_column_letter(col)].width = 22
            sheet.cell(1,col).fill = PatternFill('solid', fgColor='DCEBFF' if col < 4 + len(METHOD_ORDER) else 'DDEEDC')
        patient_sheet = writer.book['Results']
        patient_sheet.freeze_panes = 'B2'
        for column in range(2, len(PATIENT_COLUMNS) + 1):
            patient_sheet.column_dimensions[get_column_letter(column)].width = 25
            for cells in patient_sheet.iter_rows(min_row=2, min_col=column, max_col=column):
                cells[0].number_format = '0.0000'
        patient_sheet.row_dimensions[1].height = 45
    return output_file
