import io
import os
import re
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from services.column_detector import detect_columns, detect_medication_groups
from services.converter import available_methods, normalize_target
from services.exporter import export_results
from services.file_reader import read_file
from services.medication_splitter import split_medications
from services.parser import DOSE_RE, parse_medication
from services.validator import validate_file
from services.frames import parse_frames, convert_frame, summarize_frames
from services.structured import structured_frames
from services.result_summary import result_rows, METHOD_ORDER, patient_results
from services.manual_suggestions import suggest_for_review as suggest_drugs


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
from services.feedback_api import bp as feedback_bp, attach_feedback
app.register_blueprint(feedback_bp)
from services.llm_worker_api import bp as llm_worker_bp
app.register_blueprint(llm_worker_bp)
from services.longitudinal_api import bp as longitudinal_bp
app.register_blueprint(longitudinal_bp)
METHODS = [method for method in METHOD_ORDER if method in available_methods()]


def _cell_text(value):
    text = "" if value is None else str(value).strip()
    return "" if text.casefold() in {"", "nan", "none", "null"} else text


def _compose_structured_medication(row, drug_text, dose_col, unit_col, frequency_col):
    dose = _cell_text(row.get(dose_col)) if dose_col is not None else ""
    unit = _cell_text(row.get(unit_col)) if unit_col is not None else ""
    frequency = _cell_text(row.get(frequency_col)) if frequency_col is not None else ""
    dose_header = str(dose_col or "").casefold()
    if not unit:
        unit_match = re.search(r"(?:^|[_\s(])(mcg|ug|μg|㎍|mg|㎎|g)(?:$|[_\s)])", dose_header)
        unit = unit_match.group(1) if unit_match else ""
    is_daily_dose = any(word in dose_header for word in ("daily", "일일", "1일"))
    if is_daily_dose:
        frequency = "QD"
    else:
        normalized_frequency = frequency.replace(".0", "")
        if normalized_frequency == "0.5":
            frequency = "QOD"
        elif normalized_frequency.isdigit():
            count = int(normalized_frequency)
            frequency = {1: "QD", 2: "BID", 3: "TID", 4: "QID"}.get(count, f"{count} times a day")
    return " ".join(part for part in (drug_text, f"{dose}{unit}" if dose else "", frequency) if part)


@app.get("/")
def home():
    return render_template("index.html", methods=METHODS)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    from services.release import metadata
    return metadata()


@app.get("/sample")
def sample_file():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "입력예시"
    sheet.append(["patient_id", "drug", "dose", "unit", "frequency"])
    sheet.append(["P001", "risperidone", 2, "mg", "QD"])
    sheet.append(["P001", "olanzapine", 5, "mg", "QD"])
    sheet.append(["P002", "risperidone", 1, "mg", "QD"])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1769E0")
        cell.alignment = Alignment(horizontal="center")
    for column, width in {"A": 16, "B": 20, "C": 12, "D": 10, "E": 16}.items():
        sheet.column_dimensions[column].width = width
    sample = io.BytesIO()
    workbook.save(sample)
    sample.seek(0)
    return send_file(
        sample,
        as_attachment=True,
        download_name="AP_equivalence_sample.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def quick_check_text():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get('text'), str):
        raise ValueError('약물 입력은 text 문자열로 보내 주세요.')
    text = payload['text'].strip()
    if not text:
        raise ValueError('약물과 용량을 입력해 주세요.')
    if len(text) > 10000:
        raise ValueError('한 줄 계산은 10,000자까지 지원합니다. 긴 처방은 파일 업로드를 이용해 주세요.')
    return text


@app.post('/api/export')
def export_quick_check():
    try:
        text = quick_check_text()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    workbook = Workbook()
    workbook.active.append(['patient_id', 'medication'])
    workbook.active.append(['P001', text])
    workbook.active.cell(2, 2).data_type = 's'
    content = io.BytesIO()
    workbook.save(content)
    content.seek(0)
    uploaded = FileStorage(stream=content, filename='quick_check.xlsx')
    return process_upload(uploaded, 'ALL')


@app.post("/api/parse")
def parse_text():
    try:
        text = quick_check_text()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    items = [convert_frame(frame, METHODS) for frame in parse_frames(text)]
    for item in items:
        if item['status'] == 'unknown_drug':
            if 'suggestions' not in item:
                item['suggestions'] = suggest_drugs(item['original'])
            attach_feedback(item)
    return jsonify({"items": items, "totals": summarize_frames(items, METHODS)})


@app.post("/upload")
def upload():
    uploaded_file = request.files.get("file")
    method = request.form.get("method", "ALL").strip().upper() or "ALL"
    return process_upload(uploaded_file, method)


def process_upload(uploaded_file, method):
    try:
        validate_file(uploaded_file)
        selected_methods = METHODS if method == "ALL" else [method]
        for selected_method in selected_methods:
            normalize_target(selected_method)
    except ValueError as exc:
        return render_template("error.html", message=str(exc)), 400

    original_suffix = Path(uploaded_file.filename).suffix.lower()
    filename = secure_filename(uploaded_file.filename) or f"upload{original_suffix}"
    suffix = original_suffix or Path(filename).suffix.lower()
    detailed_rows, audit_rows, error_rows, total_rows, summary_rows = [], [], [], [], []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / f"upload{suffix}"
            uploaded_file.save(upload_path)
            sheets = read_file(str(upload_path))
            from services.longitudinal import is_longitudinal
            if any(is_longitudinal(df.columns) for df in sheets.values()):
                import hashlib
                from services.longitudinal_auto import automatic_analysis
                from services.release import metadata
                output = automatic_analysis(sheets, selected_methods,
                    source_sha256=hashlib.sha256(upload_path.read_bytes()).hexdigest(), release=metadata())
                from services.longitudinal_excel import FILENAME, MIMETYPE
                response = send_file(output, as_attachment=True, download_name=FILENAME, mimetype=MIMETYPE, max_age=0)
                response.headers['Cache-Control'] = 'no-store'
                return response

            patients = {}
            used_ids = {str(value) for df in sheets.values()
                        for col in [detect_columns(df)['patient_column']] if col is not None
                        for value in df[col] if _cell_text(value)}
            for sheet_name, dataframe in sheets.items():
                detected = detect_columns(dataframe)
                patient_col = detected["patient_column"]
                medication_col = detected["medication_column"]
                dose_col = detected["dose_column"]
                unit_col = detected["unit_column"]
                frequency_col = detected["frequency_column"]

                groups = detect_medication_groups(dataframe) or [{"medication_column": medication_col, "dose_column": dose_col, "unit_column": unit_col, "frequency_column": frequency_col}]

                if medication_col is None and not any(g["medication_column"] for g in groups):
                    error_rows.append({"sheet": sheet_name, "source_row": "", "medication_column": "", "patient": "", "original": "", "error": "약물 열을 찾지 못했습니다."})
                    continue

                header_row = int(dataframe.attrs.get("header_row", 0))
                for row_index, row in dataframe.iterrows():
                    if not any(_cell_text(value) for value in row.values):
                        continue
                    patient_id = row.get(patient_col, "") if patient_col is not None else ""
                    source_row = int(row_index) + header_row + 2
                    if not _cell_text(patient_id):
                        patient_id = f'__MISSING_ID_{len(patients) + 1}'
                        while patient_id in used_ids:
                            patient_id += '_'
                        used_ids.add(patient_id)
                        error_rows.append({'sheet': sheet_name, 'source_row': source_row,
                                           'patient': patient_id, 'error': 'ID 누락: 원본 행별 임시 ID입니다. 병합 전 ID를 확인하세요.'})
                    patient_id = str(patient_id)
                    patients.setdefault(patient_id, [])
                    for group in groups:
                        medication_col, dose_col, unit_col, frequency_col = (group[key] for key in ("medication_column", "dose_column", "unit_column", "frequency_column"))
                        raw_medication = _cell_text(row.get(medication_col))
                        if not raw_medication:
                            continue
                        frames = structured_frames(row, raw_medication, dose_col, unit_col, frequency_col, _compose_structured_medication)
                        cell_items = []
                        for frame in frames:
                            parsed = convert_frame(frame, selected_methods)
                            cell_items.append(parsed)
                            context = {"sheet": sheet_name, "source_row": source_row,
                                       "medication_column": str(medication_col), "patient": patient_id}
                            record = {**context, **parsed}
                            conversions = parsed["conversions"]
                            for conversion in conversions:
                                if conversion["value"] is not None:
                                    detailed_rows.append({**record, "method": conversion["method"],
                                                          "target_drug": conversion["target"],
                                                          "equivalent_dose_mg": conversion["value"],
                                                          "conversion_basis": conversion.get("basis") or parsed.get("conversion_basis", ""),
                                                          "conversion_source": parsed.get("oral_bridge_source", "") if conversion.get("basis", "").startswith("경구") else parsed.get("conversion_source", "")})
                            audit_rows.append({**record, "parsed": parsed["drug"],
                                               "unavailable_methods": ", ".join(c["method"] for c in conversions if c["value"] is None)})
                            if not parsed["ok"] or parsed.get("unit_assumed"):
                                error_rows.append({**record, "error": parsed.get("error") or parsed["warning"] or parsed["status_message"]})

                        patients[patient_id].extend(cell_items)
                        cell_totals = summarize_frames(cell_items, selected_methods)
                        summary_rows.extend(result_rows(raw_medication, patient_id, cell_items, cell_totals))
                        for total in cell_totals:
                            total_rows.append({"sheet": sheet_name, "source_row": source_row,
                                               "medication_column": str(medication_col), "patient": patient_id,
                                               "original": raw_medication, **total})

            patient_rows, patient_checks = patient_results(patients, selected_methods)
            output_file = export_results(detailed_rows, audit_rows, error_rows, directory=temp_dir, total_rows=total_rows, summary_rows=summary_rows, patient_rows=patient_rows, patient_checks=patient_checks)
            result_bytes = io.BytesIO(Path(output_file).read_bytes())
            result_bytes.seek(0)
            return send_file(
                result_bytes,
                as_attachment=True,
                download_name="AP_equivalence_result.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    except (ValueError, OSError) as exc:
        return render_template("error.html", message=str(exc)), 400


@app.errorhandler(413)
def file_too_large(_error):
    return render_template("error.html", message="파일 크기는 최대 100MB입니다."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
