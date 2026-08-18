from pathlib import Path

import pandas as pd


DETAILED_COLUMNS = [
    "sheet", "patient", "original", "drug", "dose_mg", "frequency",
    "daily_dose_mg", "method", "target_drug", "equivalent_dose_mg", "warning",
    "match_type", "match_score", "needs_review",
]
AUDIT_COLUMNS = ["sheet", "patient", "original", "parsed", "match_type", "match_score", "status"]
ERROR_COLUMNS = ["sheet", "patient", "original", "error"]


def export_results(detailed_rows, audit_rows, error_rows, directory):
    output_file = Path(directory) / "result.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        pd.DataFrame(detailed_rows, columns=DETAILED_COLUMNS).to_excel(
            writer, sheet_name="Detailed", index=False
        )
        pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS).to_excel(
            writer, sheet_name="AuditTrail", index=False
        )
        pd.DataFrame(error_rows, columns=ERROR_COLUMNS).to_excel(
            writer, sheet_name="Errors", index=False
        )
    return output_file
