import os
import pandas as pd
import numpy as np

# -----------------------------
# Directories
# -----------------------------
BASE_DIR = "output/csv"
NATIONAL_DIR = os.path.join(BASE_DIR, "00_Total_Nacional")
REGIONAL_DIR = os.path.join(BASE_DIR, "28_Regional")
OUTPUT_DIR = os.path.join(BASE_DIR, "proportional_region_weight")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# Variables to process
# -----------------------------
VARIABLES = ["A111A", "A121A", "A131A", "A221A"]

# -----------------------------
# Helper function
# -----------------------------
def read_with_header_fix(file_path):
    preview = pd.read_csv(file_path, nrows=2, header=None)
    first_row = preview.iloc[0].astype(str).tolist()
    if all(col.startswith("C") and col[1:].isdigit() for col in first_row):
        df = pd.read_csv(file_path, header=1)
    else:
        df = pd.read_csv(file_path, header=0)
    return df

# -----------------------------
# Process each region folder
# -----------------------------
for region in os.listdir(REGIONAL_DIR):
    region_path = os.path.join(REGIONAL_DIR, region)
    if not os.path.isdir(region_path):
        continue

    region_output_dir = os.path.join(OUTPUT_DIR, region)
    os.makedirs(region_output_dir, exist_ok=True)

    # Process each CSV in the region folder
    for file_name in os.listdir(region_path):
        if not file_name.endswith(".csv") or "_percent" in file_name:
            continue

        var = file_name.split("_")[0]  # Extract variable from file name

        # Skip variables not in the list
        if var not in VARIABLES:
            continue

        nat_file = os.path.join(NATIONAL_DIR, f"{var}_Nacional.csv")
        reg_file = os.path.join(region_path, file_name)

        if not os.path.exists(nat_file):
            print(f"⚠️ National file for {var} not found, skipping")
            continue

        # Read CSVs
        df_nat = read_with_header_fix(nat_file)
        df_reg = read_with_header_fix(reg_file)

        # Prepare result
        df_result = pd.DataFrame()
        if "Actividad económica" in df_nat.columns:
            df_result["Actividad económica"] = df_nat["Actividad económica"]

        nat_data = df_nat.drop(columns=["Actividad económica"], errors="ignore")
        reg_data = df_reg.drop(columns=["Actividad económica"], errors="ignore")

        # Safe division (inverted)
        df_div = reg_data.div(nat_data.replace(0, np.nan))
        df_result = pd.concat([df_result, df_div], axis=1)

        # Save output
        output_file = os.path.join(region_output_dir, f"{var}_{region}_weight.csv")
        df_result.to_csv(output_file, index=False)
        print(f"✅ Processed {var} for {region}")

print("✅ All proportional region weight CSVs created successfully.")
