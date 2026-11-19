"""Stateless CSV upload endpoints; no clinical data goes to feedback/LLM storage."""
import hashlib
import io
import json

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file

from services.longitudinal import (FIELDS, analyze_export, detect_mapping,
                                  prepare, reference_pairs)
from services.release import metadata
from services.file_reader import csv_layout

bp = Blueprint('longitudinal', __name__)
MAX_BYTES = 15 * 1024 * 1024
MAX_ROWS = 100000


def read_excel_upload(raw):
    import tempfile
    from services.file_reader import _read_excel_sheet
    with tempfile.NamedTemporaryFile(suffix='.xlsx') as handle:
        handle.write(raw); handle.flush()
        try:
            excel = pd.ExcelFile(handle.name)
        except Exception as exc:
            raise ValueError('Excel 파일을 열 수 없습니다. 파일이 손상되지 않았는지 확인하세요.') from exc
        with excel:
            sheets = [name for name in excel.sheet_names if not excel.parse(name, header=None, nrows=2).dropna(how='all').empty]
            if not sheets:
                raise ValueError('Excel 파일에 내용이 있는 시트가 없습니다.')
            if len(sheets) > 1:
                raise ValueError('내용이 있는 시트가 여러 개입니다(' + ', '.join(sheets) + '). 분석할 처방 시트 하나만 남겨 주세요.')
            frame = _read_excel_sheet(excel, sheets[0])
    if len(frame) > MAX_ROWS:
        raise ValueError('파일은 100,000행 이하로 나눠 주세요.')
    return frame.fillna('')


def read_csv_upload(upload):
    name = upload.filename.lower() if upload and upload.filename else ''
    if not name.endswith(('.csv', '.xlsx', '.xls')):
        raise ValueError('CSV 또는 Excel 파일을 선택하세요.')
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('파일은 15MB 이하로 나눠 주세요.')
    if not name.endswith('.csv'):
        return read_excel_upload(raw), hashlib.sha256(raw).hexdigest()
    for encoding in ('utf-8-sig', 'cp949', 'euc-kr'):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            delimiter, header_row = csv_layout(text)
            frame = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, keep_default_na=False, skip_blank_lines=False, skiprows=header_row, nrows=MAX_ROWS + 1)
            frame.attrs['header_row'] = header_row
            if len(frame) > MAX_ROWS:
                raise ValueError('CSV는 100,000행 이하로 나눠 주세요.')
            return frame.fillna(''), hashlib.sha256(raw).hexdigest()
        except (pd.errors.ParserError, pd.errors.EmptyDataError, IndexError) as exc:
            raise ValueError('CSV 구조를 읽을 수 없습니다. 첫 행의 열 이름과 구분자를 확인하세요.') from exc
    raise ValueError('CSV 인코딩을 확인하세요. UTF-8 또는 CP949를 지원합니다.')


@bp.after_request
def no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def _methods():
    from services.converter import available_methods
    from services.result_summary import METHOD_ORDER
    return [m for m in METHOD_ORDER if m in available_methods()]


def _base_method(value):
    # Same rule as the main calculator: ED95 unless another supported method is chosen.
    if value is None or value == '':
        return 'ED95'
    if not isinstance(value, str) or value.strip().upper() not in _methods():
        raise ValueError('지원하는 기준 방법을 하나 선택해 주세요.')
    return value.strip().upper()


@bp.get('/longitudinal')
def page():
    return render_template('longitudinal.html', fields=FIELDS, methods=_methods())


@bp.post('/api/longitudinal/inspect')
def inspect():
    try:
        frame, _ = read_csv_upload(request.files.get('file'))
        mapping = detect_mapping(frame.columns)
        return jsonify(columns=list(frame.columns), mapping=mapping, rows=len(frame), recognized=all(mapping[k] for k in ('patient', 'date', 'drug', 'daily')))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@bp.post('/api/longitudinal/analyze')
def calculate():
    try:
        if request.form.get('ack') != 'yes':
            raise ValueError('처방일과 일일 정 수의 의미를 확인하세요.')
        frame, digest = read_csv_upload(request.files.get('file'))
        mapping = json.loads(request.form.get('mapping', '{}'))
        if not isinstance(mapping, dict) or any(not isinstance(v, str) for v in mapping.values()) or set(mapping) - set(FIELDS):
            raise ValueError('열 연결 형식을 확인하세요.')
        mapping = mapping or detect_mapping(frame.columns)
        policy = 'prescription_date'
        mode = request.form.get('mode', 'all_dates')
        base_method = _base_method(request.form.get('base_method'))
        refs = read_csv_upload(request.files.get('references'))[0] if mode == 'per_patient' else None
        records = prepare(frame, mapping, policy)
        pairs = reference_pairs(records, mode, request.form.get('reference_date', ''), refs)
        # Bound output volume and CPU before generating method-by-row details.
        counts = {}
        for r in records:
            counts[r['patient']] = counts.get(r['patient'], 0) + 1
        if sum(counts.get(p, 0) for p, _ in pairs) > 10000000:
            raise ValueError('처리량이 큽니다. 기준일이나 피험자를 나눠 주세요.')
        release = metadata()
        out = analyze_export(records, pairs, dict(policy=policy, mode=mode, mapping=mapping, source_sha256=digest, date_basis='exact_prescription_date', dose_basis='tablets_per_day', release=release, base_method=base_method), policy=policy)
        from services.longitudinal_excel import FILENAME, MIMETYPE
        return send_file(out, as_attachment=True, download_name=FILENAME, mimetype=MIMETYPE)
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
