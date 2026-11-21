"""Industry metrics, ranks and the one-line verdict for every US industry in Damodaran's January 2026 data.

All ratios are aggregates (sum of the industry's market caps / sum of its net income, and so on), the way
Damodaran computes industry totals, so large companies weigh more than small ones.

Pillars (rank among the 94 industries, 0 = worst, 100 = best):
- Returns:   non-financials ROIC - cost of capital; financials ROE - cost of equity
- Growth:    revenue CAGR over the last five years
- Value:     EV/EBITDA relative to the median non-financial industry (financials: P/B relative to the median
             financial industry); a lower relative multiple ranks higher
- Risk:      beta; a lower beta ranks higher
Score = average of the available pillar ranks.
Verdict (returns spread x relative multiple):
- Quality at a discount       spread > 0, relative multiple < 1
- Quality, priced for it      spread > 0, relative multiple >= 1
- Cheap for a reason          spread <= 0, relative multiple < 1
- Expensive without returns   spread <= 0, relative multiple >= 1
Rank of x = (number of industries with a strictly lower value) / (number of industries with a value - 1).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = ROOT / "outputs"

FEATURED = "Semiconductor"
DATA_DATE = "January 2026"
FINANCIALS = {"Bank (Money Center)", "Banks (Regional)", "Brokerage & Investment Banking",
              "Financial Svcs. (Non-bank & Insurance)", "Insurance (General)", "Insurance (Life)",
              "Insurance (Prop/Cas.)", "Investments & Asset Management", "Reinsurance"}
TOTALS = ("Total Market", "Total Market (without financials)")
PILLARS = ["returns", "growth", "value", "risk"]
VERDICTS = ["Quality at a discount", "Quality, priced for it", "Cheap for a reason", "Expensive without returns"]


def num(s):
    s = str(s).strip().replace("$", "").replace(",", "")
    if s in ("", "NA", "N/A"):
        return None
    if s.endswith("%"):
        return float(s[:-1]) / 100
    return float(s)


def read(name):
    rows = list(csv.reader(open(RAW / name, encoding="utf-8")))
    return rows[0], {r[0]: [num(x) for x in r[1:]] for r in rows[1:]}


def load():
    _, dol = read("DollarUS.csv")
    _, wacc = read("wacc.csv")
    _, gr = read("histgr.csv")
    out = {}
    for name, v in dol.items():
        w, g = wacc[name], gr[name]
        out[name] = {
            "industry": name, "financial": name in FINANCIALS,
            "firms": v[0], "age": v[1], "market_cap": v[2], "book_equity": v[3], "ev": v[4], "invested_capital": v[5],
            "debt": v[6], "revenue": v[7], "gross_profit": v[8], "ebitda": v[9], "ebit": v[10], "net_income": v[11],
            "beta": w[1], "cost_of_equity": w[2], "equity_weight": w[3], "std_dev": w[4], "cost_of_debt": w[5],
            "tax_rate": w[6], "debt_weight": w[7], "cost_of_capital": w[8],
            "ni_cagr_5y": g[1], "rev_cagr_5y": g[2], "rev_growth_next2": g[3], "rev_growth_next5": g[4],
            "eps_growth_next5": g[5],
        }
    return out


def ratio(a, b, positive_b=True):
    if a is None or b is None or b == 0 or (positive_b and b < 0):
        return None
    return a / b


def metrics(r):
    roic = ratio(r["ebit"] * (1 - r["tax_rate"]), r["invested_capital"]) if r["ebit"] is not None else None
    roe = ratio(r["net_income"], r["book_equity"])
    m = {
        "ev_ebitda": ratio(r["ev"], r["ebitda"]), "ev_sales": ratio(r["ev"], r["revenue"]),
        "pe": ratio(r["market_cap"], r["net_income"]), "pb": ratio(r["market_cap"], r["book_equity"]),
        "gross_margin": ratio(r["gross_profit"], r["revenue"]), "ebitda_margin": ratio(r["ebitda"], r["revenue"]),
        "operating_margin": ratio(r["ebit"], r["revenue"]), "net_margin": ratio(r["net_income"], r["revenue"]),
        "roe": roe, "roic": roic,
    }
    if r["financial"]:
        m["spread"] = None if roe is None else roe - r["cost_of_equity"]
    else:
        m["spread"] = None if roic is None else roic - r["cost_of_capital"]
    return m


def rank(values, x, higher_is_better=True):
    vals = [v for v in values if v is not None]
    if x is None or len(vals) < 2:
        return None
    p = sum(v < x for v in vals) / (len(vals) - 1)
    return p if higher_is_better else 1 - p


def verdict(spread, rel):
    if spread is None or rel is None:
        return "Not enough data"
    if spread > 0:
        return VERDICTS[0] if rel < 1 else VERDICTS[1]
    return VERDICTS[2] if rel < 1 else VERDICTS[3]


def run():
    OUT.mkdir(exist_ok=True)
    raw = load()
    tot = {k: {**raw[k], **metrics(raw[k])} for k in TOTALS}
    inds = [{**raw[k], **metrics(raw[k])} for k in raw if k not in TOTALS]
    mk_nf, mk = tot["Total Market (without financials)"], tot["Total Market"]
    med_fin_pb = float(np.median([r["pb"] for r in inds if r["financial"] and r["pb"] is not None]))
    med_ev_ebitda = float(np.median([r["ev_ebitda"] for r in inds if not r["financial"] and r["ev_ebitda"] is not None]))
    for r in inds:
        if r["financial"]:
            r["rel_multiple"] = ratio(r["pb"], med_fin_pb)
            r["rel_basis"] = "P/B vs the median financial industry"
        else:
            r["rel_multiple"] = ratio(r["ev_ebitda"], med_ev_ebitda)
            r["rel_basis"] = "EV/EBITDA vs the median non-financial industry"
        r["share_of_market_cap"] = r["market_cap"] / mk["market_cap"]
    cols = {k: [r[k] for r in inds] for k in ("spread", "rev_cagr_5y", "rel_multiple", "beta", "market_cap", "pe",
                                               "ev_ebitda", "operating_margin", "roe", "eps_growth_next5")}
    for r in inds:
        r["ranks"] = {"returns": rank(cols["spread"], r["spread"]),
                      "growth": rank(cols["rev_cagr_5y"], r["rev_cagr_5y"]),
                      "value": rank(cols["rel_multiple"], r["rel_multiple"], higher_is_better=False),
                      "risk": rank(cols["beta"], r["beta"], higher_is_better=False)}
        av = [v for v in r["ranks"].values() if v is not None]
        r["score"] = 100 * float(np.mean(av)) if av else None
        r["verdict"] = verdict(r["spread"], r["rel_multiple"])
        r["size_rank"] = int(sum(x > r["market_cap"] for x in cols["market_cap"]) + 1)
    scored = sorted([r for r in inds if r["score"] is not None], key=lambda r: -r["score"])
    for i, r in enumerate(scored, 1):
        r["score_rank"] = i
    uni = json.load(open(DATA / "universe.json"))
    deals = json.load(open(DATA / "deals.json"))
    for r in inds:
        r["companies"] = [c for c in uni if c["industry"] == r["industry"]]
        r["deals"] = sorted([d for d in deals if d["industry"] == r["industry"]], key=lambda d: d["announced"], reverse=True)
    vc = {v: sum(r["verdict"] == v for r in inds) for v in VERDICTS + ["Not enough data"]}
    summary = {
        "industries": len(inds), "firms": int(mk["firms"]), "market_cap_tn": mk["market_cap"] / 1e6,
        "verdicts": vc,
        "top_score": [(r["industry"], r["score"]) for r in scored[:10]],
        "bottom_score": [(r["industry"], r["score"]) for r in scored[-10:]],
        "with_universe_companies": sum(bool(r["companies"]) for r in inds),
        "with_deals": sum(bool(r["deals"]) for r in inds),
        "largest": [(r["industry"], r["market_cap"] / 1e6) for r in sorted(inds, key=lambda r: -r["market_cap"])[:5]],
        "market_ev_ebitda_nonfin": mk_nf["ev_ebitda"], "market_pe": mk["pe"], "market_pb": mk["pb"],
        "market_cost_of_capital": mk["cost_of_capital"], "market_roic_nonfin": mk_nf["roic"],
        "median_industry_ev_ebitda": med_ev_ebitda, "median_financial_pb": med_fin_pb,
    }
    metrics_out = {"data_date": DATA_DATE, "featured": FEATURED, "summary": summary, "totals": tot, "industries": inds}
    json.dump(metrics_out, open(OUT / "metrics.json", "w"), indent=1, default=float)
    return metrics_out


if __name__ == "__main__":
    m = run()
    s = m["summary"]
    print({k: v for k, v in s.items()})
    f = next(r for r in m["industries"] if r["industry"] == FEATURED)
    print({k: f[k] for k in ("ev_ebitda", "pe", "roic", "spread", "rel_multiple", "score", "score_rank", "verdict", "size_rank")},
          [c["ticker"] for c in f["companies"]], [d["deal_id"] for d in f["deals"]])
