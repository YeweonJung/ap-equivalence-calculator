PATIENT_KEYWORDS = [
    "id",
    "patient",
    "patient_id",
    "subject",
    "participant",
    "mrn",
    "name"
]

MEDICATION_KEYWORDS = [
    "drug",
    "medication",
    "medications",
    "rx",
    "prescription",
    "medicine"
]


def detect_columns(df):

    patient_col = None
    medication_col = None

    for col in df.columns:

        c = (
            str(col)
            .lower()
            .strip()
        )

        if any(
            k in c
            for k in PATIENT_KEYWORDS
        ):
            patient_col = col

        if any(
            k in c
            for k in MEDICATION_KEYWORDS
        ):
            medication_col = col

    return {
        "patient_column":
        patient_col,

        "medication_column":
        medication_col
    }
