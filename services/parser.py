import math
import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process


ALIAS_FILE = Path(__file__).resolve().parents[1] / "lookup" / "drug_alias.csv"
alias_df = pd.read_csv(ALIAS_FILE)
alias_map = {
    str(row["alias"]).casefold().strip(): str(row["standard_name"]).casefold().strip()
    for _, row in alias_df.iterrows()
    if str(row["alias"]).strip()
}

DOSE_RE = re.compile(
    r"(?<![\d.])(?P<dose>[+-]?\d+(?:\.\d+)?)\s*(?P<unit>mcg|ug|μg|㎍|mg|㎎|g)(?![a-z])",
    re.IGNORECASE,
)
FREQUENCIES = (
    (re.compile(r"\b(qid|four\s+times?\s+(?:a\s+)?day|4\s*times?\s+(?:a\s+)?day)\b", re.I), "QID", 4.0),
    (re.compile(r"\b(tid|three\s+times?\s+(?:a\s+)?day|3\s*times?\s+(?:a\s+)?day)\b", re.I), "TID", 3.0),
    (re.compile(r"\b(bid|twice\s+(?:a\s+)?day|two\s+times?\s+(?:a\s+)?day|2\s*times?\s+(?:a\s+)?day)\b", re.I), "BID", 2.0),
    (re.compile(r"\b(qod|every\s+other\s+day)\b", re.I), "QOD", 0.5),
    (re.compile(r"\b(qhs|hs)\b", re.I), "QHS", 1.0),
    (re.compile(r"\bqam\b", re.I), "QAM", 1.0),
    (re.compile(r"\b(qd|od|daily|once\s+(?:a\s+)?day|every\s+day)\b", re.I), "QD", 1.0),
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


def fuzzy_match(text, threshold=85):
    value = DOSE_RE.sub(" ", str(text).casefold())
    value = re.sub(r"\b(?:qid|tid|bid|qod|qhs|hs|qam|qd|od|daily|weekly|tab(?:let)?s?|caps?(?:ules?)?)\b", " ", value, flags=re.I)
    value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:t|tabs?|tablets?|caps?)\b", " ", value, flags=re.I)
    value = re.sub(r"[^\w가-힣]+", " ", value).strip()
    if not value:
        return None
    candidates = [alias for alias in alias_map if len(alias) >= 4]
    result = process.extractOne(value, candidates, scorer=fuzz.ratio)
    if result and result[1] >= threshold:
        return alias_map[result[0]], float(result[1])
    return None, None


def _dose_to_mg(value, unit):
    unit = unit.casefold()
    if unit in {"mcg", "ug", "μg", "㎍"}:
        return value / 1000.0
    if unit == "g":
        return value * 1000.0
    return value


def parse_medication(text):
    original = "" if text is None else str(text).strip()
    if not original:
        raise ValueError("약물 값이 비어 있습니다.")
    drug = dictionary_match(original)
    match_type, match_score = "exact", 100.0
    if not drug:
        drug, match_score = fuzzy_match(original)
        match_type = "fuzzy" if drug else "unresolved"
    if not drug:
        raise ValueError("약물명을 확인할 수 없습니다.")
    match = DOSE_RE.search(original)
    if not match:
        raise ValueError("mg, mcg 또는 g 단위의 용량이 없습니다.")
    dose_mg = _dose_to_mg(float(match.group("dose")), match.group("unit"))
    if not math.isfinite(dose_mg) or dose_mg <= 0:
        raise ValueError("용량은 0보다 커야 합니다.")

    if re.search(r"\b(prn|as\s+needed|필요시)\b", original, re.I):
        raise ValueError("PRN(필요시) 처방은 일일 용량을 확정할 수 없어 자동 환산하지 않습니다.")
    if re.search(r"\b(lai|depot|injection|injectable|q\d+w|every\s+\d+\s*weeks?)\b|주사|데포", original, re.I):
        raise ValueError("장기지속형 주사제/주 단위 처방은 경구 일일 용량으로 자동 환산하지 않습니다.")

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
        "match_type": match_type,
        "match_score": match_score,
        "needs_review": match_type != "exact" or bool(warning),
    }
