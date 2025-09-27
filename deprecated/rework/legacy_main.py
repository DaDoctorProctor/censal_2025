import os
import re
import shutil
import glob
import numpy as np
import pandas as pd

# -----------------------
# Shared helpers (from process_saic.py)
# -----------------------
regions_map = {
    "Frontera": ["027 Nuevo Laredo"],
    "Ribereña": ["007 Camargo", "014 Guerrero", "015 Gustavo Díaz Ordaz", "024 Mier", "025 Miguel Alemán"],
    "Reynosa": ["005 Burgos", "032 Reynosa", "033 Río Bravo", "023 Méndez"],
    "Matamoros": ["010 Cruillas", "035 San Fernando", "022 Matamoros", "040 Valle Hermoso"],
    "Centro": [
        "001 Abasolo", "008 Casas", "013 Güémez", "016 Hidalgo", "018 Jiménez", "019 Llera", "020 Mainero",
        "030 Padilla", "034 San Carlos", "036 San Nicolás", "037 Soto la Marina", "041 Victoria", "042 Villagrán"
    ],
    "Mante": [
        "004 Antiguo Morelos", "006 Bustamante", "017 Jaumave", "026 Miquihuana", "031 Palmillas", "039 Tula",
        "021 El Mante", "011 Gómez Farías", "012 González", "028 Nuevo Morelos", "029 Ocampo", "043 Xicoténcatl"
    ],
    "Sur": ["002 Aldama", "003 Altamira", "009 Ciudad Madero", "038 Tampico"]
}
YEARS = [2008, 2013, 2018, 2023]
INPUT_CSV = "input/SAIC_Exporta_Clean.csv"
OUTPUT_DIR = "output"


def sanitize_filename(name):
    s = re.sub(r'[^\w\s-]', '', name)
    s = re.sub(r'\s+', '_', s.strip())
    return s


def clean_sectores_column(df):
    if "Actividad económica" in df.columns:
        df["Actividad económica"] = df["Actividad económica"].apply(
            lambda x: re.sub(r'Sector\s*\d+(-\d+)?\s*', '', str(x))
        )
    return df


def add_total_row_to_df(df):
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    total_row = {col: df[col].sum() if col in numeric_cols else "" for col in df.columns}
    if "Actividad económica" in df.columns:
        total_row["Actividad económica"] = "Total"
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)


def process_variable(df, variable, regions_local):
    results = []
    for region, municipios in regions_local.items():
        temp = (
            df[df["Municipio"].isin(municipios) & (df["Municipio"] != "")]
            .groupby(["Año Censal", "Actividad económica"], as_index=False)[variable]
            .sum()
        )
        temp["Region"] = region
        results.append(temp)

    combined = pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["Año Censal", "Actividad económica", variable, "Region"])
    if combined.empty:
        pivoted = pd.DataFrame()
    else:
        pivoted = combined.pivot_table(
            index="Actividad económica",
            columns=["Region", "Año Censal"],
            values=variable,
            aggfunc="sum",
            fill_value=0
        )

    col_tuples = [(region, year) for region in regions_local.keys() for year in YEARS]
    if pivoted.empty:
        activities = df["Actividad económica"].unique().tolist()
        pivoted = pd.DataFrame(0, index=activities, columns=pd.MultiIndex.from_tuples(col_tuples))
    else:
        for tup in col_tuples:
            if tup not in pivoted.columns:
                pivoted[tup] = 0

    pivoted = pivoted[[ (region, year) for region in regions_local.keys() for year in YEARS ]]
    pivoted.columns = [f"{region}_{year}" for region, year in pivoted.columns]
    pivoted.reset_index(inplace=True)
    pivoted.rename(columns={"index": "Actividad económica"}, inplace=True)
    return pivoted


# ---------------- Steps replicated from individual scripts ----------------

def step1_clear_output_csv():
    folder_path = "output/csv"
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
        print(f"All files in '{folder_path}' have been cleared.")
    else:
        print(f"The folder '{folder_path}' does not exist.")


def step2_process_saic():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(INPUT_CSV, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["Municipio"] = df["Municipio"].fillna("").astype(str).str.strip()
    df["Año Censal"] = pd.to_numeric(df["Año Censal"], errors='coerce')
    df = df[df["Año Censal"] >= 2008]

    global YEARS
    YEARS = [year for year in YEARS if year >= 2008]

    # Export national and state wide CSVs
    csv_dir = os.path.join(OUTPUT_DIR, "csv")
    os.makedirs(csv_dir, exist_ok=True)

    for entidad, label in [("00 Total Nacional", "00_Total_Nacional"), ("28 Tamaulipas", "28_Tamaulipas")]:
        df_filtered = df[(df["Entidad"] == entidad) & (df["Municipio"].str.strip() == "")]
        if df_filtered.empty:
            continue
        df_filtered = df_filtered[df_filtered["Año Censal"].isin(YEARS)]
        required = ["Año Censal", "Entidad", "Municipio", "Actividad económica"]
        var_cols = [c for c in df_filtered.columns if c not in required]

        pivot_list = []
        for var in var_cols:
            temp = df_filtered.pivot_table(
                index="Actividad económica",
                columns="Año Censal",
                values=var,
                aggfunc="sum",
                fill_value=0
            )
            code = var.split()[0]
            temp.columns = [f"{code}_{int(col)}" for col in temp.columns]
            pivot_list.append(temp)

        if pivot_list:
            df_wide = pd.concat(pivot_list, axis=1)
        else:
            df_wide = pd.DataFrame()
        df_wide.reset_index(inplace=True)
        df_wide.rename(columns={"index": "Actividad económica"}, inplace=True)
        df_wide = clean_sectores_column(df_wide)

        for col in df_wide.columns:
            if col != "Actividad económica":
                df_wide[col] = pd.to_numeric(df_wide[col], errors='coerce').fillna(0)

        df_wide = df_wide[["Actividad económica"] + sorted([c for c in df_wide.columns if c != "Actividad económica"])]
        df_wide = add_total_row_to_df(df_wide)

        filename_safe = sanitize_filename(label)
        csv_path = os.path.join(csv_dir, f"{filename_safe}.csv")
        df_wide.to_csv(csv_path, index=False)

        split_folder = os.path.join(csv_dir, filename_safe)
        os.makedirs(split_folder, exist_ok=True)
        shutil.move(csv_path, split_folder)
        moved_csv_path = os.path.join(split_folder, f"{filename_safe}.csv")
        df_wide = pd.read_csv(moved_csv_path)

        variable_cols = [c for c in df_wide.columns if c != "Actividad económica"]
        variable_codes = sorted(set(c.split("_")[0] for c in variable_cols))
        for code in variable_codes:
            cols_for_var = [c for c in df_wide.columns if c.startswith(code)]
            df_var = df_wide[["Actividad económica"] + cols_for_var].copy()
            cols_sorted = ["Actividad económica"] + sorted([c for c in df_var.columns if c != "Actividad económica"])
            df_var = df_var[cols_sorted]

            suffix = "Nacional" if entidad == "00 Total Nacional" else "Tamaulipas"
            file_name = f"{code}_{suffix}.csv"
            file_path = os.path.join(split_folder, file_name)
            df_var.to_csv(file_path, index=False)

    # Prepare numeric columns and regional outputs
    required = ["Año Censal", "Entidad", "Municipio", "Actividad económica"]
    all_cols = list(df.columns)
    var_cols = [c for c in all_cols if c not in required]
    for v in var_cols:
        df[v] = pd.to_numeric(df[v].str.replace(',', '').str.strip(), errors='coerce').fillna(0)

    csv_dir = os.path.join(OUTPUT_DIR, "csv")
    regional_folder = os.path.join(csv_dir, "28_Regional")
    os.makedirs(regional_folder, exist_ok=True)

    for var in var_cols:
        print(f"Processing regional variable: {var}")
        pivot = process_variable(df, var, regions_map)
        pivot = clean_sectores_column(pivot)
        pivot = add_total_row_to_df(pivot)
        code = var.split()[0]
        pivot.columns = ["Actividad económica"] + [f"{col.split('_')[0]}_{col.split('_')[1]}" for col in pivot.columns[1:]]
        pivot = pivot[["Actividad económica"] + sorted([c for c in pivot.columns if c != "Actividad económica"])]
        csv_path = os.path.join(regional_folder, f"{code}_Regional.csv")
        pivot.to_csv(csv_path, index=False)

    print("✅ All CSVs now include a single total row and alphabetically sorted headers.")


def step3_divide_national_state():
    BASE_CSV_DIR = "output/csv"
    OUTPUT_DIR = os.path.join(BASE_CSV_DIR, "proportional_national_state")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    VARIABLES = ["A111A", "A121A", "A131A", "A221A"]
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
                    df_result[col] = df_tam[col].replace({0: np.nan}) / df_nac[col]
                else:
                    df_result[col] = np.nan

        output_file = os.path.join(OUTPUT_DIR, f"{var}_proportional.csv")
        df_result.to_csv(output_file, index=False)

    print("✅ 4 proportional CSVs created in 'proportional_national_state', division by zero handled.")


def read_with_header_fix(file_path):
    preview = pd.read_csv(file_path, nrows=2, header=None)
    first_row = preview.iloc[0].astype(str).tolist()
    if all(col.startswith("C") and col[1:].isdigit() for col in first_row):
        df = pd.read_csv(file_path, header=1)
    else:
        df = pd.read_csv(file_path, header=0)
    return df


def step4_split_regional():
    REGIONAL_FOLDER = "output/csv/28_Regional"
    OUTPUT_BASE = REGIONAL_FOLDER
    REGIONS = ["Frontera", "Ribereña", "Reynosa", "Matamoros", "Centro", "Mante", "Sur"]

    if not os.path.isdir(REGIONAL_FOLDER):
        print(f"⚠️ Regional folder not found: {REGIONAL_FOLDER}")
        return

    regional_files = [f for f in os.listdir(REGIONAL_FOLDER) if f.endswith("_Regional.csv")]

    for file_name in regional_files:
        file_path = os.path.join(REGIONAL_FOLDER, file_name)
        df = pd.read_csv(file_path, encoding="utf-8-sig")

        variable_name = file_name.replace("_Regional.csv", "")

        for region in REGIONS:
            region_cols = [c for c in df.columns if c.startswith(region)]
            if not region_cols:
                continue

            base_cols = [c for c in ["Actividad económica"] if c in df.columns]
            df_region = df[base_cols + region_cols].copy()

            new_cols = {}
            for col in region_cols:
                if "_" in col:
                    suffix = col.split("_", 1)[1]
                    new_cols[col] = f"{variable_name}_{suffix}"
                else:
                    new_cols[col] = variable_name
            df_region.rename(columns=new_cols, inplace=True)

            region_folder = os.path.join(OUTPUT_BASE, region)
            os.makedirs(region_folder, exist_ok=True)

            output_file = os.path.join(region_folder, f"{variable_name}_{region}.csv")
            df_region.to_csv(output_file, index=False, encoding="utf-8-sig")

            print(f"✔ Procesado {variable_name} -> {region}")

    print("✅ Regional CSVs split, headers fixed, and saved into separate folders.")


def step5_divide_state_region():
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

    OUTPUT_DIR = os.path.join(BASE_CSV_DIR, "proportional_state_regions")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    VARIABLES = ["A111A", "A121A", "A131A", "A221A"]

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

            df_div = region_data.values / np.where(tam_data.values == 0, np.nan, tam_data.values)
            df_result = pd.concat([df_result, pd.DataFrame(df_div, columns=tam_data.columns)], axis=1)

            output_file = os.path.join(region_output_dir, f"{var}_{region_name}_proportional.csv")
            df_result.to_csv(output_file, index=False)

    print("✅ All proportional CSVs created successfully with region names in filenames.")


def step6_divide_nation_state_state_region():
    BASE_CSV_DIR = "output/csv"
    NATIONAL_STATE_DIR = os.path.join(BASE_CSV_DIR, "proportional_national_state")
    STATE_REGION_DIR = os.path.join(BASE_CSV_DIR, "proportional_state_regions")
    OUTPUT_DIR = os.path.join(BASE_CSV_DIR, "proportional_region_weight")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    VARIABLES = ["A111A", "A121A", "A131A", "A221A"]
    REGIONS = ["Centro", "Frontera", "Mante", "Matamoros", "Reynosa", "Ribereña", "Sur"]

    for region in REGIONS:
        region_output_dir = os.path.join(OUTPUT_DIR, region)
        os.makedirs(region_output_dir, exist_ok=True)

        for var in VARIABLES:
            nat_file = os.path.join(NATIONAL_STATE_DIR, f"{var}_proportional.csv")
            reg_file = os.path.join(STATE_REGION_DIR, region, f"{var}_{region}_proportional.csv")

            if not os.path.exists(nat_file) or not os.path.exists(reg_file):
                print(f"⚠️ Files for {var} in region {region} not found, skipping")
                continue

            df_nat = read_with_header_fix(nat_file)
            df_reg = read_with_header_fix(reg_file)

            df_result = pd.DataFrame()
            if "Actividad económica" in df_nat.columns:
                df_result["Actividad económica"] = df_nat["Actividad económica"]

            nat_data = df_nat.drop(columns=["Actividad económica"], errors="ignore")
            reg_data = df_reg.drop(columns=["Actividad económica"], errors="ignore")

            df_div = nat_data.values / np.where(reg_data.values == 0, np.nan, reg_data.values)
            df_result = pd.concat([df_result, pd.DataFrame(df_div, columns=nat_data.columns)], axis=1)

            output_file = os.path.join(region_output_dir, f"{var}_{region}_weight.csv")
            df_result.to_csv(output_file, index=False)

    print("✅ All proportional region weight CSVs created successfully in 'proportional_region_weight'.")


def step7_process_percentages():
    def process_csv_last_row(file):
        df = pd.read_csv(file, sep=",", encoding="utf-8")
        num_cols = df.columns[1:]
        df[num_cols] = df[num_cols].astype(float)
        data = df.iloc[:-1]
        last_row = df.iloc[-1]
        percentages = (data[num_cols].div(last_row[num_cols]) * 100).astype(float)
        df.iloc[:-1, 1:] = percentages
        df.iloc[-1, 1:] = 100.0
        df[num_cols] = df[num_cols].round(2)
        out_file = os.path.splitext(file)[0] + "_percent.csv"
        df.to_csv(out_file, index=False, encoding="utf-8")
        print(f"Processed {file} -> {out_file}")

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

    # 28_Regional
    regional_files = glob.glob("output/csv/28_Regional/**/*.csv", recursive=True)
    regions = ["Frontera", "Ribereña", "Reynosa", "Matamoros", "Centro", "Mante", "Sur"]
    for file in regional_files:
        if os.path.basename(file).startswith("00_Total"):
            continue
        if any(region in file for region in regions):
            process_csv_last_row(file)

    # Uncomment this if percentages are also required for proportional_* folders
    # for folder in [
    #     "output/csv/proportional_national_state",
    #     "output/csv/proportional_state_regions",
    #     "output/csv/proportional_region_weight",
    # ]:
    #     files = glob.glob(os.path.join(folder, "**/*.csv"), recursive=True)
    #     for file in files:
    #         process_csv_last_row(file)


def main():
    print("Running step 1: Clear output folder...")
    step1_clear_output_csv()

    print("Running step 2: Process SAIC and generate base CSVs...")
    step2_process_saic()

    print("Running step 3: Divide National / State...")
    step3_divide_national_state()

    print("Running step 4: Split regional CSVs...")
    step4_split_regional()

    print("Running step 5: Divide State / Region...")
    step5_divide_state_region()

    print("Running step 6: Compute (National/State) / (State/Region)...")
    step6_divide_nation_state_state_region()

    print("Running step 7: Generate percentage CSVs...")
    step7_process_percentages()

    print("✅ All steps completed in all_in_one pipeline.")


if __name__ == "__main__":
    main()
