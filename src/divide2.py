import os
import pandas as pd
import numpy as np

BASE_CSV_DIR = "output/csv"
TAMAULIPAS_DIR = os.path.join(BASE_CSV_DIR, "28_Tamaulipas")
REGIONAL_DIRS = {
    "Centro": "28_Regional/Centro",
    "Frontera": "28_Regional/Frontera",
    "Mante": "28_Regional/Mante",
    "Matamoros": "28_Regional/Matamoros",
    "Reynosa": "28_Regional/Reynosa",
    "Ribereña": "28_Regional/Ribereña",
    "Sur": "28_Regional/Sur"
}

OUTPUT_DIR = os.path.join(BASE_CSV_DIR, "prop_state_regions")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VARIABLES = ["A111A", "A121A", "A211A", "A221A"]


def read_with_header_fix(file_path):
    """
    Lee un CSV intentando detectar si la primera fila es un header válido.
    Si no, usa la segunda fila como header (header=1).
    """
    preview = pd.read_csv(file_path, nrows=2, header=None)
    first_row = preview.iloc[0].astype(str).tolist()
    if all(col.startswith("C") and col[1:].isdigit() for col in first_row):
        df = pd.read_csv(file_path, header=1)
    else:
        df = pd.read_csv(file_path, header=0)
    return df


for region_name, region_path in REGIONAL_DIRS.items():
    region_output_dir = os.path.join(OUTPUT_DIR, region_name)
    os.makedirs(region_output_dir, exist_ok=True)

    for var in VARIABLES:
        tamaulipas_file = os.path.join(TAMAULIPAS_DIR, f"{var}_Tamaulipas.csv")
        region_file = os.path.join(BASE_CSV_DIR, region_path, f"{var}_{region_name}.csv")

        if not os.path.exists(tamaulipas_file) or not os.path.exists(region_file):
            print(f"⚠️ Files for {var} in region {region_name} not found, skipping")
            continue

        df_tam = read_with_header_fix(tamaulipas_file)
        df_region = read_with_header_fix(region_file)

        df_result = pd.DataFrame()
        if "Actividad económica" in df_tam.columns:
            df_result["Actividad económica"] = df_tam["Actividad económica"]

        tam_data = df_tam.drop(columns=["Actividad económica"], errors="ignore")
        region_data = df_region.drop(columns=["Actividad económica"], errors="ignore")

        df_div = tam_data.values / np.where(region_data.values == 0, np.nan, region_data.values)
        df_result = pd.concat([df_result, pd.DataFrame(df_div, columns=tam_data.columns)], axis=1)

        # 👉 Nombre del archivo con la región incluida
        output_file = os.path.join(region_output_dir, f"{var}_{region_name}_proportional.csv")
        df_result.to_csv(output_file, index=False)

print("✅ All proportional CSVs created successfully with region names in filenames.")
