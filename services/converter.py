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

METHOD_WARNINGS = {
    "CMD": "급성 조현병 경구약 임상시험의 평균용량 기반이며 개인별 처방 권고가 아닙니다.",
    "MED": "초발성 또는 치료저항성 환자에게 일반화할 수 없는 연구용 환산값입니다.",
    "ED95": "만성 조현병 급성 악화 집단의 평균 효과 기반이며 개인별 권장용량이 아닙니다.",
    "DDD": "WHO DDD는 약물사용 연구용 기술 단위이며 권장용량 또는 처방용량이 아닙니다.",
    "CPZ_FGA": "1세대 항정신병약물의 역사적 CPZ 비교값입니다.",
}


def available_methods():
    return sorted(lookup["method_id"].unique().tolist())


def method_warning(method, source_drug=None, target_drug=None):
    method = str(method).strip().upper()
    warning = METHOD_WARNINGS.get(method, "")
    drugs = {str(source_drug or "").casefold(), str(target_drug or "").casefold()}
    if method == "ED95" and "haloperidol" in drugs:
        warning += " Haloperidol ED95 값은 단일 연구 기반의 제한적 추정치입니다."
    return warning.strip()


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
