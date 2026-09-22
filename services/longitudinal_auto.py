"""Zero-configuration longitudinal CSV/Excel processing for the main uploader."""
from collections import defaultdict
from datetime import datetime

import pandas as pd

from services.longitudinal import (FIELDS, REQUIRED, analyze, detect_mapping,
                                  export_zip, norm, parse_date, prepare,
                                  reference_pairs)

REFERENCE_HEADERS = ['reference_date', 'index_date', 'baseline_date', 'mri_date',
                     'assessment_date', '기준일', '검사일', '평가일', 'MRI촬영일']


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
    explicit = defaultdict(set)
    for sheet, frame in sheets.items():
        if frame.empty:
            continue
        mapping = detect_mapping(frame.columns)
        missing = [k for k in REQUIRED if not mapping[k]]
        if missing:
            raise ValueError(f'{sheet}: 종단 처방 필수 열을 자동 연결하지 못했습니다 ({", ".join(missing)}). 열 이름을 patient_id, PRESCR_DATE, DRUG, TABS_PER_DAY, PRESCR_DAYS로 지정하거나 상세 설정을 사용하세요.')
        refcols = [c for c in frame.columns if norm(c) in {norm(a) for a in REFERENCE_HEADERS}]
        if len(refcols) > 1:
            raise ValueError(f'{sheet}: 기준일 후보 열이 여러 개입니다. 분석할 열 하나만 reference_date로 남기거나 상세 설정에서 기준일을 지정하세요.')
        mappings[sheet] = dict(mapping, reference_date=refcols[0] if refcols else '')
        for i, row in enumerate(frame.to_dict('records')):
            if not any(str(v).strip() for v in row.values()):
                continue
            record = {k: str(row.get(mapping[k], '')).strip() if mapping[k] else '' for k in FIELDS}
            record['date'] = date_cell(row[mapping['date']])
            if refcols and str(row[refcols[0]]).strip():
                if not record['patient']:
                    raise ValueError(f'{sheet}: 기준일이 있으나 피험자 ID가 없는 행이 있습니다.')
                explicit[record['patient']].add(parse_date(date_cell(row[refcols[0]])))
            standardized.append(record)
            provenance.append((sheet, i + 2 + int(frame.attrs.get('header_row', 0))))
    if not standardized or len(standardized) > 100000:
        raise ValueError('종단 자료는 전체 시트 합계 1~100,000행이어야 합니다.')
    frame = pd.DataFrame(standardized)
    records = prepare(frame, {k:k for k in FIELDS}, 'review', provenance)
    fallback = {(r['patient'], r['start']) for r in records if r['patient'] and r['start']}
    pairs = sorted({(p, d) for p, d in fallback if p not in explicit} |
                   {(p, d) for p, dates in explicit.items() for d in dates})
    if not pairs or len(pairs) > 30000:
        raise ValueError('유효한 기준일 조합이 없거나 30,000개를 초과합니다. 날짜를 확인하거나 피험자를 나눠 주세요.')
    counts = defaultdict(int)
    for r in records:
        counts[r['patient']] += 1
    if sum(counts[p] for p, _ in pairs) > 10000000:
        raise ValueError('처리량이 큽니다. 피험자별로 파일을 나눠 주세요.')
    results, details = analyze(records, pairs, methods=methods, policy='review')
    for r in results:
        r['reference_basis'] = 'explicit_reference_date' if r['patient_id'] in explicit else 'each_prescription_date'
    return export_zip(records, results, details, dict(policy='review', mode='automatic', mapping=mappings,
                      source_sha256=source_sha256, release=release or {},
                      reference_rule='Use explicit reference date when supplied per patient; otherwise every prescription date.',
                      date_basis='prescription_date_as_start', dose_basis='recognized_daily_tablets_column'))
