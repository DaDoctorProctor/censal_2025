import os
import re
import math
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, Border, Side
from openpyxl.utils import get_column_letter

# -----------------------
# Config
# -----------------------
INPUT_CSV = "input/SAIC_Exporta_2025919_1928329.csv"
OUTPUT_DIR = "output"
YEARS = [2008, 2013, 2018, 2023]
NUMERIC_COL_WIDTH = 14  # Fixed width for numeric columns
FIRST_COL_WIDTH = 50    # Width for 'Actividad económica'

# ---------- Helpers ----------
def center_numeric_columns_and_bold_total(filename, sheet_name):
    wb = load_workbook(filename)
    ws = wb[sheet_name]
    max_row = ws.max_row
    max_col = ws.max_column

    # Center numeric columns B onward, from row 2
    for row in ws.iter_rows(min_row=2, max_row=max_row, min_col=2, max_col=max_col):
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Bold last row (Total)
    for cell in ws[max_row]:
        cell.font = Font(bold=True)

    wb.save(filename)

def sanitize_filename(name):
    s = re.sub(r'[^\w\s-]', '', name)
    s = re.sub(r'\s+', '_', s.strip())
    return s

def clean_actividad_economica(df, col="Actividad económica"):
    df[col] = df[col].apply(lambda x: re.sub(r'Sector\s*\d+(-\d+)?\s*', '', str(x)))
    return df

def add_total_row(df, first_col="Actividad económica"):
    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) == 0:
        return df
    total = df[numeric_cols].sum()
    total[first_col] = "Total"
    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)

def format_numbers_with_two_decimals_and_commas(filename):
    wb = load_workbook(filename)
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=2, max_col=ws.max_column):
            for cell in row:
                cell.number_format = '#,##0.00'
    wb.save(filename)

def wrap_text_first_column(filename, sheet_name):
    wb = load_workbook(filename)
    ws = wb[sheet_name]
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=1):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(filename)

def set_column_widths(filename, sheet_name, first_col_width=50, numeric_col_width=20):
    wb = load_workbook(filename)
    ws = wb[sheet_name]
    ws.column_dimensions[get_column_letter(1)].width = first_col_width
    for col in range(2, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col)].width = numeric_col_width
    wb.save(filename)

def adjust_first_column_and_autofit_rows(filename, sheet_name, line_height=15):
    """Adjust row heights based on wrapped text in first column."""
    wb = load_workbook(filename)
    ws = wb[sheet_name]
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        max_lines = 1
        for cell in row:
            if cell.value:
                col_letter = get_column_letter(cell.column)
                col_width = ws.column_dimensions[col_letter].width or 10
                lines = math.ceil(len(str(cell.value)) / max(col_width, 1))
                max_lines = max(max_lines, lines)
        ws.row_dimensions[row[0].row].height = max_lines * line_height
    wb.save(filename)

def add_two_row_header(filename, sheet_name, var_names, years):
    wb = load_workbook(filename)
    ws = wb[sheet_name]
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                         top=Side(style='thin'), bottom=Side(style='thin'))

    ws.insert_rows(1)
    col_start = 2
    for var in var_names:
        ws.merge_cells(start_row=1, start_column=col_start, end_row=1, end_column=col_start + len(years) - 1)
        cell = ws.cell(row=1, column=col_start, value=var)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        for i, year in enumerate(years):
            y_cell = ws.cell(row=2, column=col_start + i, value=year)
            y_cell.font = Font(bold=True)
            y_cell.alignment = Alignment(horizontal="center", vertical="center")
            y_cell.border = thin_border
        col_start += len(years)

    ws.cell(row=2, column=1, value="Actividad económica")
    ws.cell(row=2, column=1).font = Font(bold=True)
    ws.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(row=2, column=1).border = thin_border

    # Apply borders to all cells
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin_border

    wb.save(filename)

# ---------- Main ----------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(INPUT_CSV)
    df.columns = [c.strip() for c in df.columns]

    var_cols = df.columns[3:]

    for ent in df["Entidad"].unique():
        df_ent = df[df["Entidad"] == ent].copy()
        df_ent = clean_actividad_economica(df_ent, col="Actividad económica")
        output_file = os.path.join(OUTPUT_DIR, sanitize_filename(ent) + ".xlsx")

        # ---------- Create Main Table ----------
        main_table = pd.DataFrame({"Actividad económica": df_ent["Actividad económica"].unique()})
        main_table.set_index("Actividad económica", inplace=True)

        for var in var_cols:
            for year in YEARS:
                val = df_ent[df_ent["Año Censal"] == year][["Actividad económica", var]].set_index("Actividad económica")
                val = val.reindex(main_table.index).fillna(0)
                col_name = f"{var}_{year}"
                main_table[col_name] = val[var]

        main_table.reset_index(inplace=True)
        main_table = add_total_row(main_table, first_col="Actividad económica")

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            # Main table
            main_table.to_excel(writer, sheet_name="Main Table", index=False)

            # Individual variable tabs
            for var in var_cols:
                var_table = pd.DataFrame({"Actividad económica": df_ent["Actividad económica"].unique()})
                var_table.set_index("Actividad económica", inplace=True)
                for year in YEARS:
                    val = df_ent[df_ent["Año Censal"] == year][["Actividad económica", var]].set_index("Actividad económica")
                    val = val.reindex(var_table.index).fillna(0)
                    var_table[year] = val[var]
                var_table.reset_index(inplace=True)
                var_table = add_total_row(var_table, first_col="Actividad económica")
                code = var.split()[0]
                var_table.to_excel(writer, sheet_name=code, index=False)

        # ---------- Formatting ----------
        # Main Table
        add_two_row_header(output_file, "Main Table", var_cols, YEARS)
        wrap_text_first_column(output_file, "Main Table")
        set_column_widths(output_file, "Main Table", first_col_width=FIRST_COL_WIDTH, numeric_col_width=NUMERIC_COL_WIDTH)
        adjust_first_column_and_autofit_rows(output_file, "Main Table")

        # Individual variable tabs
        for var in var_cols:
            code = var.split()[0]
            add_two_row_header(output_file, code, [var], YEARS)
            wrap_text_first_column(output_file, code)
            set_column_widths(output_file, code, first_col_width=FIRST_COL_WIDTH, numeric_col_width=NUMERIC_COL_WIDTH)
            adjust_first_column_and_autofit_rows(output_file, code)

        # Number formatting
        format_numbers_with_two_decimals_and_commas(output_file)

        # ---------- Center numeric columns and bold Total ----------
        wb = load_workbook(output_file)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            max_row = ws.max_row
            max_col = ws.max_column

            # Center numeric columns B onward from row 2
            for row in ws.iter_rows(min_row=2, max_row=max_row, min_col=2, max_col=max_col):
                for cell in row:
                    cell.alignment = Alignment(horizontal="center", vertical="center")

            # Bold last row (Total)
            for cell in ws[max_row]:
                cell.font = Font(bold=True)

        wb.save(output_file)

        print(f"Saved Excel for Entidad: {ent} -> {output_file}")

    print("✅ Finished all Entidades with fixed widths, borders, two decimals, centered numeric columns, and bold Total row.")


if __name__ == "__main__":
    main()
