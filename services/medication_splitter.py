import re

SEPARATORS = [
    ";",
    ",",
    "/",
    "\n",
    "+"
]


def split_medications(text):

    if text is None:
        return []

    pattern = "|".join(
        map(
            re.escape,
            SEPARATORS
        )
    )

    meds = re.split(
        pattern,
        str(text)
    )

    return [
        m.strip()
        for m in meds
        if m.strip()
    ]
