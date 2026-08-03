import math
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


ALIAS_FILE = Path(__file__).resolve().parents[1] / "lookup" / "drug_alias.csv"
alias_df = pd.read_csv(ALIAS_FILE)
alias_map = {
    str(row["alias"]).casefold().strip(): str(row["standard_name"]).casefold().strip()
    for _, row in alias_df.iterrows()
    if str(row["alias"]).strip()
}

DOSE_RE = re.compile(
    r"(?<![\d.])(?P<dose>[+-]?\d+(?:\.\d+)?)\s*(?P<unit>mcg|ug|μg|mg|g)\b",
    re.IGNORECASE,
)
FREQUENCIES = (
    (re.compile(r"\b(qid|four\s+times?\s+(?:a\s+)?day|4\s*times?\s+(?:a\s+)?day)\b", re.I), "QID", 4.0),
    (re.compile(r"\b(tid|three\s+times?\s+(?:a\s+)?day|3\s*times?\s+(?:a\s+)?day)\b", re.I), "TID", 3.0),
    (re.compile(r"\b(bid|twice\s+(?:a\s+)?day|two\s+times?\s+(?:a\s+)?day|2\s*times?\s+(?:a\s+)?day)\b", re.I), "BID", 2.0),
    (re.compile(r"\b(qod|every\s+other\s+day)\b", re.I), "QOD", 0.5),
    (re.compile(r"\b(qhs|hs|qam|qd|od|daily|once\s+(?:a\s+)?day|every\s+day)\b", re.I), "QD", 1.0),
    (re.compile(r"\b(weekly|once\s+(?:a\s+)?week)\b", re.I), "WEEKLY", 1.0 / 7.0),
)


def _alias_pattern(alias):
    escaped = re.escape(alias)
    if re.search(r"[a-z0-9]", alias, re.I):
        return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.I)
    return re.compile(escaped, re.I)


ALIAS_PATTERNS = [(alias, _alias_pattern(alias)) for alias in sorted(alias_map, key=len, reverse=True)]


def dictionary_match(text):
    value = str(text).casefold().strip()
    for alias, pattern in ALIAS_PATTERNS:
        if pattern.search(value):
            return alias_map[alias]
    return None


def fuzzy_match(text, threshold=88):
    value = DOSE_RE.sub(" ", str(text).casefold())
    value = re.sub(r"[^\w가-힣]+", " ", value).strip()
    if not value:
        return None
    best_alias, best_score = None, 0.0
    for alias in alias_map:
        score = SequenceMatcher(None, value, alias).ratio() * 100
        if score > best_score:
            best_alias, best_score = alias, score
    return alias_map[best_alias] if best_alias and best_score >= threshold else None


def _dose_to_mg(value, unit):
    unit = unit.casefold()
    if unit in {"mcg", "ug", "μg"}:
        return value / 1000.0
    if unit == "g":
        return value * 1000.0
    return value


def parse_medication(text):
    original = "" if text is None else str(text).strip()
    if not original:
        raise ValueError("약물 값이 비어 있습니다.")
    drug = dictionary_match(original) or fuzzy_match(original)
    if not drug:
        raise ValueError("약물명을 확인할 수 없습니다.")
    match = DOSE_RE.search(original)
    if not match:
        raise ValueError("mg, mcg 또는 g 단위의 용량이 없습니다.")
    dose_mg = _dose_to_mg(float(match.group("dose")), match.group("unit"))
    if not math.isfinite(dose_mg) or dose_mg <= 0:
        raise ValueError("용량은 0보다 커야 합니다.")

    frequency, frequency_per_day = "ASSUMED_QD", 1.0
    warning = "복용 빈도 없음: 1일 1회로 계산"
    for pattern, label, per_day in FREQUENCIES:
        if pattern.search(original):
            frequency, frequency_per_day, warning = label, per_day, ""
            break
    return {
        "original": original,
        "drug": drug,
        "dose_mg": round(dose_mg, 6),
        "frequency": frequency,
        "frequency_per_day": frequency_per_day,
        "daily_dose_mg": round(dose_mg * frequency_per_day, 6),
        "warning": warning,
    }
