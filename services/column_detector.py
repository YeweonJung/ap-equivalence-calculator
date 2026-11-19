import re


PATIENT_KEYWORDS = ["patient_id", "patient", "subject", "participant", "mrn", "id", "name", "환자번호", "환자", "대상자", "등록번호", "차트번호",
                    "pt", "pt_id", "pid", "hid", "sid", "study_id", "subject_id", "case", "case_id", "case_no",
                    "환자id", "연구번호", "피험자", "피험자번호", "병록번호", "患者id", "患者番号", "患者", "病人", "病历号", "identifiant", "رقم_المريض"]
# Substrings that mark a patient column even inside a longer header ("환자 ID (원내)").
PATIENT_PARTS = ["patient", "subject", "participant", "mrn", "환자", "대상자", "등록번호", "차트번호", "피험자", "연구번호", "병록번호",
                 "患者", "病人", "study_id", "case_id"]

# Matched anywhere in the header.
MEDICATION_KEYWORDS = ["medications", "medication", "prescription", "medicine", "drug", "rx", "처방내역", "처방약", "처방", "투약내역", "투약", "약물정보", "약물명", "약품명", "제품명", "성분명", "의약품명", "약제",
                       "antipsychotic", "regimen", "항정신병", "약물", "약품", "복용약", "医薬品", "薬剤", "药物", "药品", "médicament", "traitement", "دواء", "أدوية"]
# Short headers matched only as the whole header, so "med" does not catch "median" and "약" does not catch "투약횟수".
MEDICATION_EXACT = ["aps", "ap", "meds", "med", "drugs", "tx", "treatment", "약", "약명", "薬", "药"]
DOSE_KEYWORDS = ["daily_dose", "dose_mg", "dosage", "dose", "strength", "일일용량", "1일용량", "1회용량", "투약량", "투여량", "함량", "용량",
                 "mg_per_day", "mg/day", "mg_day", "mgday", "daily_mg", "복용량", "1일량", "하루용량", "用量", "剂量", "posologie", "الجرعة"]
DOSE_EXACT = ["mg", "mg/d", "mgd", "량"]
UNIT_KEYWORDS = ["dose_unit", "unit", "용량단위", "단위", "単位", "单位", "unité", "الوحدة"]
UNIT_EXACT = ["uom"]
FREQUENCY_KEYWORDS = ["frequency", "freq", "일일횟수", "복용횟수", "투약횟수", "투여횟수", "횟수", "복용빈도", "투여빈도", "용법",
                      "times_per_day", "times/day", "per_day", "daily_frequency", "dosing", "schedule", "복용법", "투여법", "하루횟수", "1일횟수",
                      "회/일", "회수", "빈도", "回数", "用法", "频次", "次数", "fréquence", "التكرار"]
FREQUENCY_EXACT = ["sig", "times", "x/day"]

EXACT = {"medication": MEDICATION_EXACT, "dose": DOSE_EXACT, "unit": UNIT_EXACT, "frequency": FREQUENCY_EXACT}

DOSE_VALUE_RE = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)\s*(?:mcg|ug|μg|㎍|mg|㎎|g)(?=$|[\s,;+/])", re.I)


def _key(column):
    return re.sub(r"[\s_\-().\[\]]", "", str(column).casefold())


def _name_score(column, keywords, exact=()):
    name = str(column).casefold().strip().replace(" ", "_")
    if _key(column) in {_key(word) for word in exact}:
        return 20
    return max((len(word) for word in keywords if word in name), default=0)


def _med_name_score(column):
    # "투약량" holds "투약" but is a dose column: a longer dose/unit/frequency match wins.
    score = _name_score(column, MEDICATION_KEYWORDS, MEDICATION_EXACT)
    other = max(_name_score(column, DOSE_KEYWORDS, DOSE_EXACT), _name_score(column, UNIT_KEYWORDS, UNIT_EXACT),
                _name_score(column, FREQUENCY_KEYWORDS, FREQUENCY_EXACT))
    return score if score > other else 0


def _patient_name_score(column):
    exact = {_key(word) for word in PATIENT_KEYWORDS}
    if _key(column) in exact:
        return 100
    name = str(column).casefold().strip().replace(" ", "_")
    if any(word in name for word in PATIENT_PARTS):
        return 50
    return 0


def _content_score(series):
    values = [str(value).strip() for value in series.dropna().head(100) if str(value).strip()]
    if not values:
        return 0.0
    return sum(bool(DOSE_VALUE_RE.search(value)) for value in values) / len(values)


def _drug_name_score(series):
    """Share of cells that contain a known drug name ("ris 3, olan 10"), for files whose drug column has no usual header."""
    from services.parser import dictionary_match
    values = [str(value).strip() for value in series.dropna().head(100) if str(value).strip()]
    if not values:
        return 0.0
    return sum(dictionary_match(value) is not None for value in values) / len(values)


def detect_columns(df):
    patient_scores = {col: _patient_name_score(col) for col in df.columns}
    patient_col = max(patient_scores, key=patient_scores.get) if any(patient_scores.values()) else None

    medication_scores = {}
    has_named_medication = any(_med_name_score(col) for col in df.columns)
    for col in df.columns:
        name_score = _med_name_score(col)
        # A separate dose column (e.g. "10mg 15mg") is not a drug column.
        if has_named_medication and not name_score and (_name_score(col, DOSE_KEYWORDS, DOSE_EXACT) or _name_score(col, UNIT_KEYWORDS, UNIT_EXACT) or _name_score(col, FREQUENCY_KEYWORDS, FREQUENCY_EXACT)):
            medication_scores[col] = -1
            continue
        content_score = _content_score(df[col])
        # 실제 '약물+용량' 값이 가장 강한 근거이며, 명확한 열 이름은 보조 근거다.
        medication_scores[col] = content_score * 100 + min(name_score, 20)
    medication_col = max(medication_scores, key=medication_scores.get) if medication_scores else None
    best_content = _content_score(df[medication_col]) if medication_col is not None else 0
    best_name = _med_name_score(medication_col) if medication_col is not None else 0
    if best_content == 0 and best_name == 0:
        medication_col = None
        # Last resort: a column of drug names written without mg and under an unusual header (e.g. "aps").
        name_scores = {col: _drug_name_score(df[col]) for col in df.columns if col != patient_col}
        if name_scores and max(name_scores.values()) >= 0.5:
            medication_col = max(name_scores, key=name_scores.get)

    def best_named(keywords, exact, excluded=()):
        scores = {col: _name_score(col, keywords, exact) for col in df.columns if col not in excluded}
        return max(scores, key=scores.get) if scores and any(scores.values()) else None

    dose_col = best_named(DOSE_KEYWORDS, DOSE_EXACT, excluded=(medication_col,))
    unit_col = best_named(UNIT_KEYWORDS, UNIT_EXACT, excluded=(medication_col, dose_col))
    frequency_col = best_named(FREQUENCY_KEYWORDS, FREQUENCY_EXACT, excluded=(medication_col, dose_col, unit_col))

    return {
        "patient_column": patient_col,
        "medication_column": medication_col,
        "dose_column": dose_col,
        "unit_column": unit_col,
        "frequency_column": frequency_col,
    }


def detect_medication_groups(df):
    """Pair numbered drug/dose/unit/frequency columns by their explicit suffix."""
    groups = {}
    for column in df.columns:
        match = re.fullmatch(r'(.+?)[_\s]*(\d+)', str(column).strip())
        if not match:
            continue
        base, number = match.groups()
        base = base.rstrip('_ ').casefold()
        for kind, keywords in [('medication_column', MEDICATION_KEYWORDS + MEDICATION_EXACT),
                               ('dose_column', DOSE_KEYWORDS + DOSE_EXACT),
                               ('unit_column', UNIT_KEYWORDS + UNIT_EXACT),
                               ('frequency_column', FREQUENCY_KEYWORDS + FREQUENCY_EXACT)]:
            if base in keywords:
                groups.setdefault(number, {})[kind] = column
                break
    result = []
    for number in sorted(groups, key=int):
        group = groups[number]
        if 'medication_column' in group:
            result.append({key: group.get(key) for key in ('medication_column', 'dose_column', 'unit_column', 'frequency_column')})
    return result
