import os
import pandas as pd
import numpy as np

BASE_CSV_DIR = "output/csv"
OUTPUT_DIR = os.path.join(BASE_CSV_DIR, "proportional_national_state")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VARIABLES = ["A111A", "A121A", "A211A", "A221A"]
ENTIDADES = {
    "Nacional": "00_Total_Nacional",
    "Tamaulipas": "28_Tamaulipas"
}

for var in VARIABLES:
    nacional_file = os.path.join(BASE_CSV_DIR, ENTIDADES["Nacional"], f"{var}_Nacional.csv")
    tamaulipas_file = os.path.join(BASE_CSV_DIR, ENTIDADES["Tamaulipas"], f"{var}_Tamaulipas.csv")

    if not os.path.exists(nacional_file) or not os.path.exists(tamaulipas_file):
        print(f"⚠️ Files for {var} not found, skipping")
        continue

    df_nac = pd.read_csv(nacional_file)
    df_tam = pd.read_csv(tamaulipas_file)

    df_result = df_nac.copy()
    for col in df_result.columns:
        if col != "Actividad económica":
            if col in df_tam.columns:
                # División segura, reemplaza inf o división por 0
                df_result[col] = df_nac[col] / df_tam[col].replace({0: np.nan})
            else:
                df_result[col] = np.nan

    # Guardar CSV final por variable
    output_file = os.path.join(OUTPUT_DIR, f"{var}_proportional.csv")
    df_result.to_csv(output_file, index=False)

print("✅ 4 proportional CSVs created in 'proportional_national_state', division by zero handled.")
