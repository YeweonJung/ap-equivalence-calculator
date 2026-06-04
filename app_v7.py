from flask import Flask, request, render_template_string
import pandas as pd

app = Flask(__name__)

DB_PATH = "raw_data/DRUG_DATABASE_fixed.xlsx"

# -------------------------
# Load Database
# -------------------------
db = pd.read_excel(
    DB_PATH,
    sheet_name="Master_Conversion_DB "
)

db["method_id"] = db["method_id"].astype(str)
db["source_drug"] = db["source_drug"].astype(str)
db["target_drug"] = db["target_drug"].astype(str)

methods = sorted(
    db["method_id"].dropna().unique()
)

drugs = sorted(
    list(
        set(db["source_drug"].dropna())
        |
        set(db["target_drug"].dropna())
    )
)

# -------------------------
# HTML
# -------------------------
HTML = """
<!DOCTYPE html>
<html>

<head>

<title>AP Equivalence Calculator</title>

<style>

body{
    font-family: Arial, sans-serif;
    background:#f4f6f9;
}

.container{
    max-width:900px;
    margin:auto;
    margin-top:40px;
    background:white;
    padding:30px;
    border-radius:10px;
    box-shadow:0px 0px 15px rgba(0,0,0,0.1);
}

h1{
    color:#2c3e50;
}

label{
    display:block;
    margin-top:15px;
    font-weight:bold;
}

select,input{
    width:100%;
    padding:10px;
    margin-top:5px;
}

button{
    margin-top:20px;
    padding:12px;
    width:100%;
    background:#2563eb;
    color:white;
    border:none;
    border-radius:5px;
    font-size:16px;
}

.result{
    margin-top:25px;
    padding:20px;
    background:#e8f5e9;
    border-radius:5px;
    font-size:20px;
}

.error{
    margin-top:25px;
    padding:20px;
    background:#ffebee;
    border-radius:5px;
    color:#c62828;
}

</style>

</head>

<body>

<div class="container">

<h1>AP Equivalence Calculator</h1>

<form method="POST">

<label>Method</label>

<select name="method">
{% for m in methods %}
<option value="{{m}}">
{{m}}
</option>
{% endfor %}
</select>

<label>Source Drug</label>

<select name="source_drug">
{% for d in drugs %}
<option value="{{d}}">
{{d}}
</option>
{% endfor %}
</select>

<label>Target Drug</label>

<select name="target_drug">
{% for d in drugs %}
<option value="{{d}}">
{{d}}
</option>
{% endfor %}
</select>

<label>Dose (mg)</label>

<input
type="number"
step="0.01"
name="dose"
required>

<button type="submit">
Convert
</button>

</form>

{% if result %}
<div class="result">
{{ result }}
</div>
{% endif %}

{% if error %}
<div class="error">
{{ error }}
</div>
{% endif %}

</div>

</body>
</html>
"""

# -------------------------
# Main Route
# -------------------------
@app.route("/", methods=["GET", "POST"])
def home():

    result = None
    error = None

    if request.method == "POST":

        method = request.form["method"]
        source = request.form["source_drug"]
        target = request.form["target_drug"]
        dose = float(request.form["dose"])

        row = db[
            (db["method_id"] == method)
            &
            (db["source_drug"].str.lower() == source.lower())
            &
            (db["target_drug"].str.lower() == target.lower())
        ]

        if len(row) > 0:

            factor = float(
                row.iloc[0]["factor"]
            )

            converted = dose * factor

            result = (
                f"{dose:.2f} mg {source} "
                f"= "
                f"{converted:.2f} mg {target}"
            )

        else:

            reverse_row = db[
                (db["method_id"] == method)
                &
                (db["source_drug"].str.lower() == target.lower())
                &
                (db["target_drug"].str.lower() == source.lower())
            ]

            if len(reverse_row) > 0:

                factor = float(
                    reverse_row.iloc[0]["inverse_factor"]
                )

                converted = dose * factor

                result = (
                    f"{dose:.2f} mg {source} "
                    f"= "
                    f"{converted:.2f} mg {target}"
                )

            else:

                error = (
                    "No conversion found "
                    "for this combination."
                )

    return render_template_string(
        HTML,
        methods=methods,
        drugs=drugs,
        result=result,
        error=error
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5004,
        debug=True
    )
