import pandas as pd

MAX_SHEETS = 5


def read_file(filepath):

    if filepath.lower().endswith(
        ".csv"
    ):

        return {
            "Sheet1":
            pd.read_csv(filepath)
        }

    excel = pd.ExcelFile(
        filepath
    )

    if (
        len(excel.sheet_names)
        > MAX_SHEETS
    ):
        raise ValueError(
            f"Maximum {MAX_SHEETS} sheets allowed."
        )

    sheets = {}

    for sheet in (
        excel.sheet_names
    ):

        sheets[sheet] = (
            pd.read_excel(
                filepath,
                sheet_name=sheet
            )
        )

    return sheets
