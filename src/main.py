from __future__ import annotations

import os
from pathlib import Path
import pandas as pd


def _append_checksum_row(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Append a checksum row at the bottom that sums only 'Sector ' rows per column.

    - Assumes first column is 'Actividad Economica'.
    - For every other column, sums only rows whose 'Actividad Economica' starts with 'Sector '.
    - Supports cells formatted as plain numbers (float/int) or annotated strings like "123.45 + n" or "123.45 + 3n".
      The checksum cell becomes "sum + kn" when k > 0, with base rounded to 3 decimals (trailing zeros trimmed).
    - Returns a new DataFrame with the checksum row appended at the end.
    """
    if wide_df.empty or 'Actividad Economica' not in wide_df.columns:
        return wide_df

    def parse_val(x):
        """Parse a value that may be numeric or a string like '123.45 + n' or '123.45 + 2n'.
        Returns (base_float, k_int, had_value: bool).
        """
        if pd.isna(x):
            return 0.0, 0, False
        # If already numeric
        try:
            if isinstance(x, (int, float)):
                # Exclude pandas Int64/NA scalars handled by pd.isna above
                return float(x), 0, True
        except Exception:
            pass
        s = str(x).strip()
        if s == '' or s.lower() == 'nan':
            return 0.0, 0, False
        # Try direct numeric
        try:
            return float(s), 0, True
        except Exception:
            pass
        base = 0.0
        k = 0
        had = False
        # Expect forms like "<num> + n" or "<num> + 2n"; be tolerant about spaces
        if '+' in s:
            parts = s.split('+', 1)
            base_str = parts[0].strip()
            rest = parts[1].strip().replace(' ', '')
            try:
                base = float(base_str)
                had = True
            except Exception:
                # If base not parseable, ignore entire cell
                return 0.0, 0, False
            if rest.endswith('n'):
                coef_str = rest[:-1]
                if coef_str == '' or coef_str == '+':
                    k = 1
                else:
                    try:
                        k = int(coef_str)
                    except Exception:
                        # If cannot parse coef, assume 1 when pattern had 'n'
                        k = 1
            else:
                # No 'n' annotation found after '+'; ignore annotation
                k = 0
            return base, k, had
        # If string contains 'n' without '+', try to extract base before ' ' and coefficient
        if 'n' in s:
            # Try something like '123n' (unlikely in our data)
            t = s.replace(' ', '')
            if t.endswith('n'):
                coef_str = t[:-1]
                try:
                    k = int(coef_str)
                    return 0.0, k, True
                except Exception:
                    return 0.0, 0, False
        # Fallback: unrecognized string
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
                    new_row[col] = f"{base_str} + n"
                else:
                    new_row[col] = f"{base_str} + {k_sum}n"

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

        # Special case: 041 Victoria - apply C vs N/A marking to all sector rows
        # For each sector row and year:
        # - If the activity exists for that year (present in SAIC_clean) but value is null -> mark "C".
        # - If the activity does not exist for that year -> mark "N/A".
        if str(mun) == '041 Victoria':
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
    in_path = base_dir / 'input' / 'dataset' / 'SAIC_clean.csv'
    out_dir = base_dir / 'output' / 'ready_csv' / '28_Tam_Regional'

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

    # Read input
    df = pd.read_csv(in_path)

    # Determine activity column name
    if 'Actividad económica' in df.columns:
        activity_col = 'Actividad económica'
    else:
        activity_col = 'Actividad Economica' if 'Actividad Economica' in df.columns else df.columns[3]

    # Identify metric columns
    id_cols = ['Año Censal', 'Entidad', 'Municipio', activity_col]
    metric_cols = [c for c in df.columns if c not in id_cols]

    outputs = []
    os.makedirs(out_dir, exist_ok=True)

    for region, municipios in regions_map.items():
        # Filter rows for the region: Tamaulipas + municipios in list
        mask = (df['Entidad'] == '28 Tamaulipas') & (df['Municipio'].isin(municipios))
        df_reg = df.loc[mask, ['Año Censal', activity_col] + metric_cols].copy()

        if df_reg.empty:
            # Still create an empty file with just header? We'll skip but note.
            continue

        # Aggregate across municipios by year and activity, preserving NaNs when all values are NaN
        grp = df_reg.groupby(['Año Censal', activity_col], dropna=False)
        try:
            sum_df = grp[metric_cols].sum(min_count=1)
        except TypeError:
            # Fallback: emulate min_count=1
            sum_df = grp[metric_cols].sum()
            counts_nonnull = grp[metric_cols].count()
            sum_df = sum_df.where(counts_nonnull > 0)
        # Non-null counts per metric
        counts_nonnull = grp[metric_cols].count()
        # Rows per group
        group_sizes = grp.size()
        # Null counts per metric = group size - non-null counts
        null_counts = counts_nonnull.copy()
        for col in metric_cols:
            null_counts[col] = group_sizes - counts_nonnull[col]
        # Reset index for melt
        sum_df = sum_df.reset_index()
        null_counts = null_counts.reset_index()

        # Melt to long for sums
        long_sum = sum_df.melt(
            id_vars=['Año Censal', activity_col],
            value_vars=metric_cols,
            var_name='Variable',
            value_name='Valor'
        )
        # Melt to long for null counts
        long_nulls = null_counts.melt(
            id_vars=['Año Censal', activity_col],
            value_vars=metric_cols,
            var_name='Variable',
            value_name='Nulls'
        )
        # Merge
        long = pd.merge(long_sum, long_nulls, on=['Año Censal', activity_col, 'Variable'], how='left')

        # Build display value that appends "+ n" when sum involved nulls (but keep NaN if all inputs were NaN)
        def format_with_n(row):
            val = row['Valor']
            n = row['Nulls']
            # If all inputs were NaN, Valor is NaN; leave as NaN
            if pd.isna(val):
                return pd.NA

            # Helper to format with up to 3 decimals
            def fmt3(x):
                try:
                    s = f"{float(x):.3f}"
                    # Trim trailing zeros and dot
                    if '.' in s:
                        s = s.rstrip('0').rstrip('.')
                    return s
                except Exception:
                    return str(x)

            # Determine null coefficient
            try:
                coef = 0 if pd.isna(n) else int(n)
            except Exception:
                coef = 0

            base = fmt3(val)
            if coef <= 0:
                # Return formatted number (as string) to ensure 3-decimal limit
                return base
            # Append + n or + 2n, + 3n, etc.
            if coef == 1:
                return f"{base} + n"
            else:
                return f"{base} + {coef}n"

        long['Display'] = long.apply(format_with_n, axis=1)

        # Build Code_Year
        long['Code'] = long['Variable'].map(lambda v: str(v).split(' ')[0] if ' ' in str(v) else str(v))
        long['Year'] = pd.to_numeric(long['Año Censal'], errors='coerce').astype('Int64').astype(str)
        long['ColName'] = long['Code'] + '_' + long['Year']

        # Pivot to wide; use Display as values to include annotation. Preserve NaNs
        wide = long.pivot(index=activity_col, columns='ColName', values='Display')

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

        first_col = ['Actividad Economica']
        other_cols = [c for c in wide.columns if c != 'Actividad Economica']
        wide = wide[first_col + other_cols]

        # Prepare regional total row based on the aggregated 'Total municipal' (sum of municipalities in region)
        total_label = 'Total municipal'
        new_total_label = f'Total {region}'
        total_row_df = wide[wide['Actividad Economica'] == total_label].copy()
        if not total_row_df.empty:
            total_row_df.loc[:, 'Actividad Economica'] = new_total_label

        # Remove any rows that start with 'Total ' (like 'Total municipal' or pre-existing totals) EXCEPT the new regional total label
        wide = wide[~(wide['Actividad Economica'].astype(str).str.startswith('Total ') & (wide['Actividad Economica'] != new_total_label))]

        # Ensure the new regional total row is present and placed just above checksum (i.e., at the bottom before checksum is appended)
        if not total_row_df.empty:
            # Remove any duplicates of the label just in case, then append one instance at the bottom
            wide = wide[wide['Actividad Economica'] != new_total_label]
            wide = pd.concat([wide, total_row_df], ignore_index=True)

        # Append checksum row of sector sums at the bottom
        wide = _append_checksum_row(wide)

        # Write file
        out_path = out_dir / f'{region}.csv'
        # Limit floats to 3 decimals in output (for any float cells)
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
