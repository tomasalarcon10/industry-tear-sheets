"""Static charts (PNG + HTML) and the interactive dashboard."""
from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go

import model as Mo

ROOT = Mo.ROOT
OUT = ROOT / "outputs"
CH = OUT / "charts"
BG, CARD, TEXT, TEXT2, MUTED, GRID = "#1a1a19", "#222220", "#f0efec", "#c3c2b7", "#8a8980", "#3a3936"
VC = {"Quality at a discount": "#199e70", "Quality, priced for it": "#3987e5", "Cheap for a reason": "#c98500",
      "Expensive without returns": "#e66767", "Not enough data": "#8a8980"}


def layout(fig, title, h=640, w=1100):
    fig.update_layout(title=dict(text=title, font=dict(size=19, color=TEXT), x=0.02),
                      paper_bgcolor=BG, plot_bgcolor=CARD, font=dict(color=TEXT2, family="Inter, Arial"),
                      height=h, width=w, margin=dict(l=80, r=40, t=90, b=60),
                      legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.07, x=0.0))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=MUTED)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=MUTED)
    return fig


def save(fig, name):
    CH.mkdir(parents=True, exist_ok=True)
    fig.write_html(CH / f"{name}.html", include_plotlyjs="cdn")
    fig.write_image(CH / f"{name}.png", scale=2)


def ok(m):
    return [r for r in m["industries"] if r["spread"] is not None and r["rel_multiple"] is not None]


def chart_map(m):
    rs = ok(m)
    fig = go.Figure()
    top = {r["industry"] for r in sorted(rs, key=lambda r: -r["market_cap"])[:12]} | {m["featured"]}
    for v in Mo.VERDICTS:
        sub = [r for r in rs if r["verdict"] == v]
        fig.add_trace(go.Scatter(
            x=[min(max(r["rel_multiple"], 0.1), 5) for r in sub], y=[min(max(r["spread"], -0.25), 0.6) * 100 for r in sub],
            mode="markers+text", name=f"{v} ({len(sub)})",
            text=[r["industry"] if r["industry"] in top else "" for r in sub], textposition="top center",
            textfont=dict(size=9, color=TEXT2),
            marker=dict(size=[8 + 40 * np.sqrt(r["market_cap"] / 7.9e6) for r in sub], color=VC[v], opacity=0.85,
                        line=dict(color=BG, width=1)),
            customdata=[[r["industry"], r["market_cap"] / 1e6, r["score"] or 0] for r in sub],
            hovertemplate="%{customdata[0]}<br>relative multiple %{x:.2f}x<br>spread %{y:+.1f} pp<br>"
                          "market cap $%{customdata[1]:.2f}tn<br>score %{customdata[2]:.0f}<extra></extra>"))
    fig.add_vline(x=1, line=dict(color=MUTED, dash="dot"))
    fig.add_hline(y=0, line=dict(color=MUTED, dash="dot"))
    fig.update_xaxes(title="Multiple relative to the median industry (EV/EBITDA; P/B for financials), log scale",
                     type="log", tickvals=[0.25, 0.5, 1, 2, 4], ticktext=["0.25x", "0.5x", "1x", "2x", "4x"])
    fig.update_yaxes(title="Return spread: ROIC - cost of capital (ROE - cost of equity for financials), pp",
                     type="linear")
    layout(fig, "94 US industries: are they earning their cost of capital, and is the market paying for it? "
                "(bubble = market cap)", h=720, w=1200)
    save(fig, "industry_map")


def chart_scores(m):
    rs = sorted([r for r in m["industries"] if r["score"] is not None], key=lambda r: r["score"])
    pick = rs[:12] + rs[-12:]
    fig = go.Figure(go.Bar(y=[r["industry"] for r in pick], x=[r["score"] for r in pick], orientation="h",
                           marker=dict(color=[VC[r["verdict"]] for r in pick], line=dict(color=BG, width=1.5)),
                           text=[f"{r['score']:.0f}" for r in pick], textposition="outside", textfont=dict(color=TEXT2),
                           hovertemplate="%{y}: %{x:.1f}<extra></extra>", showlegend=False))
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=[r["industry"] for r in pick], tickfont=dict(size=10))
    fig.update_xaxes(title="Score: average rank on returns, growth, value and risk (0-100)", type="linear", range=[0, 90])
    layout(fig, "Top 12 and bottom 12 industries by score (colour = verdict)", h=760)
    save(fig, "industry_scores")


def chart_3d(m):
    rs = ok(m)
    fig = go.Figure()
    for v in Mo.VERDICTS:
        sub = [r for r in rs if r["verdict"] == v]
        fig.add_trace(go.Scatter3d(
            x=[min(max(r["rev_cagr_5y"], -0.15), 0.5) * 100 for r in sub],
            y=[min(max(r["spread"], -0.25), 0.6) * 100 for r in sub],
            z=[np.log10(min(max(r["rel_multiple"], 0.1), 5)) for r in sub], mode="markers", name=v,
            marker=dict(size=[3 + 14 * np.sqrt(r["market_cap"] / 7.9e6) for r in sub], color=VC[v], opacity=0.9),
            text=[r["industry"] for r in sub], hovertemplate="%{text}<extra></extra>"))
    ax = lambda t, **k: dict(title=t, backgroundcolor=CARD, gridcolor=GRID, color=TEXT2, **k)
    fig.update_layout(scene=dict(xaxis=ax("Revenue CAGR 5y, %"), yaxis=ax("Return spread, pp"),
                                 zaxis=ax("Relative multiple", tickvals=[np.log10(x) for x in (0.25, 0.5, 1, 2, 4)],
                                          ticktext=["0.25x", "0.5x", "1x", "2x", "4x"]),
                                 aspectmode="cube", camera=dict(eye=dict(x=1.7, y=-1.5, z=0.8))))
    layout(fig, "Growth, returns and valuation of 94 US industries (bubble = market cap)", h=760, w=1250)
    save(fig, "industry_space_3d")


def chart_size(m):
    rs = sorted(m["industries"], key=lambda r: -r["market_cap"])[:20][::-1]
    fig = go.Figure(go.Bar(y=[r["industry"] for r in rs], x=[r["market_cap"] / 1e6 for r in rs], orientation="h",
                           marker=dict(color=[VC[r["verdict"]] for r in rs], line=dict(color=BG, width=1.5)),
                           text=[f"${r['market_cap'] / 1e6:.2f}tn | {r['share_of_market_cap']:.1%}" for r in rs],
                           textposition="outside", textfont=dict(color=TEXT2), showlegend=False,
                           hovertemplate="%{y}: $%{x:.2f}tn<extra></extra>"))
    fig.update_yaxes(type="category")
    fig.update_xaxes(title="Market cap of US-listed firms, $ trillion", type="linear", range=[0, 9.5])
    layout(fig, "The 20 largest US industries by market cap (colour = verdict)", h=700)
    save(fig, "industry_size")


def dashboard(m):
    keep = ["industry", "financial", "firms", "market_cap", "revenue", "ebitda", "net_income", "ev_ebitda", "ev_sales", "pe",
            "pb", "gross_margin", "operating_margin", "net_margin", "roe", "roic", "cost_of_capital", "cost_of_equity",
            "spread", "rel_multiple", "rev_cagr_5y", "eps_growth_next5", "beta", "debt_weight", "share_of_market_cap",
            "ranks", "score", "verdict", "companies", "recent_deals", "market_size", "size_rank"]
    data = {"featured": m["featured"], "summary": m["summary"],
            "inds": [{k: r[k] for k in keep} for r in m["industries"]]}
    for r in data["inds"]:
        r["companies"] = [{k: c[k] for k in ("ticker", "name", "market_cap_usd_bn", "pe", "house_rating")} for c in r["companies"]]
        r["recent_deals"] = [{k: d[k] for k in ("acquirer", "target", "date", "value_usd_bn", "value_text", "url")} for d in r["recent_deals"]]
    html = (ROOT / "src" / "dashboard_template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, default=float)).replace("__N__", str(len(m["industries"])))
    (ROOT / "dashboard.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    m = json.load(open(OUT / "metrics.json"))
    for f in (chart_map, chart_scores, chart_3d, chart_size, dashboard):
        f(m)
    print("charts + dashboard written")
