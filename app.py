import io
import os
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from services.anonymizer import anonymize_dataframe
from services.column_detector import detect_columns
from services.converter import available_methods, convert_drug, normalize_target
from services.exporter import export_results
from services.file_reader import read_file
from services.medication_splitter import split_medications
from services.parser import parse_medication
from services.validator import validate_file


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
METHODS = available_methods()


@app.get("/")
def home():
    return render_template("index.html", methods=METHODS)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample")
def sample_file():
    sample = "patient_id,medication\nP001,Risperdal 2mg BID\nP002,Abilify 15mg QD\n"
    return send_file(
        io.BytesIO(sample.encode("utf-8-sig")),
        as_attachment=True,
        download_name="AP_equivalence_sample.csv",
        mimetype="text/csv; charset=utf-8",
    )


@app.post("/upload")
def upload():
    uploaded_file = request.files.get("file")
    method = request.form.get("method", "").strip().upper()

    try:
        validate_file(uploaded_file)
        target = normalize_target(method)
    except ValueError as exc:
        return render_template("error.html", message=str(exc)), 400

    filename = secure_filename(uploaded_file.filename) or "upload.xlsx"
    suffix = Path(filename).suffix.lower()
    detailed_rows, audit_rows, error_rows = [], [], []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / f"upload{suffix}"
            uploaded_file.save(upload_path)
            sheets = read_file(str(upload_path))

            for sheet_name, dataframe in sheets.items():
                detected = detect_columns(dataframe)
                patient_col = detected["patient_column"]
                medication_col = detected["medication_column"]

                if medication_col is None:
                    error_rows.append({"sheet": sheet_name, "patient": "", "original": "", "error": "약물 열을 찾지 못했습니다."})
                    continue

                anonymized, _ = anonymize_dataframe(dataframe)
                for _, row in anonymized.iterrows():
                    patient_id = row.get(patient_col, "") if patient_col is not None else ""
                    for medication in split_medications(row.get(medication_col)):
                        try:
                            parsed = parse_medication(medication)
                            equivalent = convert_drug(parsed["drug"], parsed["daily_dose_mg"], method, target)
                            detailed_rows.append({
                                "sheet": sheet_name,
                                "patient": patient_id,
                                "original": medication,
                                "drug": parsed["drug"],
                                "dose_mg": parsed["dose_mg"],
                                "frequency": parsed["frequency"],
                                "daily_dose_mg": parsed["daily_dose_mg"],
                                "method": method,
                                "target_drug": target,
                                "equivalent_dose_mg": round(equivalent, 4),
                                "warning": parsed["warning"],
                            })
                            audit_rows.append({"sheet": sheet_name, "patient": patient_id, "original": medication, "parsed": parsed["drug"], "status": "converted"})
                        except (ValueError, LookupError) as exc:
                            error_rows.append({"sheet": sheet_name, "patient": patient_id, "original": medication, "error": str(exc)})

            output_file = export_results(detailed_rows, audit_rows, error_rows, directory=temp_dir)
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
