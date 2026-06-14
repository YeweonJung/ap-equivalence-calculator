import pandas as pd

from rapidfuzz import process

ALIAS_FILE = (
    "lookup/drug_alias.csv"
)

alias_df = pd.read_csv(
    ALIAS_FILE
)

alias_map = {
    str(row["alias"])
    .lower()
    .strip():

    row["standard_name"]

    for _, row
    in alias_df.iterrows()
}


def dictionary_match(text):

    text = (
        str(text)
        .lower()
        .strip()
    )

    matches = []

    for alias in alias_map:

        if alias in text:

            matches.append(
                alias
            )

    if not matches:
        return None

    best = max(
        matches,
        key=len
    )

    return alias_map[best]


def fuzzy_match(
    text,
    threshold=85
):

    result = (
        process.extractOne(
            str(text)
            .lower(),
            list(
                alias_map.keys()
            )
        )
    )

    if not result:
        return None

    candidate, score, _ = result

    if score < threshold:
        return None

    return alias_map[
        candidate
    ]
