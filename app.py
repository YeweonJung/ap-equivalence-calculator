from flask import (
    Flask,
    render_template,
    request,
    send_file
)

import os
import pandas as pd

from services.validator import (
    validate_file
)

from services.file_reader import (
    read_file
)

from services.column_detector import (
    detect_columns
)

from services.anonymizer import (
    anonymize_dataframe
)

from services.medication_splitter import (
    split_medications
)

from services.parser import (
    dictionary_match,
    fuzzy_match
)

from services.llm_batch_parser import (
    batch_parse_medications
)

from services.converter import (
    convert_drug
)

from services.exporter import (
    export_results
)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

lookup = pd.read_csv(
    "lookup/master_lookup.csv"
)

METHODS = sorted(
    lookup["method_id"].unique()
)


@app.route("/")
def home():

    return render_template(
        "index.html",
        methods=METHODS
    )


@app.route(
    "/upload",
    methods=["POST"]
)
def upload():

    file = request.files["file"]

    validate_file(file)

    method = request.form[
        "method"
    ]

    upload_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    file.save(upload_path)

    sheets = read_file(
        upload_path
    )

    detailed_rows = []
    audit_rows = []
    error_rows = []

    for sheet_name, df in (
        sheets.items()
    ):

        detected = (
            detect_columns(df)
        )

        patient_col = (
            detected[
                "patient_column"
            ]
        )

        medication_col = (
            detected[
                "medication_column"
            ]
        )

        if medication_col is None:

            error_rows.append(
                {
                    "sheet":
                    sheet_name,

                    "error":
                    "Medication column not found"
                }
            )

            continue

        anon_df, _ = (
            anonymize_dataframe(
                df
            )
        )

        unresolved = []

        unresolved_meta = []

        for idx, row in (
            anon_df.iterrows()
        ):

            patient_id = None

            if patient_col:

                patient_id = (
                    row[
                        patient_col
                    ]
                )

            meds = (
                split_medications(
                    row[
                        medication_col
                    ]
                )
            )

            for med in meds:

                drug = (
                    dictionary_match(
                        med
                    )
                )

                parser_method = (
                    "dictionary"
                )

                if not drug:

                    drug = (
                        fuzzy_match(
                            med
                        )
                    )

                    parser_method = (
                        "fuzzy"
                    )

                if drug:

                    audit_rows.append(
                        {
                            "sheet":
                            sheet_name,

                            "patient":
                            patient_id,

                            "original":
                            med,

                            "parsed":
                            drug,

                            "confidence":
                            1.0,

                            "parser_method":
                            parser_method
                        }
                    )

                else:

                    unresolved.append(
                        med
                    )

                    unresolved_meta.append(
                        (
                            sheet_name,
                            patient_id,
                            med
                        )
                    )

        if unresolved:

            llm_results = (
                batch_parse_medications(
                    unresolved
                )
            )

            for meta, result in zip(
                unresolved_meta,
                llm_results
            ):

                sheet_name, patient_id, original = meta

                audit_rows.append(
                    {
                        "sheet":
                        sheet_name,

                        "patient":
                        patient_id,

                        "original":
                        original,

                        "parsed":
                        result.get(
                            "drug"
                        ),

                        "confidence":
                        result.get(
                            "confidence"
                        ),

                        "parser_method":
                        "llm"
                    }
                )

    output_file = (
        export_results(
            detailed_rows,
            audit_rows,
            error_rows
        )
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
