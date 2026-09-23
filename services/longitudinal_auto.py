"""Zero-configuration longitudinal CSV/Excel processing for the main uploader."""
from collections import defaultdict
from datetime import datetime

import pandas as pd

from services.longitudinal import (FIELDS, REQUIRED, analyze_export, detect_mapping,
                                  prepare)

def date_cell(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    # pandas' Excel reader serializes actual midnight date cells this way.
    if len(text) == 19 and text.endswith(' 00:00:00'):
        return text[:10]
    return text


def automatic_analysis(sheets, methods, source_sha256='', release=None):
    standardized, provenance, mappings = [], [], {}
    for sheet, frame in sheets.items():
        if frame.empty:
            continue
        mapping = detect_mapping(frame.columns)
        missing = [k for k in REQUIRED[:-1] if not mapping[k]]
        if missing:
            raise ValueError(f'{sheet}: 종단 처방 필수 열을 자동 연결하지 못했습니다 ({", ".join(missing)}). 열 이름을 patient_id, PRESCR_DATE, DRUG, TABS_PER_DAY로 지정하거나 상세 설정을 사용하세요.')
        mappings[sheet] = dict(mapping)
        for i, row in enumerate(frame.to_dict('records')):
            if not any(str(v).strip() for v in row.values()):
                continue
            record = {k: str(row.get(mapping[k], '')).strip() if mapping[k] else '' for k in FIELDS}
            record['date'] = date_cell(row[mapping['date']])
            standardized.append(record)
            provenance.append((sheet, i + 2 + int(frame.attrs.get('header_row', 0))))
    if not standardized or len(standardized) > 100000:
        raise ValueError('종단 자료는 전체 시트 합계 1~100,000행이어야 합니다.')
    frame = pd.DataFrame(standardized)
    records = prepare(frame, {k:k for k in FIELDS}, 'prescription_date', provenance)
    del standardized, provenance, frame
    fallback = {(r['patient'], r['start']) for r in records if r['patient'] and r['start']}
    pairs = sorted(fallback)
    if not pairs or len(pairs) > 30000:
        raise ValueError('유효한 기준일 조합이 없거나 30,000개를 초과합니다. 날짜를 확인하거나 피험자를 나눠 주세요.')
    counts = defaultdict(int)
    for r in records:
        counts[r['patient']] += 1
    if sum(counts[p] for p, _ in pairs) > 10000000:
        raise ValueError('처리량이 큽니다. 피험자별로 파일을 나눠 주세요.')
    def annotate(results):
        for r in results:
            r['reference_basis'] = 'each_prescription_date'
    return analyze_export(records, pairs, dict(policy='prescription_date', mode='automatic', mapping=mappings,
                      source_sha256=source_sha256, release=release or {},
                      reference_rule='Group by patient ID and exact prescription date; ignore overlapping durations and reference-date columns.',
                      date_basis='exact_prescription_date', dose_basis='recognized_daily_tablets_column'),
                      methods=methods, policy='prescription_date', result_transform=annotate)
