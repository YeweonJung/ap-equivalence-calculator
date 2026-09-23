"""Stateless CSV upload endpoints; no clinical data goes to feedback/LLM storage."""
import csv
import hashlib
import io
import json

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file

from services.longitudinal import (FIELDS, analyze_export, detect_mapping,
                                  prepare, reference_pairs)
from services.release import metadata

bp = Blueprint('longitudinal', __name__)
MAX_BYTES = 15 * 1024 * 1024
MAX_ROWS = 100000


def read_csv_upload(upload):
    if not upload or not upload.filename.lower().endswith('.csv'):
        raise ValueError('CSV 파일을 선택하세요.')
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('CSV는 15MB 이하로 나눠 주세요.')
    for encoding in ('utf-8-sig', 'cp949', 'euc-kr'):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            header = text.splitlines()[0]
            try:
                delimiter = csv.Sniffer().sniff(header, delimiters=',;\t|').delimiter
            except csv.Error:
                delimiter = ','
            cols = next(csv.reader(io.StringIO(text), delimiter=delimiter))
            if len(cols) != len(set(cols)):
                raise ValueError('중복 열 이름을 구분한 뒤 다시 업로드하세요.')
            frame = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, keep_default_na=False, skip_blank_lines=False, nrows=MAX_ROWS + 1)
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


@bp.get('/longitudinal')
def page():
    return render_template('longitudinal.html', fields=FIELDS)


@bp.post('/api/longitudinal/inspect')
def inspect():
    try:
        frame, _ = read_csv_upload(request.files.get('file'))
        mapping = detect_mapping(frame.columns)
        return jsonify(columns=list(frame.columns), mapping=mapping, rows=len(frame), recognized=all(mapping[k] for k in ('patient', 'date', 'drug', 'daily', 'days')))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@bp.post('/api/longitudinal/analyze')
def calculate():
    try:
        if request.form.get('ack') != 'yes':
            raise ValueError('처방 시작일과 일일 정 수의 의미를 확인하세요.')
        frame, digest = read_csv_upload(request.files.get('file'))
        mapping = json.loads(request.form.get('mapping', '{}'))
        if not isinstance(mapping, dict) or any(not isinstance(v, str) for v in mapping.values()) or set(mapping) - set(FIELDS):
            raise ValueError('열 연결 형식을 확인하세요.')
        mapping = mapping or detect_mapping(frame.columns)
        policy = request.form.get('policy', 'review')
        mode = request.form.get('mode', 'common')
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
        out = analyze_export(records, pairs, dict(policy=policy, mode=mode, mapping=mapping, source_sha256=digest, date_basis='prescription_date_as_start', dose_basis='tablets_per_day', release=release), policy=policy)
        from services.longitudinal_excel import FILENAME, MIMETYPE
        return send_file(out, as_attachment=True, download_name=FILENAME, mimetype=MIMETYPE)
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
