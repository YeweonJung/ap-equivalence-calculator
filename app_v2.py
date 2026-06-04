from flask import Flask, render_template_string, request
import pandas as pd

DB_PATH = "/mnt/c/Users/jyo52/OneDrive/Desktop/계산툴개발/AP_Equiv_Project/raw_data/DRUG_DATABASE_fixed.xlsx"

app = Flask(**name**)

db = pd.read_excel(
DB_PATH,
sheet_name="Master_Conversion_DB "
)

methods = sorted(db["method_id"].dropna().unique())

HTML = """

<!DOCTYPE html>

<html>
<head>
<title>AP Equivalence Calculator</title>
<style>
body{
    font-family:Arial;
    margin:40px;
}
label{
    display:block;
    margin-top:15px;
}
.result{
    margin-top:30px;
    padding:20px;
    background:#f4f4f4;
    font-size:22px;
}
</style>
</head>
<body>

<h1>Antipsychotic Equivalence Calculator</h1>

<form method="POST">

<label>Method</label> <select name="method">
{% for m in methods %}

<option value="{{m}}">{{m}}</option>
{% endfor %}
</select>

<label>Source Drug</label> <input name="source_drug" required>

<label>Target Drug</label> <input name="target_drug" required>

<label>Dose (mg)</label> <input name="dose" type="number" step="0.01" required>

<br><br> <button type="submit">Convert</button>

</form>

{% if result %}

<div class="result">
{{result}}
</div>
{% endif %}

</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def home():

```
result = None

if request.method == "POST":

    method = request.form["method"]
    source = request.form["source_drug"].strip()
    target = request.form["target_drug"].strip()
    dose = float(request.form["dose"])

    row = db[
        (db["method_id"].str.upper()==method.upper()) &
        (db["source_drug"].astype(str).str.upper()==source.upper()) &
        (db["target_drug"].astype(str).str.upper()==target.upper())
    ]

    if len(row)==0:

        row = db[
            (db["method_id"].str.upper()==method.upper()) &
            (db["source_drug"].astype(str).str.upper()==target.upper()) &
            (db["target_drug"].astype(str).str.upper()==source.upper())
        ]

        if len(row)==0:
            result = "Conversion not found."

        else:

            factor = float(row.iloc[0]["inverse_factor"])

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
```

if **name** == "**main**":
app.run(
host="0.0.0.0",
port=5001,
debug=True
)
