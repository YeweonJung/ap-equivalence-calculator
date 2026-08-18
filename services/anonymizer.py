PATIENT_COLUMNS = [
    "id",
    "patient_id",
    "name",
    "patient",
    "patient_name",
    "mrn",
    "subject",
    "participant",
    "환자번호",
    "환자명",
    "대상자번호",
    "등록번호",
    "차트번호",
]


def anonymize_dataframe(df, columns=None, mapping=None):

    import pandas as pd

    df = df.copy()

    mapping = mapping if mapping is not None else {}

    counter = len(mapping) + 1

    for col in df.columns:

        col_lower = (
            str(col)
            .lower()
            .strip()
        )

        selected = set(columns or [])
        if col in selected or (not selected and col_lower in PATIENT_COLUMNS):

            for value in (
                df[col]
                .dropna()
                .unique()
            ):

                key = str(value).strip()
                if not key:
                    continue
                if key not in mapping:

                    mapping[key] = (
                        f"PATIENT_{counter:05d}"
                    )

                    counter += 1

            df[col] = df[col].map(
                lambda value: mapping.get(str(value).strip(), "") if not pd.isna(value) else ""
            )

    return df, mapping
