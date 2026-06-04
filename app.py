from flask import Flask, request, render_template_string
import pandas as pd

app = Flask(__name__)

lookup = pd.read_csv("master_lookup.csv")

methods = sorted(
    lookup["method_id"].dropna().unique()
)

drugs = sorted(
    lookup["source_drug"].dropna().unique()
)

HTML = """
<!DOCTYPE html>
<html>
<head>

<title>AP Equivalence Calculator</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

<style>

body{
    background:#f5f7fa;
}

.main-card{
    max-width:1100px;
    margin:auto;
    margin-top:40px;
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

<select
name="method"
class="form-select">

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

<select
name="source_drug"
class="form-select">

{% for d in drugs %}
<option value="{{d}}">
{{d}}
</option>
{% endfor %}

</select>

</div>

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
class="btn btn-primary mt-4"
type="submit">
Convert
</button>

</form>

{% if table %}

<hr>

<h4>
Equivalent Doses
</h4>

{{ table|safe }}

{% endif %}

</div>

</div>

</div>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():

    table = None

    if request.method == "POST":

        method = request.form["method"]
        source = request.form["source_drug"]
        dose = float(request.form["dose"])

        tmp = lookup[
            (lookup["method_id"] == method)
            &
            (lookup["source_drug"] == source)
        ].copy()

        tmp["Equivalent Dose (mg)"] = (
            tmp["factor"] * dose
        )

        tmp = tmp[
            [
                "target_drug",
                "Equivalent Dose (mg)"
            ]
        ]

        tmp.columns = [
            "Target Drug",
            "Equivalent Dose (mg)"
        ]

        tmp["Equivalent Dose (mg)"] = (
            tmp["Equivalent Dose (mg)"]
            .round(2)
        )

        table = tmp.to_html(
            classes="table table-striped table-hover",
            index=False
        )

    return render_template_string(
        HTML,
        methods=methods,
        drugs=drugs,
        table=table
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
