import pandas as pd

LOOKUP_FILE = (
    "lookup/master_lookup.csv"
)

lookup = pd.read_csv(
    LOOKUP_FILE
)


def convert_drug(
    source_drug,
    daily_dose,
    method="CMD",
    target_drug="chlorpromazine"
):

    result = lookup[
        (
            lookup["method_id"]
            == method
        )
        &
        (
            lookup["source_drug"]
            == source_drug
        )
        &
        (
            lookup["target_drug"]
            == target_drug
        )
    ]

    if result.empty:

        return None

    factor = float(
        result.iloc[0]["factor"]
    )

    return round(
        daily_dose *
        factor,
        2
    )
