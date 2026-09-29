import math
from pathlib import Path

import pandas as pd


LOOKUP_FILE = Path(__file__).resolve().parents[1] / "lookup" / "master_lookup.csv"

lookup = pd.read_csv(LOOKUP_FILE)
for column in ("method_id", "source_drug", "target_drug"):
    lookup[column] = lookup[column].astype(str).str.strip().str.casefold()
lookup["method_id"] = lookup["method_id"].str.upper()

# The shipped table is immutable during a worker's lifetime. Index once instead
# of filtering pandas for every medication, method and patient total.
_FACTORS = {}
_TARGETS = {}
for _row in lookup.itertuples(index=False):
    _key = (_row.method_id, _row.source_drug, _row.target_drug)
    if _key in _FACTORS:
        raise ValueError(f"Duplicate conversion factor: {_key}")
    _factor = float(_row.factor)
    if not math.isfinite(_factor) or _factor <= 0:
        raise ValueError(f"Invalid conversion factor: {_key}")
    _FACTORS[_key] = _factor
    _TARGETS.setdefault(_row.method_id, set()).add(_row.target_drug)

DEFAULT_TARGETS = {
    "CMD_DIRECT": "olanzapine",
    "CMD_INDIRECT": "olanzapine",
    "WOODS": "chlorpromazine",
    "GARDNER": "olanzapine",
    "CMD": "olanzapine",
    "CPZ_FGA": "chlorpromazine",
    "DDD": "olanzapine",
    "ED95": "risperidone",
    "MED": "olanzapine",
}

def available_methods():
    return sorted(_TARGETS)


def available_targets(method):
    method = str(method).strip().upper()
    return sorted(_TARGETS.get(method, ()))


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

    factor = _FACTORS.get((method, source, target))
    if factor is None:
        raise LookupError(f"{method}: {source} → {target} 환산값이 없습니다.")
    return dose * factor
