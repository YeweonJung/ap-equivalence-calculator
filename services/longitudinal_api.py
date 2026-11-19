"""Stateless CSV upload endpoints; no clinical data goes to feedback/LLM storage."""
import hashlib
import io
import json
import re

import pandas as pd
from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from services.longitudinal import (FIELDS, analyze_export, detect_mapping,
                                  prepare, reference_pairs)
from services.release import metadata
from services.heavy_lock import one_at_a_time

bp = Blueprint('longitudinal', __name__)
MAX_BYTES = 15 * 1024 * 1024
ROWS_MESSAGE = '한 번에 처방 2,000행까지 계산합니다(지금 {n}). 환자별로 파일을 나눠 차례로 올려 주세요.'
# Measured on the hosted server: about 30 ms per row, and 3,000 rows ran it out of memory.
MAX_ROWS = 2000
UNEXPECTED = '파일을 처리하지 못했습니다. Excel에서 열어 Excel 통합 문서(.xlsx)로 다시 저장한 뒤 올려 주세요. 그래도 안 되면 파일 형식(확장자, 시트 수, 첫 몇 줄 모양)을 알려 주세요.'


def read_csv_upload(upload):
    from services.emr_reader import read_prescription_table
    from services.longitudinal import norm
    name = upload.filename.lower() if upload and upload.filename else ''
    if not name:
        raise ValueError('처방 파일을 선택하세요.')
    if not name.endswith(('.csv', '.xlsx', '.xls', '.xlsm', '.txt', '.tsv', '.htm', '.html')):
        raise ValueError('CSV 또는 Excel 파일을 선택하세요.')
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('파일은 15MB 이하로 나눠 주세요.')
    aliases = {norm(a) for names in FIELDS.values() for a in names}
    frame = read_prescription_table(raw, MAX_ROWS, aliases, {norm(a) for a in FIELDS['date']})
    return frame, hashlib.sha256(raw).hexdigest()


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
    return render_template('longitudinal.html', fields=FIELDS, methods=_methods(), detected_notice=request.args.get('from') == 'upload')


@bp.post('/api/longitudinal/inspect')
def inspect():
    try:
        with one_at_a_time():
            return _inspect()
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


def _inspect():
    try:
        frame, _ = read_csv_upload(request.files.get('file'))
        mapping = detect_mapping(frame.columns)
        # A name that occurs twice ('처방일', '처방일 (2)') is never chosen for the researcher.
        duplicated = {base for base in (re.sub(r' \(\d+\)$', '', c) for c in frame.columns if re.search(r' \(\d+\)$', c)) if base in frame.columns}
        mapping = {k: ('' if v in duplicated else v) for k, v in mapping.items()}
        return jsonify(columns=list(frame.columns), mapping=mapping, rows=len(frame), duplicated=sorted(duplicated),
                       recognized=all(mapping[k] for k in ('patient', 'date', 'drug', 'daily')))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        # Never a bare server error: log it and tell the researcher what to try.
        current_app.logger.exception('hospital data upload failed')
        return jsonify(error=UNEXPECTED), 400


@bp.post('/api/longitudinal/analyze')
def calculate():
    try:
        with one_at_a_time():
            return _calculate()
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


def _calculate():
    try:
        if request.form.get('ack') != 'yes':
            raise ValueError('처방일과 일일 정 수의 의미를 확인하세요.')
        frame, digest = read_csv_upload(request.files.get('file'))
        try:
            mapping = json.loads(request.form.get('mapping', '{}') or '{}')
        except ValueError:
            raise ValueError('열 연결 형식을 확인하세요.') from None
        if not isinstance(mapping, dict) or any(not isinstance(v, str) for v in mapping.values()) or set(mapping) - set(FIELDS):
            raise ValueError('열 연결 형식을 확인하세요.')
        if not mapping:
            duplicated = {re.sub(r' \(\d+\)$', '', c) for c in frame.columns if re.search(r' \(\d+\)$', c)}
            mapping = {k: ('' if v in duplicated else v) for k, v in detect_mapping(frame.columns).items()}
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
    except Exception:
        # Never a bare server error: log it and tell the researcher what to try.
        current_app.logger.exception('hospital data upload failed')
        return jsonify(error=UNEXPECTED), 400
