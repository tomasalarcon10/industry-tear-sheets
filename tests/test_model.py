import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import model as Mo  # noqa: E402
from tear_sheet import slug  # noqa: E402

M = json.load(open(ROOT / "outputs" / "metrics.json"))
INDS = M["industries"]


def test_coverage():
    assert len(INDS) == 94
    for f in ("DollarUS.csv", "wacc.csv", "histgr.csv"):
        rows = list(csv.reader(open(ROOT / "data" / "raw" / f, encoding="utf-8")))
        assert len(rows) - 1 == 96                       # 94 industries + 2 totals
    assert sum(M["summary"]["verdicts"].values()) == 94


def test_totals_add_up():
    tot = M["totals"]["Total Market"]
    assert sum(r["firms"] for r in INDS) == pytest.approx(tot["firms"], abs=2)
    assert sum(r["market_cap"] for r in INDS) == pytest.approx(tot["market_cap"], rel=1e-3)


@pytest.mark.parametrize("r", INDS, ids=lambda r: r["industry"])
def test_industry(r):
    if r["ebitda"] > 0:
        assert r["ev_ebitda"] == pytest.approx(r["ev"] / r["ebitda"])
    if r["net_income"] > 0:
        assert r["pe"] == pytest.approx(r["market_cap"] / r["net_income"])
    if r["spread"] is not None:
        base = r["roe"] - r["cost_of_equity"] if r["financial"] else r["roic"] - r["cost_of_capital"]
        assert r["spread"] == pytest.approx(base)
    assert r["verdict"] == Mo.verdict(r["spread"], r["rel_multiple"])
    for k, v in r["ranks"].items():
        assert v is None or 0 <= v <= 1
    av = [v for v in r["ranks"].values() if v is not None]
    if av:
        assert r["score"] == pytest.approx(100 * np.mean(av))
    assert (ROOT / "reports" / f"{slug(r['industry'])}.pdf").exists()
    assert (ROOT / "excel" / f"Industry_{slug(r['industry'])}.xlsx").exists()


def test_relative_multiple_median_is_one():
    nf = [r["rel_multiple"] for r in INDS if not r["financial"] and r["rel_multiple"] is not None]
    fi = [r["rel_multiple"] for r in INDS if r["financial"] and r["rel_multiple"] is not None]
    assert np.median(nf) == pytest.approx(1) and np.median(fi) == pytest.approx(1)


def test_rank_definition():
    vals = [1.0, 2.0, 3.0, None]
    assert Mo.rank(vals, 1.0) == 0 and Mo.rank(vals, 3.0) == 1
    assert Mo.rank(vals, 3.0, higher_is_better=False) == 0


def test_companies_and_deals_attached():
    assert sum(len(r["companies"]) for r in INDS) == 85
    assert sum(len(r["deals"]) for r in INDS) == 43


RECENT = [json.loads(l) for l in open(ROOT / "data" / "recent_deals.jsonl") if l.strip()]
MSIZE = [json.loads(l) for l in open(ROOT / "data" / "market_size.jsonl") if l.strip()]
NAMES = {r["industry"] for r in INDS}


def test_every_industry_has_a_sourced_recent_deal():
    assert all(r["recent_deals"] for r in INDS)
    assert sum(len(r["recent_deals"]) for r in INDS) == len(RECENT)


@pytest.mark.parametrize("d", RECENT, ids=lambda d: f"{d['industry']}|{d['target']}"[:60])
def test_recent_deal_record(d):
    assert d["industry"] in NAMES
    assert d["url"].startswith("https://")
    assert d["date"][:4] in ("2025", "2026")
    assert d["acquirer"] and d["target"]
    assert d["value_usd_bn"] is None or d["value_usd_bn"] > 0


def test_recent_deals_sorted_by_value():
    for r in INDS:
        v = [d["value_usd_bn"] or 0 for d in r["recent_deals"]]
        assert v == sorted(v, reverse=True)


def test_market_size_records():
    assert len({m["industry"] for m in MSIZE}) == len(MSIZE)
    for m in MSIZE:
        assert m["industry"] in NAMES and m["url"].startswith("https://")
        assert m["value_usd_bn"] > 0 and m["year"] >= 2025 and m["publisher"] in ("IBISWorld", "Gartner", "SEMI")
    assert M["summary"]["with_market_size"] == len(MSIZE)
    assert sum(r["market_size"] is not None for r in INDS) == len(MSIZE)
