import os
import pandas as pd

# ---------------- Config ----------------
REGIONAL_FOLDER = "output/csv/28_Regional"
OUTPUT_BASE = REGIONAL_FOLDER  # folders will be created inside this
REGIONS = ["Frontera", "Ribereña", "Reynosa", "Matamoros", "Centro", "Mante", "Sur"]

# Get all regional CSV files
regional_files = [f for f in os.listdir(REGIONAL_FOLDER) if f.endswith("_Regional.csv")]

for file_name in regional_files:
    file_path = os.path.join(REGIONAL_FOLDER, file_name)
    df = pd.read_csv(file_path, encoding="utf-8-sig")

    # Variable name from file
    variable_name = file_name.replace("_Regional.csv", "")

    for region in REGIONS:
        # Columns that belong to this region
        region_cols = [c for c in df.columns if c.startswith(region)]
        if not region_cols:
            continue

        # Base column(s)
        base_cols = [c for c in ["Actividad económica"] if c in df.columns]

        df_region = df[base_cols + region_cols].copy()

        # --- Rename columns ---
        new_cols = {}
        for col in region_cols:
            # Keep the suffix (e.g. 2008) but replace prefix with variable name
            if "_" in col:
                suffix = col.split("_", 1)[1]   # "2008"
                new_cols[col] = f"{variable_name}_{suffix}"
            else:
                new_cols[col] = variable_name
        df_region.rename(columns=new_cols, inplace=True)

        # Create folder for this region
        region_folder = os.path.join(OUTPUT_BASE, region)
        os.makedirs(region_folder, exist_ok=True)

        # Save CSV
        output_file = os.path.join(region_folder, f"{variable_name}_{region}.csv")
        df_region.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(f"✔ Procesado {variable_name} -> {region}")

print("✅ Regional CSVs split, headers fixed, and saved into separate folders.")
