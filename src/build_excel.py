"""Live-formula workbooks.

excel/Industry_<name>.xlsx (one per industry)
- Tear sheet  the one-pager in cells; type any industry name in B2 and every figure updates (INDEX/MATCH)
- Data        Damodaran inputs for all 94 industries (blue) and every derived metric, rank, score and verdict (formulas)
excel/Industry_Database.xlsx: the same Data sheet with every industry, sorted by score.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

import model as Mo
from tear_sheet import slug

ROOT = Path(__file__).resolve().parents[1]
XL = ROOT / "excel"
ARIAL = "Arial"
F_IN = Font(name=ARIAL, color="0000FF", size=9)
F_CALC = Font(name=ARIAL, color="000000", size=9)
F_LINK = Font(name=ARIAL, color="008000", size=10)
F_B = Font(name=ARIAL, bold=True, size=10)
F_H = Font(name=ARIAL, bold=True, size=9, color="FFFFFF")
F_T = Font(name=ARIAL, bold=True, size=14)
F_S = Font(name=ARIAL, italic=True, size=9, color="555555")
FILL_H = PatternFill("solid", fgColor="1F3864")
FILL_KEY = PatternFill("solid", fgColor="FFF2CC")
PCT, X1, M0, N2 = "0.0%", '0.0"x"', '"$"#,##0', "0.00"

INPUTS = [("Industry", "industry", None), ("Financial (1 = yes)", "financial", "0"), ("Firms", "firms", "0"),
          ("Market cap ($m)", "market_cap", M0), ("Book equity ($m)", "book_equity", M0), ("EV ($m)", "ev", M0),
          ("Invested capital ($m)", "invested_capital", M0), ("Revenue ($m)", "revenue", M0),
          ("Gross profit ($m)", "gross_profit", M0), ("EBITDA ($m)", "ebitda", M0), ("EBIT ($m)", "ebit", M0),
          ("Net income ($m)", "net_income", M0), ("Beta", "beta", N2), ("Cost of equity", "cost_of_equity", PCT),
          ("Cost of capital", "cost_of_capital", PCT), ("Tax rate", "tax_rate", PCT),
          ("Revenue CAGR 5y", "rev_cagr_5y", PCT), ("Net income CAGR 5y", "ni_cagr_5y", PCT),
          ("Expected EPS growth 5y", "eps_growth_next5", PCT), ("Std dev of stock", "std_dev", PCT),
          ("Debt / capital", "debt_weight", PCT), ("Average age (years)", "age", "0.0")]
# column letters A..V for the inputs
C = {key: L(i + 1) for i, (_, key, _) in enumerate(INPUTS)}
R0, N = 5, 94
R1 = R0 + N - 1


def rng(col):
    return f"${col}${R0}:${col}${R1}"


DERIVED = [  # header, column, formula template (row r), format
    ("EV/EBITDA", "W", "=IF({J}{r}>0,{F}{r}/{J}{r},\"\")", X1),
    ("EV/Sales", "X", "=IF({H}{r}>0,{F}{r}/{H}{r},\"\")", X1),
    ("P/E", "Y", "=IF({L}{r}>0,{D}{r}/{L}{r},\"\")", X1),
    ("P/B", "Z", "=IF({E}{r}>0,{D}{r}/{E}{r},\"\")", X1),
    ("ROE", "AA", "=IF({E}{r}>0,{L}{r}/{E}{r},\"\")", PCT),
    ("ROIC (after tax)", "AB", "=IF({G}{r}>0,{K}{r}*(1-{P}{r})/{G}{r},\"\")", PCT),
    ("Return spread", "AC", "=IF({B}{r}=1,IF(AA{r}=\"\",\"\",AA{r}-{N}{r}),IF(AB{r}=\"\",\"\",AB{r}-{O}{r}))", PCT),
    ("EV/EBITDA, non-financials", "AD", "=IF({B}{r}=1,\"\",W{r})", X1),
    ("P/B, financials", "AE", "=IF({B}{r}=1,Z{r},\"\")", X1),
    ("Relative multiple", "AF", "=IF({B}{r}=1,IF(Z{r}=\"\",\"\",Z{r}/MEDIAN(" + rng("AE") + ")),IF(W{r}=\"\",\"\",W{r}/MEDIAN("
     + rng("AD") + ")))", N2),
    ("Rank: returns", "AG", "=IF(AC{r}=\"\",\"\",SUMPRODUCT(ISNUMBER(" + rng("AC") + ")*(" + rng("AC") + "<AC{r}))/(COUNT("
     + rng("AC") + ")-1))", "0.00"),
    ("Rank: growth", "AH", "=IF({Q}{r}=\"\",\"\",SUMPRODUCT(ISNUMBER(" + rng("Q") + ")*(" + rng("Q") + "<{Q}{r}))/(COUNT("
     + rng("Q") + ")-1))", "0.00"),
    ("Rank: value", "AI", "=IF(AF{r}=\"\",\"\",1-SUMPRODUCT(ISNUMBER(" + rng("AF") + ")*(" + rng("AF") + "<AF{r}))/(COUNT("
     + rng("AF") + ")-1))", "0.00"),
    ("Rank: risk", "AJ", "=IF({M}{r}=\"\",\"\",1-SUMPRODUCT(ISNUMBER(" + rng("M") + ")*(" + rng("M") + "<{M}{r}))/(COUNT("
     + rng("M") + ")-1))", "0.00"),
    ("Score (0-100)", "AK", "=IF(COUNT(AG{r}:AJ{r})=0,\"\",100*AVERAGE(AG{r}:AJ{r}))", "0.0"),
    ("Verdict", "AL", "=IF(OR(AC{r}=\"\",AF{r}=\"\"),\"Not enough data\",IF(AC{r}>0,IF(AF{r}<1,\"Quality at a discount\","
     "\"Quality, priced for it\"),IF(AF{r}<1,\"Cheap for a reason\",\"Expensive without returns\")))", None),
    ("Share of market cap", "AM", "={D}{r}/$D$2", PCT),
]


def data_sheet(ws, inds, total_mc):
    ws["A1"] = "Damodaran US industry data, January 2026: inputs (blue) and derived metrics (formulas)"
    ws["A1"].font = F_T
    ws["A2"] = "Total US market cap ($m)"
    ws["A2"].font = F_B
    ws["D2"] = total_mc
    ws["D2"].font, ws["D2"].number_format = F_IN, M0
    heads = [h for h, _, _ in INPUTS] + [h for h, _, _, _ in DERIVED]
    for j, h in enumerate(heads, 1):
        c = ws.cell(row=4, column=j, value=h)
        c.font, c.fill = F_H, FILL_H
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 42
    for i, r in enumerate(inds):
        row = R0 + i
        for j, (_, key, fmt) in enumerate(INPUTS, 1):
            v = r[key]
            if key == "financial":
                v = 1 if v else 0
            c = ws.cell(row=row, column=j, value=v)
            c.font = F_IN if j > 1 else F_CALC
            if fmt:
                c.number_format = fmt
        for _, col, f, fmt in DERIVED:
            c = ws[f"{col}{row}"]
            c.value = f.format(r=row, **{k: v for k, v in zip("ABCDEFGHIJKLMNOPQRSTUV", [C[k] for _, k, _ in INPUTS])})
            c.font = F_CALC
            if fmt:
                c.number_format = fmt
    ws.column_dimensions["A"].width = 34
    for j in range(2, len(heads) + 1):
        ws.column_dimensions[L(j)].width = 11
    ws.freeze_panes = "B5"


def tear_sheet(ws, name):
    ws["A1"] = "Industry tear sheet"
    ws["A1"].font = F_T
    ws["A2"] = "Industry (type any name from the Data sheet)"
    ws["A2"].font = F_B
    ws["B2"] = name
    ws["B2"].font, ws["B2"].fill = F_IN, FILL_KEY
    ws["A3"] = "Row in Data"
    ws["B3"] = f"=MATCH(B2,Data!$A${R0}:$A${R1},0)"
    look = lambda col: f"=INDEX(Data!${col}${R0}:${col}${R1},$B$3)"
    rows = [("Verdict", "AL", None, True), ("Score (0-100)", "AK", "0.0", True),
            ("Rank: returns", "AG", "0.00", False), ("Rank: growth", "AH", "0.00", False),
            ("Rank: value", "AI", "0.00", False), ("Rank: risk", "AJ", "0.00", False),
            ("Firms", C["firms"], "0", False), ("Market cap ($m)", C["market_cap"], M0, False),
            ("Share of US market cap", "AM", PCT, False), ("Revenue ($m)", C["revenue"], M0, False),
            ("EBITDA ($m)", C["ebitda"], M0, False), ("Net income ($m)", C["net_income"], M0, False),
            ("EV/EBITDA", "W", X1, False), ("EV/Sales", "X", X1, False), ("P/E", "Y", X1, False), ("P/B", "Z", X1, False),
            ("Relative multiple", "AF", N2, True), ("ROE", "AA", PCT, False), ("ROIC (after tax)", "AB", PCT, False),
            ("Cost of capital", C["cost_of_capital"], PCT, False), ("Cost of equity", C["cost_of_equity"], PCT, False),
            ("Return spread", "AC", PCT, True), ("Revenue CAGR 5y", C["rev_cagr_5y"], PCT, False),
            ("Expected EPS growth 5y", C["eps_growth_next5"], PCT, False), ("Beta", C["beta"], N2, False),
            ("Debt / capital", C["debt_weight"], PCT, False)]
    out = {}
    for i, (lab, col, fmt, key) in enumerate(rows, 5):
        ws[f"A{i}"] = lab
        ws[f"A{i}"].font = F_B if key else F_CALC
        c = ws[f"B{i}"]
        c.value = look(col)
        c.font = F_LINK
        if fmt:
            c.number_format = fmt
        if key:
            c.fill = FILL_KEY
        out[lab] = f"'Tear sheet'!B{i}"
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 26
    return out


def run():
    m = json.load(open(ROOT / "outputs" / "metrics.json"))
    inds = sorted(m["industries"], key=lambda r: r["industry"].lower())
    total_mc = m["totals"]["Total Market"]["market_cap"]
    XL.mkdir(exist_ok=True)
    cells = {}
    for r in inds:
        wb = Workbook()
        ts = wb.active
        ts.title = "Tear sheet"
        ds = wb.create_sheet("Data")
        data_sheet(ds, inds, total_mc)
        cells[r["industry"]] = tear_sheet(ts, r["industry"])
        wb.save(XL / f"Industry_{slug(r['industry'])}.xlsx")
    wb = Workbook()
    ds = wb.active
    ds.title = "Data"
    data_sheet(ds, inds, total_mc)
    wb.save(XL / "Industry_Database.xlsx")
    json.dump(cells, open(ROOT / "outputs" / "excel_cells.json", "w"), indent=1)
    print("built", len(inds) + 1)


if __name__ == "__main__":
    run()
