import json

from services.llm_client import (
    ask_llm_json
)


def batch_parse_medications(
    medication_list
):

    prompt = f"""
You are a clinical medication normalization engine.

Return JSON only.

Input:

{json.dumps(medication_list)}

Output:

[
 {{
  "original":"",
  "drug":"",
  "dose":null,
  "frequency":"",
  "confidence":0.0
 }}
]
"""

    result = ask_llm_json(
        prompt
    )

    for item in result:

        item["drug"] = (
            item["drug"]
            .lower()
            .strip()
        )

        freq = (
            item.get(
                "frequency",
                ""
            )
            .upper()
            .strip()
        )

        if freq == "HS":
            freq = "QHS"

        item["frequency"] = freq

    return result
