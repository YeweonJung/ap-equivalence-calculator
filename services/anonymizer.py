PATIENT_COLUMNS = [
    "name",
    "patient",
    "patient_name",
    "mrn",
    "subject",
    "participant"
]


def anonymize_dataframe(df):

    df = df.copy()

    mapping = {}

    counter = 1

    for col in df.columns:

        col_lower = (
            str(col)
            .lower()
            .strip()
        )

        if any(
            k in col_lower
            for k in PATIENT_COLUMNS
        ):

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
