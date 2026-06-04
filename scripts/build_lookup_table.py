import pandas as pd
import numpy as np

DB_PATH = "raw_data/DRUG_DATABASE_fixed.xlsx"

df = pd.read_excel(
    DB_PATH,
    sheet_name="Master_Conversion_DB "
)

anchor_map = {
    "OLZ": "olanzapine",
    "RIS": "risperidone",
    "CPZ": "chlorpromazine"
}

all_rows = []

for method in sorted(df["method_id"].dropna().unique()):

    tmp = df[df["method_id"] == method].copy()

    anchor_code = str(tmp["source_drug"].iloc[0]).strip()

    if anchor_code not in anchor_map:
        continue

    anchor_name = anchor_map[anchor_code]

    factor_dict = {}

    factor_dict[anchor_name] = 1.0

    for _, row in tmp.iterrows():

        target = str(row["target_drug"]).strip()

        factor = row["factor"]

        if pd.isna(factor):
            continue

        factor_dict[target] = float(factor)

    drugs = sorted(factor_dict.keys())

    for source in drugs:

        for target in drugs:

            source_factor = factor_dict[source]
            target_factor = factor_dict[target]

            conversion_factor = (
                target_factor /
                source_factor
            )

            all_rows.append({
                "method_id": method,
                "source_drug": source,
                "target_drug": target,
                "factor": conversion_factor
            })

lookup = pd.DataFrame(all_rows)

lookup = lookup.sort_values(
    ["method_id",
     "source_drug",
     "target_drug"]
)

lookup.to_csv(
    "master_lookup.csv",
    index=False
)

print()
print("DONE")
print()
print("Rows:", len(lookup))
print()
print(lookup.head(20))
