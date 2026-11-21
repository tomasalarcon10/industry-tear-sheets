"""Assemble the project inputs.

- data/raw/*.csv           Damodaran US industry data, January 2026 (DollarUS, wacc, histgr pages)
- dcf-valuation            Damodaran industry of each company in the 85-company universe
- comparable-companies     market snapshot of the universe (market cap, multiples)
- equity-research          house rating and street rating of each company
- precedent-transactions   43 SEC-documented deals; data/deal_industry_map.json assigns each target an industry
Writes data/universe.json and data/deals.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT.parent
EXTRA_INDUSTRY = {"EAND.AE": "Telecom. Services", "IHC.AE": "Diversified", "FAB.AE": "Bank (Money Center)"}


def main():
    dcf = {r["ticker"]: r for r in json.load(open(P / "dcf-valuation" / "outputs" / "metrics.json"))["rows"]}
    comps = json.load(open(P / "comparable-companies" / "outputs" / "metrics.json"))["companies"]
    er = {r["ticker"]: r for r in json.load(open(P / "equity-research" / "outputs" / "metrics.json"))["companies"]}
    uni = []
    for c in comps:
        t = c["ticker"]
        ind = dcf[t]["industry"] if t in dcf else EXTRA_INDUSTRY[t]
        e = er[t]
        st = c["stats"]
        uni.append({"ticker": t, "name": c["name"], "country": c["country"], "currency": c["currency"],
                    "industry": ind, "market_cap_usd_bn": (dcf[t]["market_cap_usd"] / 1e9) if t in dcf else None,
                    "pe": (st.get("pe") or {}).get("own"), "ev_ebitda": (st.get("ev_ebitda") or {}).get("own"),
                    "pb": (st.get("pb") or {}).get("own"),
                    "house_rating": e["rating"], "street_rating": (e["street"] or {}).get("rating")})
    m = json.load(open(ROOT / "data" / "deal_industry_map.json"))
    deals = []
    for d in json.load(open(P / "precedent-transactions" / "outputs" / "metrics.json"))["deals"]:
        deals.append({"deal_id": d["deal_id"], "target": d["target"], "acquirer": d["acquirer"], "industry": m[d["deal_id"]],
                      "announced": d["announced"], "equity_value_m": d["equity_value_m"], "ev_ebitda": d["ev_ebitda"],
                      "ev_revenue": d["ev_revenue"], "premium": d["premium"], "consideration": d["consideration"],
                      "source": d["source"]})
    json.dump(uni, open(ROOT / "data" / "universe.json", "w"), indent=1)
    json.dump(deals, open(ROOT / "data" / "deals.json", "w"), indent=1)
    print(len(uni), "companies,", len(deals), "deals")


if __name__ == "__main__":
    main()
