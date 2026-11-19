"""Fixed column names for uploads.

The upload reads only columns whose header is one of the names below (case, spaces,
underscores, hyphens, dots and brackets are ignored). Nothing is guessed from cell
contents: a wrong guess would put another column into the totals without any warning.
"""
import re

ID_NAMES = ["환자ID", "ID", "patient_id"]
DRUG_NAMES = ["약물", "medication", "drug"]
DOSE_NAMES = ["용량", "dose", "1일용량", "daily_dose"]
UNIT_NAMES = ["단위", "unit"]
FREQUENCY_NAMES = ["횟수", "frequency"]

# Kept for the header-row search in file_reader.
MEDICATION_KEYWORDS = DRUG_NAMES

DOSE_VALUE_RE = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)\s*(?:mcg|ug|μg|㎍|mg|㎎|g)(?=$|[\s,;+/])", re.I)

MISSING_DRUG = "약물 열을 찾지 못했습니다. 약물이 적힌 열의 제목을 '약물'(또는 medication, drug)로 바꿔 주세요."
MISSING_ID = "환자ID 열을 찾지 못했습니다. 환자 번호가 적힌 열의 제목을 '환자ID'(또는 ID)로 바꿔 주세요."


def _key(column):
    return re.sub(r"[\s_\-().\[\]]", "", str(column).casefold())


_KINDS = {
    "patient_column": {_key(n) for n in ID_NAMES},
    "medication_column": {_key(n) for n in DRUG_NAMES},
    "dose_column": {_key(n) for n in DOSE_NAMES},
    "unit_column": {_key(n) for n in UNIT_NAMES},
    "frequency_column": {_key(n) for n in FREQUENCY_NAMES},
}


def column_kind(column):
    """The role of a column with an exact fixed name, or None."""
    key = _key(column)
    return next((kind for kind, names in _KINDS.items() if key in names), None)


def is_known_header(column):
    return column_kind(column) is not None or bool(_numbered(column))


def _numbered(column):
    match = re.fullmatch(r"(.+?)(\d+)", _key(column))
    if not match:
        return None
    kind = column_kind(match.group(1))
    return (kind, match.group(2)) if kind and kind != "patient_column" else None


def detect_columns(df):
    found = {kind: None for kind in _KINDS}
    for column in df.columns:
        kind = column_kind(column)
        if kind and found[kind] is None:
            found[kind] = column
    return found


def detect_medication_groups(df):
    """Pair numbered columns (약물1·용량1, 약물2·용량2, ...) by their number."""
    groups = {}
    for column in df.columns:
        numbered = _numbered(column)
        if numbered:
            kind, number = numbered
            groups.setdefault(number, {}).setdefault(kind, column)
    return [{key: group.get(key) for key in ("medication_column", "dose_column", "unit_column", "frequency_column")}
            for number, group in sorted(groups.items(), key=lambda item: int(item[0])) if "medication_column" in group]
