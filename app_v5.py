from flask import Flask, request, render_template_string
import pandas as pd

DB_PATH = "raw_data/DRUG_DATABASE_fixed.xlsx"

app = Flask(__name__)

db = pd.read_excel(
DB_PATH,
sheet_name="Master_Conversion_DB "
)

drug_map = {
"OLZ": "olanzapine",
"RIS": "risperidone",
"CPZ": "chlorpromazine"
}

all_drugs = sorted(
list(
set(
db["source_drug"].dropna().astype(str)
).union(
set(
db["target_drug"].dropna().astype(str)
)
)
)
)

methods = sorted(
db["method_id"].dropna().unique()
)

HTML = """

<!DOCTYPE html>

<html>
<head>

<title>AP Equivalence Calculator</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body{
    background:#f8fafc;
}

.main-card{
    max-width:900px;
    margin:auto;
    margin-top:40px;
}

.result-card{
    margin-top:20px;
}
</style>

</head>

<body>

<div class="container">

<div class="card shadow main-card">

<div class="card-body">

<h2 class="mb-4">
Antipsychotic Equivalence Calculator
</h2>

<form method="POST">

<div class="row">

<div class="col-md-4">

<label class="form-label">
Method
</label>

<select name="method" class="form-select">

{% for m in methods %}

<option value="{{m}}">
{{m}}
</option>
{% endfor %}

</select>

</div>

<div class="col-md-4">

<label class="form-label">
Source Drug
</label>

<select name="source_drug" class="form-select">

{% for d in drugs %}

<option value="{{d}}">
{{d}}
</option>
{% endfor %}

</select>

</div>

<div class="col-md-4">

<label class="form-label">
Target Drug
</label>

<select name="target_drug" class="form-select">

{% for d in drugs %}

<option value="{{d}}">
{{d}}
</option>
{% endfor %}

</select>

</div>

</div>

<div class="row mt-3">

<div class="col-md-4">

<label class="form-label">
Dose (mg)
</label>

<input
type="number"
step="0.01"
name="dose"
class="form-control"
required>

</div>

</div>

<button
type="submit"
class="btn btn-primary mt-4">
Convert </button>

</form>

{% if result %}

<div class="alert alert-success result-card">

<h4>Result</h4>

<p>{{ result }}</p>

</div>

{% endif %}

{% if error %}

<div class="alert alert-danger result-card">

{{ error }}

</div>

{% endif %}

</div>

</div>

</div>

</body>
</html>
"""

def normalize_drug(drug):

```
drug = str(drug).strip()

if drug in drug_map:
    return drug_map[drug]

return drug
```

@app.route("/", methods=["GET", "POST"])
def home():

```
result = None
error = None

if request.method == "POST":

    method = request.form["method"]

    source = normalize_drug(
        request.form["source_drug"]
    )

    target = normalize_drug(
        request.form["target_drug"]
    )

    dose = float(
        request.form["dose"]
    )

    row = db[
        (db["method_id"].astype(str).str.upper() == method.upper())
        &
        (
            db["source_drug"]
            .astype(str)
            .str.lower()
            ==
            source.lower()
        )
        &
        (
            db["target_drug"]
            .astype(str)
            .str.lower()
            ==
            target.lower()
        )
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
            (db["method_id"].astype(str).str.upper() == method.upper())
            &
            (
                db["source_drug"]
                .astype(str)
                .str.lower()
                ==
                target.lower()
            )
            &
            (
                db["target_drug"]
                .astype(str)
                .str.lower()
                ==
                source.lower()
            )
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
                "for selected combination."
            )

return render_template_string(
    HTML,
    methods=methods,
    drugs=all_drugs,
    result=result,
    error=error
)
```

if __name__ == "__main__":
app.run(
host="0.0.0.0",
port=5002,
debug=True
)
