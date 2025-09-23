import pandas as pd
import glob
import os

def process_csv_last_row(file):
    """
    Convert numeric columns to percentages of the last row,
    force last row to 100%, round to 2 decimals, save _percent.csv
    Handles NaNs and int/float dtype issues.
    """
    df = pd.read_csv(file, sep=",", encoding="utf-8")
    num_cols = df.columns[1:]

    # Ensure numeric columns are floats
    df[num_cols] = df[num_cols].astype(float)

    # Separate data rows and last row
    data = df.iloc[:-1]
    last_row = df.iloc[-1]

    # Divide each column by last row, handle NaNs, cast to float
    percentages = (data[num_cols].div(last_row[num_cols]) * 100).astype(float)
    df.iloc[:-1, 1:] = percentages

    # Force last row to 100
    df.iloc[-1, 1:] = 100.0

    # Round
    df[num_cols] = df[num_cols].round(2)

    # Save
    out_file = os.path.splitext(file)[0] + "_percent.csv"
    df.to_csv(out_file, index=False, encoding="utf-8")
    print(f"Processed {file} -> {out_file}")





# -------- Old folders ----------

# 00_Total_Nacional
nacional_files = glob.glob("output/csv/00_Total_Nacional/*.csv")
for file in nacional_files:
    if os.path.basename(file) == "00_Total_Nacional.csv":
        continue
    process_csv_last_row(file)

# 28_Tamaulipas
tamaulipas_files = glob.glob("output/csv/28_Tamaulipas/*.csv")
for file in tamaulipas_files:
    if os.path.basename(file).startswith("00_Total"):
        continue
    process_csv_last_row(file)

# 28_Regional (all subfolders)
regional_files = glob.glob("output/csv/28_Regional/**/*.csv", recursive=True)
regions = ["Frontera", "Ribereña", "Reynosa", "Matamoros", "Centro", "Mante", "Sur"]
for file in regional_files:
    if os.path.basename(file).startswith("00_Total"):
        continue
    if any(region in file for region in regions):
        process_csv_last_row(file)


# -------- New proportional folders ----------

# # 1. proportional_national_state
# prop_nat_files = glob.glob("output/csv/proportional_national_state/*.csv")
# for file in prop_nat_files:
#     process_csv_last_row(file)
#
# # 2. proportional_state_regions (subfolders)
# prop_state_files = glob.glob("output/csv/proportional_state_regions/**/*.csv", recursive=True)
# for file in prop_state_files:
#     process_csv_last_row(file)
#
# # 3. proportional_region_weight (subfolders)
# prop_weight_files = glob.glob("output/csv/proportional_region_weight/**/*.csv", recursive=True)
# for file in prop_weight_files:
#     process_csv_last_row(file)
