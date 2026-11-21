import json, sys
from pathlib import Path
from openpyxl import load_workbook
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tear_sheet import slug
m = json.load(open(ROOT / "outputs/metrics.json"))
cells = json.load(open(ROOT / "outputs/excel_cells.json"))
n = bad = 0; worst = 0.0
num = {"Score (0-100)": "score", "Relative multiple": "rel_multiple", "Return spread": "spread", "EV/EBITDA": "ev_ebitda",
       "P/E": "pe", "P/B": "pb", "ROE": "roe", "ROIC (after tax)": "roic", "Share of US market cap": "share_of_market_cap"}
ranks = {"Rank: returns": "returns", "Rank: growth": "growth", "Rank: value": "value", "Rank: risk": "risk"}
for r in m["industries"]:
    wb = load_workbook(ROOT / f"excel/Industry_{slug(r['industry'])}.xlsx", data_only=True)
    c = cells[r["industry"]]
    v = lambda ref: wb["Tear sheet"][ref.split("!")[1]].value
    pairs = [(v(c[k]), r[f]) for k, f in num.items()] + [(v(c[k]), r["ranks"][f]) for k, f in ranks.items()]
    for xl, py in pairs:
        n += 1
        if py is None:
            if xl not in (None, ""): bad += 1; print("EXPECTED BLANK", r["industry"], xl)
            continue
        if not isinstance(xl, (int, float)): bad += 1; print("NONNUM", r["industry"], xl, py); continue
        gap = abs(xl - py) / max(1.0, abs(py)); worst = max(worst, gap)
        if gap > 1e-9: bad += 1; print("MISMATCH", r["industry"], xl, py)
    n += 1
    if v(c["Verdict"]) != r["verdict"]: bad += 1; print("VERDICT", r["industry"], v(c["Verdict"]), r["verdict"])
print(f"checked {n} values, mismatches {bad}, worst gap {worst:.1e}")
sys.exit(1 if bad else 0)
