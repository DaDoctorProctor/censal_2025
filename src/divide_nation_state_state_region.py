import os
import pandas as pd
import numpy as np

BASE_CSV_DIR = "output/csv"
NATIONAL_STATE_DIR = os.path.join(BASE_CSV_DIR, "proportional_national_state")
STATE_REGION_DIR = os.path.join(BASE_CSV_DIR, "proportional_state_regions")
OUTPUT_DIR = os.path.join(BASE_CSV_DIR, "proportional_region_weight")

os.makedirs(OUTPUT_DIR, exist_ok=True)

VARIABLES = ["A111A", "A121A", "A131A", "A221A"]
REGIONS = ["Centro", "Frontera", "Mante", "Matamoros", "Reynosa", "Ribereña", "Sur"]


def read_with_header_fix(file_path):
    """Asegura que se lea el encabezado correcto (detecta si la primera fila es dummy)."""
    preview = pd.read_csv(file_path, nrows=2, header=None)
    first_row = preview.iloc[0].astype(str).tolist()
    if all(col.startswith("C") and col[1:].isdigit() for col in first_row):
        df = pd.read_csv(file_path, header=1)
    else:
        df = pd.read_csv(file_path, header=0)
    return df


for region in REGIONS:
    region_output_dir = os.path.join(OUTPUT_DIR, region)
    os.makedirs(region_output_dir, exist_ok=True)

    for var in VARIABLES:
        # Archivos fuente
        nat_file = os.path.join(NATIONAL_STATE_DIR, f"{var}_proportional.csv")
        reg_file = os.path.join(STATE_REGION_DIR, region, f"{var}_{region}_proportional.csv")

        if not os.path.exists(nat_file) or not os.path.exists(reg_file):
            print(f"⚠️ Files for {var} in region {region} not found, skipping")
            continue

        df_nat = read_with_header_fix(nat_file)
        df_reg = read_with_header_fix(reg_file)

        # Construcción resultado
        df_result = pd.DataFrame()
        if "Actividad económica" in df_nat.columns:
            df_result["Actividad económica"] = df_nat["Actividad económica"]

        nat_data = df_nat.drop(columns=["Actividad económica"], errors="ignore")
        reg_data = df_reg.drop(columns=["Actividad económica"], errors="ignore")

        # División segura por posición
        df_div = nat_data.values / np.where(reg_data.values == 0, np.nan, reg_data.values)
        df_result = pd.concat([df_result, pd.DataFrame(df_div, columns=nat_data.columns)], axis=1)

        # Guardar archivo final
        output_file = os.path.join(region_output_dir, f"{var}_{region}_weight.csv")
        df_result.to_csv(output_file, index=False)

print("✅ All proportional region weight CSVs created successfully in 'proportional_region_weight'.")
