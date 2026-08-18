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


def anonymize_dataframe(df, columns=None):

    df = df.copy()

    mapping = {}

    counter = 1

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

                if value not in mapping:

                    mapping[value] = (
                        f"PATIENT_{counter:05d}"
                    )

                    counter += 1

            df[col] = (
                df[col]
                .map(mapping)
            )

    return df, mapping
