import math
from pathlib import Path

import pandas as pd


LOOKUP_FILE = Path(__file__).resolve().parents[1] / "lookup" / "master_lookup.csv"

lookup = pd.read_csv(LOOKUP_FILE)
for column in ("method_id", "source_drug", "target_drug"):
    lookup[column] = lookup[column].astype(str).str.strip().str.casefold()
lookup["method_id"] = lookup["method_id"].str.upper()

DEFAULT_TARGETS = {
    "CMD": "chlorpromazine",
    "CPZ_FGA": "chlorpromazine",
    "DDD": "chlorpromazine",
    "ED95": "olanzapine",
    "MED": "olanzapine",
}


def available_methods():
    return sorted(lookup["method_id"].unique().tolist())


def available_targets(method):
    method = str(method).strip().upper()
    return sorted(lookup.loc[lookup["method_id"] == method, "target_drug"].unique().tolist())


def normalize_target(method, target_drug=None):
    method = str(method).strip().upper()
    if method not in available_methods():
        raise ValueError(f"지원하지 않는 환산법입니다: {method}")
    target = str(target_drug or DEFAULT_TARGETS.get(method, "olanzapine")).strip().casefold()
    if target not in available_targets(method):
        raise ValueError(f"{method}에서 사용할 수 없는 기준 약물입니다: {target}")
    return target


def convert_drug(source_drug, daily_dose, method="CMD", target_drug=None):
    method = str(method).strip().upper()
    source = str(source_drug).strip().casefold()
    target = normalize_target(method, target_drug)
    try:
        dose = float(daily_dose)
    except (TypeError, ValueError) as exc:
        raise ValueError("일일 용량은 숫자여야 합니다.") from exc
    if not math.isfinite(dose) or dose <= 0:
        raise ValueError("일일 용량은 0보다 큰 유한한 숫자여야 합니다.")

    result = lookup[
        (lookup["method_id"] == method)
        & (lookup["source_drug"] == source)
        & (lookup["target_drug"] == target)
    ]
    if result.empty:
        raise LookupError(f"{method}: {source} → {target} 환산값이 없습니다.")
    if len(result) != 1:
        raise ValueError(f"환산표에 중복 행이 있습니다: {method}, {source}, {target}")

    factor = float(result.iloc[0]["factor"])
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("환산표의 계수가 올바르지 않습니다.")
    return dose * factor
