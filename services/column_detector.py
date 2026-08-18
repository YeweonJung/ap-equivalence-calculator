import re


PATIENT_KEYWORDS = ["patient_id", "patient", "subject", "participant", "mrn", "id", "name", "환자번호", "환자", "대상자", "등록번호", "차트번호"]

MEDICATION_KEYWORDS = ["medications", "medication", "prescription", "medicine", "drug", "rx", "처방내역", "처방약", "처방", "투약내역", "투약", "약물정보", "약물명", "약제"]

DOSE_VALUE_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:mcg|ug|μg|㎍|mg|㎎|g)\b", re.I)


def _name_score(column, keywords):
    name = str(column).casefold().strip().replace(" ", "_")
    return max((len(word) for word in keywords if word in name), default=0)


def _content_score(series):
    values = [str(value).strip() for value in series.dropna().head(100) if str(value).strip()]
    if not values:
        return 0.0
    return sum(bool(DOSE_VALUE_RE.search(value)) for value in values) / len(values)


def detect_columns(df):
    patient_scores = {col: _name_score(col, PATIENT_KEYWORDS) for col in df.columns}
    patient_col = max(patient_scores, key=patient_scores.get) if any(patient_scores.values()) else None

    medication_scores = {}
    for col in df.columns:
        name_score = _name_score(col, MEDICATION_KEYWORDS)
        content_score = _content_score(df[col])
        # 실제 '약물+용량' 값이 가장 강한 근거이며, 명확한 열 이름은 보조 근거다.
        medication_scores[col] = content_score * 100 + min(name_score, 20)
    medication_col = max(medication_scores, key=medication_scores.get) if medication_scores else None
    best_content = _content_score(df[medication_col]) if medication_col is not None else 0
    best_name = _name_score(medication_col, MEDICATION_KEYWORDS) if medication_col is not None else 0
    if best_content == 0 and best_name == 0:
        medication_col = None

    return {"patient_column": patient_col, "medication_column": medication_col}
