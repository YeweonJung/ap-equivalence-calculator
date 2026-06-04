from flask import Flask, render_template, request, send_file
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

DB_PATH = (
    "/mnt/c/Users/jyo52/OneDrive/Desktop/"
    "계산툴개발/AP_Equiv_Project/raw_data/"
    "DRUG_DATABASE_fixed.xlsx"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

drug_db = pd.read_excel(DB_PATH)

drug_db.columns = drug_db.columns.str.strip()


def calculate_equiv(input_df):

    input_df.columns = input_df.columns.str.strip()

    merged = input_df.merge(
        drug_db,
        on="Drug",
        how="left"
    )

    merged["AP_Equivalent"] = (
        merged["Dose"] *
        merged["CPZ_factor"]
    )

    return merged


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():

    file = request.files["file"]

    upload_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    file.save(upload_path)

    df = pd.read_excel(upload_path)

    result = calculate_equiv(df)

    output_file = os.path.join(
        OUTPUT_FOLDER,
        "AP_equivalent_result.xlsx"
    )

    result.to_excel(
        output_file,
        index=False
    )

    return send_file(
        output_file,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
