"""Fixed column names for uploads.

The upload reads only columns whose header is one of the names below (case, spaces,
underscores, hyphens, dots and brackets are ignored). Nothing is guessed from cell
contents: a wrong guess would put another column into the totals without any warning.
"""
import re
import unicodedata

# Users are told one rule: column 1 "id", column 2 "med". The other exact names are
# still read so that files made under the earlier instructions keep working.
ID_NAMES = ["id", "환자ID", "patient_id"]
DRUG_NAMES = ["med", "약물", "medication", "drug"]
DOSE_NAMES = ["용량", "dose", "1일용량", "daily_dose"]
UNIT_NAMES = ["단위", "unit"]
FREQUENCY_NAMES = ["횟수", "frequency"]

# Kept for the header-row search in file_reader.
MEDICATION_KEYWORDS = DRUG_NAMES

DOSE_VALUE_RE = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)\s*(?:mcg|ug|μg|㎍|mg|㎎|g)(?=$|[\s,;+/])", re.I)

MISSING_DRUG = "med 열을 찾지 못했습니다. 첫 번째 열 제목은 id, 두 번째 열 제목은 med로 해 주세요."
MISSING_ID = "id 열을 찾지 못했습니다. 첫 번째 열 제목은 id, 두 번째 열 제목은 med로 해 주세요."


def _key(column):
    # NFKC folds full-width letters and the decomposed Hangul that some Mac files contain.
    text = unicodedata.normalize("NFKC", str(column)).replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"[\s_\-().\[\]]", "", text.casefold())


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


LABEL = {"patient_column": "환자ID", "medication_column": "약물", "dose_column": "용량",
         "unit_column": "단위", "frequency_column": "횟수"}


def column_problem(df):
    """A message when the fixed-name columns cannot be read without guessing, else None."""
    plain, numbered = {}, {}
    for column in df.columns:
        kind = column_kind(column)
        if kind:
            plain.setdefault(kind, []).append(str(column))
            continue
        hit = _numbered(column)
        if hit:
            numbered.setdefault(hit, []).append(str(column))
    for kind, columns in plain.items():
        if len(columns) > 1:
            return f"같은 역할의 열이 여러 개입니다: {', '.join(columns)}. 하나만 남기거나 이름을 바꿔 주세요."
    for (kind, number), columns in numbered.items():
        if len(columns) > 1:
            return f"같은 번호의 열이 여러 개입니다: {', '.join(columns)}."
    if numbered:
        mixed = [plain[k][0] for k in ("medication_column", "dose_column", "unit_column", "frequency_column") if k in plain]
        if mixed:
            return f"번호 붙은 열(med1, med2 …)과 번호 없는 열({', '.join(mixed)})이 함께 있습니다. 한 가지 방식으로 맞춰 주세요."
        drugs = {number for (kind, number) in numbered if kind == "medication_column"}
        orphans = [columns[0] for (kind, number), columns in numbered.items() if kind != "medication_column" and number not in drugs]
        if orphans:
            return f"짝이 되는 약물 열이 없는 열이 있습니다: {', '.join(orphans)}. 예: dose2가 있으면 med2도 있어야 합니다."
    return None
