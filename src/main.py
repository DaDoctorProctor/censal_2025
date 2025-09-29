from __future__ import annotations

import os
from pathlib import Path
import pandas as pd


def _append_checksum_row(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Append a checksum row at the bottom that sums only 'Sector ' rows per column.

    - Assumes first column is 'Actividad Economica'.
    - For every other column, sums only rows whose 'Actividad Economica' starts with 'Sector '.
    - Supports cells formatted as plain numbers (float/int) or annotated strings like "123.45 + C" or "123.45 + 3C"
      (and remains backward-compatible with old forms like "+ n").
      The checksum cell becomes "sum + kC" when k > 0, with base rounded to 3 decimals (trailing zeros trimmed).
    - Returns a new DataFrame with the checksum row appended at the end.
    """
    if wide_df.empty or 'Actividad Economica' not in wide_df.columns:
        return wide_df

    def parse_val(x):
        """Parse a value that may be numeric or a string like '123.45 + C' or '123.45 + 2C'.
        Also supports legacy 'n' annotations. Returns (base_float, k_int, had_value: bool).
        """
        if pd.isna(x):
            return 0.0, 0, False
        # If already numeric
        try:
            if isinstance(x, (int, float)):
                return float(x), 0, True
        except Exception:
            pass
        s = str(x).strip()
        if s == '' or s.lower() == 'nan':
            return 0.0, 0, False
        # Normalize common tokens
        s_norm = s.replace('c', 'C')
        # Treat plain C as 1 censored observation contributing zero to base
        if s_norm == 'C':
            return 0.0, 1, True
        if s_norm.upper() == 'N/A':
            return 0.0, 0, True
        # Try direct numeric
        try:
            return float(s_norm), 0, True
        except Exception:
            pass
        base = 0.0
        k = 0
        had = False
        # Expect forms like "<num> + C", "<num> + 2C", and legacy "<num> + n", "<num> + 2n"
        if '+' in s_norm:
            parts = s_norm.split('+', 1)
            base_str = parts[0].strip()
            rest = parts[1].strip().replace(' ', '')
            try:
                base = float(base_str)
                had = True
            except Exception:
                return 0.0, 0, False
            if rest.endswith('C'):
                coef_str = rest[:-1]
                k = 1 if coef_str == '' else (int(coef_str) if coef_str.isdigit() else 1)
            elif rest.endswith('n'):
                coef_str = rest[:-1]
                k = 1 if coef_str == '' else (int(coef_str) if coef_str.isdigit() else 1)
            else:
                k = 0
            return base, k, had
        # Handle forms like '2C' or '2n'
        t = s_norm.replace(' ', '')
        if t.endswith('C'):
            coef_str = t[:-1]
            if coef_str.isdigit():
                return 0.0, int(coef_str), True
            return 0.0, 1, True
        if t.endswith('n'):
            coef_str = t[:-1]
            if coef_str.isdigit():
                return 0.0, int(coef_str), True
            return 0.0, 1, True
        # Fallback: unrecognized string contributes nothing
        return 0.0, 0, False

    def fmt3(x: float) -> str:
        try:
            s = f"{float(x):.3f}"
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        except Exception:
            return str(x)

    mask_sector = wide_df['Actividad Economica'].astype(str).str.startswith('Sector ')

    new_row = {'Actividad Economica': 'checksum'}
    for col in wide_df.columns:
        if col == 'Actividad Economica':
            continue
        base_sum = 0.0
        k_sum = 0
        had_any = False
        col_vals = wide_df.loc[mask_sector, col]
        for v in col_vals:
            b, k, had = parse_val(v)
            if had:
                had_any = True
                base_sum += 0.0 if pd.isna(b) else float(b)
                try:
                    k_sum += int(k)
                except Exception:
                    pass
        if not had_any:
            new_row[col] = pd.NA
        else:
            base_str = fmt3(base_sum)
            if k_sum <= 0:
                new_row[col] = base_str
            else:
                if k_sum == 1:
                    new_row[col] = f"{base_str} + C"
                else:
                    new_row[col] = f"{base_str} + {k_sum}C"

    return pd.concat([wide_df, pd.DataFrame([new_row])], ignore_index=True)


def build_national_wide_csv():
    # Resolve paths relative to this file (src directory)
    base_dir = Path(__file__).parent
    in_path = base_dir / 'input' / 'dataset' / 'SAIC_clean.csv'
    out_dir = base_dir / 'output' / 'ready_csv' / '00_Total_Nacional'
    out_path = out_dir / '00_Total_Nacional.csv'

    # Read input
    df = pd.read_csv(in_path)

    # Filter national rows only
    df_nat = df[df['Entidad'] == '00 Total Nacional'].copy()

    # Standardize activity name for the total row as requested
    if 'Actividad económica' in df_nat.columns:
        activity_col = 'Actividad económica'
    else:
        # Fallback in case of different naming
        # Try without accent just in case
        activity_col = 'Actividad Economica' if 'Actividad Economica' in df_nat.columns else df_nat.columns[3]

    df_nat[activity_col] = df_nat[activity_col].replace({'Total nacional': 'Total Nacional'})

    # Identify metric columns (all except these identifiers)
    id_cols = ['Año Censal', 'Entidad', 'Municipio', activity_col]
    metric_cols = [c for c in df_nat.columns if c not in id_cols]

    # Melt to long format
    long = df_nat.melt(
        id_vars=['Año Censal', activity_col],
        value_vars=metric_cols,
        var_name='Variable',
        value_name='Valor'
    )

    # Extract code and year to build the target column names Code_YYYY
    long['Code'] = long['Variable'].map(lambda v: str(v).split(' ')[0] if ' ' in str(v) else str(v))
    # Ensure year is integer-like string
    long['Year'] = pd.to_numeric(long['Año Censal'], errors='coerce').astype('Int64').astype(str)
    long['ColName'] = long['Code'] + '_' + long['Year']

    # Pivot to wide; preserve NaNs (no fill)
    wide = long.pivot(index=activity_col, columns='ColName', values='Valor')

    # Order columns: by code then by year asc
    def sort_key(col: str):
        try:
            code, year = col.split('_', 1)
            return (code, int(year))
        except Exception:
            return (col, 0)

    ordered_cols = sorted(wide.columns, key=sort_key)
    wide = wide.reindex(columns=ordered_cols)

    # Move total row to bottom and ensure its label is exactly "Total Nacional"
    wide = wide.reset_index()
    wide.rename(columns={activity_col: 'Actividad Economica'}, inplace=True)

    # Ensure the first column order is maintained
    first_col = ['Actividad Economica']
    other_cols = [c for c in wide.columns if c != 'Actividad Economica']
    wide = wide[first_col + other_cols]

    # Reorder rows to put Total Nacional last
    if 'Total Nacional' in wide['Actividad Economica'].values:
        is_total = wide['Actividad Economica'] == 'Total Nacional'
        wide = pd.concat([wide[~is_total], wide[is_total]], ignore_index=True)

    # Append checksum row of sector sums at the bottom
    wide = _append_checksum_row(wide)

    # Create output directory and write CSV
    os.makedirs(out_dir, exist_ok=True)
    # Limit floats to 3 decimals in output
    wide.to_csv(out_path, index=False, float_format='%.3f')

    return out_path


def build_tamaulipas_wide_csv():
    # Resolve paths relative to this file (src directory)
    base_dir = Path(__file__).parent
    in_path = base_dir / 'input' / 'dataset' / 'SAIC_clean.csv'
    out_dir = base_dir / 'output' / 'ready_csv' / '28_Tamaulipas'
    out_path = out_dir / '28_Tamaulipas.csv'

    # Read input
    df = pd.read_csv(in_path)

    # Filter state rows only: Entidad == '28 Tamaulipas' and Municipio is null (NaN)
    df_sta = df[(df['Entidad'] == '28 Tamaulipas') & (df['Municipio'].isna())].copy()

    # Determine activity column name
    if 'Actividad económica' in df_sta.columns:
        activity_col = 'Actividad económica'
    else:
        activity_col = 'Actividad Economica' if 'Actividad Economica' in df_sta.columns else df_sta.columns[3]

    # Optional: standardize total row label for clarity
    df_sta[activity_col] = df_sta[activity_col].replace({'Total estatal': 'Total Tamaulipas'})

    # Identify metric columns
    id_cols = ['Año Censal', 'Entidad', 'Municipio', activity_col]
    metric_cols = [c for c in df_sta.columns if c not in id_cols]

    # Melt to long
    long = df_sta.melt(
        id_vars=['Año Censal', activity_col],
        value_vars=metric_cols,
        var_name='Variable',
        value_name='Valor'
    )

    # Build Code_Year
    long['Code'] = long['Variable'].map(lambda v: str(v).split(' ')[0] if ' ' in str(v) else str(v))
    long['Year'] = pd.to_numeric(long['Año Censal'], errors='coerce').astype('Int64').astype(str)
    long['ColName'] = long['Code'] + '_' + long['Year']

    # Pivot to wide; preserve NaNs
    wide = long.pivot(index=activity_col, columns='ColName', values='Valor')

    # Order columns by code then year asc
    def sort_key(col: str):
        try:
            code, year = col.split('_', 1)
            return (code, int(year))
        except Exception:
            return (col, 0)

    ordered_cols = sorted(wide.columns, key=sort_key)
    wide = wide.reindex(columns=ordered_cols)

    # Finalize columns and move total to bottom
    wide = wide.reset_index()
    wide.rename(columns={activity_col: 'Actividad Economica'}, inplace=True)

    first_col = ['Actividad Economica']
    other_cols = [c for c in wide.columns if c != 'Actividad Economica']
    wide = wide[first_col + other_cols]

    # Reorder rows to put the Total row last if present
    for total_label in ['Total Tamaulipas', 'Total estatal']:
        if total_label in wide['Actividad Economica'].values:
            is_total = wide['Actividad Economica'] == total_label
            wide = pd.concat([wide[~is_total], wide[is_total]], ignore_index=True)
            break

    # Append checksum row of sector sums at the bottom
    wide = _append_checksum_row(wide)

    # Create output directory and write CSV
    os.makedirs(out_dir, exist_ok=True)
    # Limit floats to 3 decimals in output
    wide.to_csv(out_path, index=False, float_format='%.3f')

    return out_path


def build_tam_municipal_wide_csvs():
    # Resolve paths relative to this file (src directory)
    base_dir = Path(__file__).parent
    in_path = base_dir / 'input' / 'dataset' / 'SAIC_clean.csv'
    out_dir = base_dir / 'output' / 'ready_csv' / '28_Tam_Mun'

    # Read input
    df = pd.read_csv(in_path)

    # Determine activity column name
    if 'Actividad económica' in df.columns:
        activity_col = 'Actividad económica'
    else:
        activity_col = 'Actividad Economica' if 'Actividad Economica' in df.columns else df.columns[3]

    # Filter Tamaulipas municipal rows only (exclude Municipio nulls)
    df_mun = df[(df['Entidad'] == '28 Tamaulipas') & (~df['Municipio'].isna())].copy()

    # Identify metric columns
    id_cols = ['Año Censal', 'Entidad', 'Municipio', activity_col]
    metric_cols = [c for c in df.columns if c not in id_cols]

    # Unique municipios
    municipios = sorted(df_mun['Municipio'].dropna().unique())

    outputs = []
    os.makedirs(out_dir, exist_ok=True)

    for mun in municipios:
        df_one = df_mun[df_mun['Municipio'] == mun].copy()
        if df_one.empty:
            continue

        # Melt to long
        long = df_one.melt(
            id_vars=['Año Censal', activity_col],
            value_vars=metric_cols,
            var_name='Variable',
            value_name='Valor'
        )

        # Build Code_Year
        long['Code'] = long['Variable'].map(lambda v: str(v).split(' ')[0] if ' ' in str(v) else str(v))
        long['Year'] = pd.to_numeric(long['Año Censal'], errors='coerce').astype('Int64').astype(str)
        long['ColName'] = long['Code'] + '_' + long['Year']

        # Pivot to wide; preserve NaNs
        wide = long.pivot(index=activity_col, columns='ColName', values='Valor')

        # Order columns by code then year asc
        def sort_key(col: str):
            try:
                code, year = col.split('_', 1)
                return (code, int(year))
            except Exception:
                return (col, 0)

        ordered_cols = sorted(wide.columns, key=sort_key)
        wide = wide.reindex(columns=ordered_cols)

        # Finalize columns
        wide = wide.reset_index()
        wide.rename(columns={activity_col: 'Actividad Economica'}, inplace=True)

        # Apply C vs N/A marking to all municipios, following the logic initially used for '041 Victoria'.
        # For each sector row and year:
        # - If the activity exists for that year (present in SAIC_clean) but value is null -> mark "C".
        # - If the activity does not exist for that year -> mark "N/A".
        years = [2003, 2008, 2013, 2018, 2023]
        sector_mask = wide['Actividad Economica'].astype(str).str.startswith('Sector ')
        for idx in wide.index[sector_mask]:
            act_label = str(wide.at[idx, 'Actividad Economica'])
            for y in years:
                year_cols = [c for c in wide.columns if c != 'Actividad Economica' and str(c).endswith(f'_{y}')]
                exists_row = not df_one[
                    (df_one['Año Censal'] == y) &
                    (df_one[activity_col].astype(str) == act_label)
                ].empty
                for col in year_cols:
                    if col in wide.columns:
                        val = wide.at[idx, col]
                        if pd.isna(val):
                            wide.at[idx, col] = 'C' if exists_row else 'N/A'

        # Rename total label similar to state file and move to bottom
        total_label = f'Total {mun}'
        wide['Actividad Economica'] = wide['Actividad Economica'].replace({'Total municipal': total_label})

        first_col = ['Actividad Economica']
        other_cols = [c for c in wide.columns if c != 'Actividad Economica']
        wide = wide[first_col + other_cols]

        # Put total row (renamed or original) last if present
        if total_label in wide['Actividad Economica'].values:
            is_total = wide['Actividad Economica'] == total_label
            wide = pd.concat([wide[~is_total], wide[is_total]], ignore_index=True)
        elif 'Total municipal' in wide['Actividad Economica'].values:
            is_total = wide['Actividad Economica'] == 'Total municipal'
            wide = pd.concat([wide[~is_total], wide[is_total]], ignore_index=True)

        # Append checksum row of sector sums at the bottom
        wide = _append_checksum_row(wide)

        # Safe file name from municipio value
        safe_name = str(mun).replace('/', '-')
        out_path = out_dir / f'{safe_name}.csv'
        # Limit floats to 3 decimals in output
        wide.to_csv(out_path, index=False, float_format='%.3f')
        outputs.append(out_path)

    return outputs



def build_tam_regional_wide_csvs():
    # Resolve paths relative to this file (src directory)
    base_dir = Path(__file__).parent
    mun_dir = base_dir / 'output' / 'ready_csv' / '28_Tam_Mun'
    out_dir = base_dir / 'output' / 'ready_csv' / '28_Tam_Regional'
    # Load original dataset to source regional Total rows directly
    saic_path = base_dir / 'input' / 'dataset' / 'SAIC_clean.csv'
    try:
        df_saic = pd.read_csv(saic_path)
    except Exception:
        df_saic = None

    # Regions map as specified
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

    def fmt3(x: float) -> str:
        try:
            s = f"{float(x):.3f}"
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        except Exception:
            return str(x)

    def parse_cell(x):
        # Returns (base_float, c_count_int)
        if pd.isna(x):
            return 0.0, 0
        s = x
        # Convert to string unless numeric
        if isinstance(x, (int, float)):
            try:
                return float(x), 0
            except Exception:
                return 0.0, 0
        s = str(x).strip()
        if s == '' or s.lower() == 'nan':
            return 0.0, 0
        s_norm = s.replace('c', 'C')
        if s_norm.upper() == 'N/A':
            return 0.0, 0
        if s_norm == 'C':
            return 0.0, 1
        # Try direct numeric
        try:
            return float(s_norm), 0
        except Exception:
            pass
        # Pattern like "<num> + C" / "+ 2C" / legacy n
        if '+' in s_norm:
            parts = s_norm.split('+', 1)
            base_str = parts[0].strip()
            rest = parts[1].strip().replace(' ', '')
            try:
                base = float(base_str)
            except Exception:
                base = 0.0
            if rest.endswith('C'):
                coef_str = rest[:-1]
                c = 1 if coef_str == '' else (int(coef_str) if coef_str.isdigit() else 1)
                return base, c
            if rest.endswith('n'):
                coef_str = rest[:-1]
                c = 1 if coef_str == '' else (int(coef_str) if coef_str.isdigit() else 1)
                return base, c
            # Unknown annotation, ignore
            return base, 0
        # Pattern like '2C' or '2n'
        t = s_norm.replace(' ', '')
        if t.endswith('C') and t[:-1].isdigit():
            return 0.0, int(t[:-1])
        if t.endswith('n') and t[:-1].isdigit():
            return 0.0, int(t[:-1])
        return 0.0, 0

    def format_sum(base_sum: float, c_sum: int) -> str:
        base_str = fmt3(base_sum)
        if c_sum <= 0:
            return base_str
        if c_sum == 1:
            return f"{base_str} + C"
        return f"{base_str} + {c_sum}C"

    outputs = []
    os.makedirs(out_dir, exist_ok=True)

    for region, municipios in regions_map.items():
        # Load municipal CSVs for the region
        muni_dfs = []
        for mun in municipios:
            path = mun_dir / f"{mun}.csv"
            if not path.exists():
                continue
            try:
                dfm = pd.read_csv(path)
                muni_dfs.append(dfm)
            except Exception:
                continue
        if not muni_dfs:
            # Nothing to aggregate for this region
            continue

        # Use the first file as template for column order
        template = muni_dfs[0]
        if 'Actividad Economica' not in template.columns:
            # Try alternative label
            if 'Actividad económica' in template.columns:
                template = template.rename(columns={'Actividad económica': 'Actividad Economica'})
                for i in range(1, len(muni_dfs)):
                    if 'Actividad económica' in muni_dfs[i].columns:
                        muni_dfs[i] = muni_dfs[i].rename(columns={'Actividad económica': 'Actividad Economica'})
            else:
                # Cannot proceed without activity column
                continue

        # Normalize all dfs to have the same columns as union of columns
        all_cols = set(template.columns)
        for dfm in muni_dfs[1:]:
            all_cols.update(dfm.columns)
        # Ensure string order: keep 'Actividad Economica' first, then others sorted for stability
        other_cols = sorted([c for c in all_cols if c != 'Actividad Economica'])
        cols_order = ['Actividad Economica'] + other_cols
        norm_dfs = []
        for dfm in muni_dfs:
            # Rename activity column if needed
            if 'Actividad Economica' not in dfm.columns and 'Actividad económica' in dfm.columns:
                dfm = dfm.rename(columns={'Actividad económica': 'Actividad Economica'})
            # Add missing columns as N/A
            for c in cols_order:
                if c not in dfm.columns:
                    dfm[c] = pd.NA
            dfm = dfm[cols_order]
            norm_dfs.append(dfm)

        # Determine activities to aggregate: rows starting with 'Sector '
        activities = (
            norm_dfs[0]['Actividad Economica']
            .astype(str)
            .tolist()
        )
        activities = [a for a in activities if str(a).startswith('Sector ')]

        # Aggregate per activity
        rows = []
        for act in activities:
            row = {'Actividad Economica': act}
            for col in other_cols:
                base_sum = 0.0
                c_sum = 0
                for dfm in norm_dfs:
                    # find row for this activity
                    match = dfm['Actividad Economica'] == act
                    if not match.any():
                        v = pd.NA
                    else:
                        v = dfm.loc[match, col].values
                        v = v[0] if len(v) > 0 else pd.NA
                    b, c = parse_cell(v)
                    base_sum += b
                    c_sum += c
                row[col] = format_sum(base_sum, c_sum)
            rows.append(row)

        wide = pd.DataFrame(rows)

        # Create regional Total row sourced directly from SAIC_clean.csv (sum of 'Total municipal' over municipios in region)
        total_row = {'Actividad Economica': f'Total {region}'}
        inserted_direct_total = False
        if df_saic is not None:
            try:
                df_tot = df_saic[
                    (df_saic.get('Entidad') == '28 Tamaulipas') &
                    (df_saic.get('Municipio').isin(municipios)) &
                    (df_saic.get('Actividad económica') == 'Total municipal')
                ].copy()
                if df_tot is not None and not df_tot.empty:
                    metric_cols_saic = [
                        c for c in df_tot.columns
                        if c not in ['Año Censal', 'Entidad', 'Municipio', 'Actividad económica']
                    ]
                    grp = df_tot.groupby('Año Censal', dropna=False)
                    try:
                        sum_df = grp[metric_cols_saic].sum(min_count=1)
                    except TypeError:
                        sum_df = grp[metric_cols_saic].sum()
                        counts_nonnull = grp[metric_cols_saic].count()
                        sum_df = sum_df.where(counts_nonnull > 0)
                    sum_df = sum_df.reset_index()
                    long = sum_df.melt(
                        id_vars=['Año Censal'],
                        value_vars=metric_cols_saic,
                        var_name='Variable',
                        value_name='Valor'
                    )
                    # Extract code before first space and build Code_Year column names
                    long['Code'] = long['Variable'].map(lambda v: str(v).split(' ')[0])
                    long['Year'] = pd.to_numeric(long['Año Censal'], errors='coerce').astype('Int64').astype(str)
                    long['ColName'] = long['Code'] + '_' + long['Year']
                    # Map to wide
                    tot_map = {}
                    for _, r in long.iterrows():
                        coln = r['ColName']
                        val = r['Valor']
                        if pd.isna(val):
                            continue
                        tot_map[coln] = fmt3(val)
                    for col in other_cols:
                        total_row[col] = tot_map.get(col, pd.NA)
                    inserted_direct_total = True
            except Exception:
                inserted_direct_total = False
        if not inserted_direct_total:
            # Fallback: compute from current sector rows (as before)
            for col in other_cols:
                base_sum = 0.0
                c_sum = 0
                for v in wide[col].tolist():
                    b, c = parse_cell(v)
                    base_sum += b
                    c_sum += c
                total_row[col] = format_sum(base_sum, c_sum)
        wide = pd.concat([wide, pd.DataFrame([total_row])], ignore_index=True)

        # Append checksum row of sector sums at the bottom
        wide = _append_checksum_row(wide)

        # Write file
        out_path = out_dir / f'{region}.csv'
        wide.to_csv(out_path, index=False, float_format='%.3f')
        outputs.append(out_path)

    return outputs



if __name__ == '__main__':
    out_nat = build_national_wide_csv()
    print(f'Wrote national CSV to: {out_nat}')

    out_tam = build_tamaulipas_wide_csv()
    print(f'Wrote Tamaulipas CSV to: {out_tam}')

    out_muns = build_tam_municipal_wide_csvs()
    if out_muns:
        for p in out_muns:
            print(f'Wrote Municipal CSV to: {p}')
    else:
        print('No municipal CSVs were generated (no matching data).')

    out_regs = build_tam_regional_wide_csvs()
    if out_regs:
        for p in out_regs:
            print(f'Wrote Regional CSV to: {p}')
    else:
        print('No regional CSVs were generated (no matching data).')
