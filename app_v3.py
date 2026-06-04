from flask import Flask, request, render_template_string
import pandas as pd

DB_PATH = "/mnt/c/Users/jyo52/OneDrive/Desktop/계산툴개발/AP_Equiv_Project/raw_data/DRUG_DATABASE_fixed.xlsx"

app = Flask(__name__)

db = pd.read_excel(
    DB_PATH,
    sheet_name="Master_Conversion_DB "
)

db["method_id"] = db["method_id"].astype(str)
db["source_drug"] = db["source_drug"].astype(str)
db["target_drug"] = db["target_drug"].astype(str)

methods = sorted(db["method_id"].dropna().unique())

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AP Equivalence Calculator</title>
    <style>
        body{
            font-family: Arial, sans-serif;
            margin:40px;
        }

        h1{
            color:#2c3e50;
        }

        label{
            display:block;
            margin-top:15px;
            font-weight:bold;
        }

        input, select{
            width:300px;
            padding:8px;
        }

        button{
            margin-top:20px;
            padding:10px 20px;
        }

        .result{
            margin-top:30px;
            padding:20px;
            background:#f0f4f8;
            border-radius:8px;
            font-size:20px;
        }
    </style>
</head>

<body>

<h1>Antipsychotic Equivalence Calculator</h1>

<form method="POST">

<label>Method</label>
<select name="method">
{% for m in methods %}
<option value="{{m}}">{{m}}</option>
{% endfor %}
</select>

<label>Source Drug</label>
<input type="text" name="source_drug" required>

<label>Target Drug</label>
<input type="text" name="target_drug" required>

<label>Dose (mg)</label>
<input type="number" step="0.01" name="dose" required>

<br>

<button type="submit">
Convert
</button>

</form>

{% if result %}
<div class="result">
{{ result }}
</div>
{% endif %}

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():

    result = None

    if request.method == "POST":

        method = request.form["method"].strip()
        source = request.form["source_drug"].strip().upper()
        target = request.form["target_drug"].strip().upper()
        dose = float(request.form["dose"])

        row = db[
            (db["method_id"].str.upper() == method.upper()) &
            (db["source_drug"].str.upper() == source) &
            (db["target_drug"].str.upper() == target)
        ]

        if len(row) == 0:

            reverse_row = db[
                (db["method_id"].str.upper() == method.upper()) &
                (db["source_drug"].str.upper() == target) &
                (db["target_drug"].str.upper() == source)
            ]

            if len(reverse_row) == 0:

                result = "Conversion not found."

            else:

                factor = float(reverse_row.iloc[0]["inverse_factor"])

                converted = dose * factor

                result = (
                    f"{dose:.2f} mg {source} "
                    f"= {converted:.2f} mg {target}"
                )

        else:

            factor = float(row.iloc[0]["factor"])

            converted = dose * factor

            result = (
                f"{dose:.2f} mg {source} "
                f"= {converted:.2f} mg {target}"
            )

    return render_template_string(
        HTML,
        methods=methods,
        result=result
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )
