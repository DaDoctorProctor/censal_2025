# process_saic.py
import os
import re
import shutil
import pandas as pd

# -----------------------
# Configuration / Globals
# -----------------------
regions = {
    "Frontera": ["027 Nuevo Laredo"],
    "Ribereña": ["007 Camargo", "014 Guerrero", "015 Gustavo Díaz Ordaz", "024 Mier", "025 Miguel Alemán"],
    "Reynosa": ["005 Burgos", "032 Reynosa", "033 Río Bravo", "023 Méndez"],
    "Matamoros": ["010 Cruillas", "035 San Fernando", "022 Matamoros", "040 Valle Hermoso"],
    "Centro": ["001 Abasolo", "008 Casas", "013 Güémez", "016 Hidalgo", "018 Jiménez", "019 Llera", "020 Mainero",
               "030 Padilla", "034 San Carlos", "036 San Nicolás", "037 Soto la Marina", "041 Victoria", "042 Villagrán"],
    "Mante": ["004 Antiguo Morelos", "006 Bustamante", "017 Jaumave", "026 Miquihuana", "031 Palmillas", "039 Tula",
              "021 El Mante", "011 Gómez Farías", "012 González", "028 Nuevo Morelos", "029 Ocampo", "043 Xicoténcatl"],
    "Sur": ["002 Aldama", "003 Altamira", "009 Ciudad Madero", "038 Tampico"]
}

YEARS = [2008, 2013, 2018, 2023]
INPUT_CSV = "input/SAIC_Exporta_Clean.csv"
OUTPUT_DIR = "output"

# ---------------- Helper functions ----------------
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
    pivoted = combined.pivot_table(
        index="Actividad económica",
        columns=["Region", "Año Censal"],
        values=variable,
        aggfunc="sum",
        fill_value=0
    ) if not combined.empty else pd.DataFrame()

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

def export_nation_state_wide_csvs(df, years, output_dir):
    csv_dir = os.path.join(output_dir, "csv")
    os.makedirs(csv_dir, exist_ok=True)

    for entidad, label in [("00 Total Nacional", "00_Total_Nacional"), ("28 Tamaulipas", "28_Tamaulipas")]:
        df_filtered = df[(df["Entidad"] == entidad) & (df["Municipio"].str.strip() == "")]
        if df_filtered.empty: continue
        df_filtered = df_filtered[df_filtered["Año Censal"].isin(years)]
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

        df_wide = pd.concat(pivot_list, axis=1)
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

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(INPUT_CSV, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["Municipio"] = df["Municipio"].fillna("").astype(str).str.strip()
    df["Año Censal"] = pd.to_numeric(df["Año Censal"], errors='coerce')
    df = df[df["Año Censal"] >= 2008]

    global YEARS
    YEARS = [year for year in YEARS if year >= 2008]

    export_nation_state_wide_csvs(df, YEARS, OUTPUT_DIR)

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
        pivot = process_variable(df, var, regions)
        pivot = clean_sectores_column(pivot)
        pivot = add_total_row_to_df(pivot)
        code = var.split()[0]
        pivot.columns = ["Actividad económica"] + [f"{col.split('_')[0]}_{col.split('_')[1]}" for col in pivot.columns[1:]]
        pivot = pivot[["Actividad económica"] + sorted([c for c in pivot.columns if c != "Actividad económica"])]
        csv_path = os.path.join(regional_folder, f"{code}_Regional.csv")
        pivot.to_csv(csv_path, index=False)

    print("✅ All CSVs now include a single total row and alphabetically sorted headers.")

if __name__ == "__main__":
    main()
