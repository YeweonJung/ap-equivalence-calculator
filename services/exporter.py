from pathlib import Path

import pandas as pd


def export_results(detailed_rows, audit_rows, error_rows, directory):
    output_file = Path(directory) / "result.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        pd.DataFrame(detailed_rows).to_excel(writer, sheet_name="Detailed", index=False)
        pd.DataFrame(audit_rows).to_excel(writer, sheet_name="AuditTrail", index=False)
        pd.DataFrame(error_rows).to_excel(writer, sheet_name="Errors", index=False)
    return output_file
