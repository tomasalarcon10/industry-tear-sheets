"""One-page industry tear sheet generator.

    python tear_sheet.py                      # every industry + the book
    python tear_sheet.py "Semiconductor"      # one industry
Writes reports/<industry>.pdf and reports/Industry_Tear_Sheets_Book.pdf.
"""
from __future__ import annotations

import json
import re
import sys
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pypdf import PdfWriter  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

import model as Mo  # noqa: E402

ROOT = Mo.ROOT
REP = ROOT / "reports"
NAVY = colors.HexColor("#1F3864")
GREY = colors.HexColor("#6b6b6b")
LIGHT = colors.HexColor("#eef1f6")
VC = {"Quality at a discount": "#1a7f5a", "Quality, priced for it": "#2f5fa7", "Cheap for a reason": "#b07400",
      "Expensive without returns": "#c0392b", "Not enough data": "#6b6b6b"}
RC = {"Buy": "#1a7f5a", "Hold": "#b07400", "Sell": "#c0392b"}
S = {
    "title": ParagraphStyle("t", fontName="Times-Bold", fontSize=17, leading=20, textColor=NAVY),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=GREY),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=NAVY, spaceAfter=2),
    "body": ParagraphStyle("b", fontName="Helvetica", fontSize=7.6, leading=9.6),
    "cell": ParagraphStyle("c", fontName="Helvetica", fontSize=6.9, leading=8.2),
    "small": ParagraphStyle("sm", fontName="Helvetica", fontSize=6.2, leading=7.6, textColor=GREY),
}


def slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def pc(x, d=1, sign=False):
    if x is None:
        return "n/a"
    return f"{x:+.{d}%}" if sign else f"{x:.{d}%}"


def xm(x):
    return "n/m" if x is None else f"{x:.1f}x"


def bn(x_m):
    if x_m is None:
        return "n/a"
    if abs(x_m) >= 1e6:
        return f"${x_m / 1e6:,.2f}tn"
    if abs(x_m) >= 1e3:
        return f"${x_m / 1e3:,.1f}bn"
    return f"${x_m:,.0f}m"


def rk(x):
    return "" if x is None else f"{100 * x:.0f}"


def tbl(data, widths, right_from=1, head=True):
    t = Table(data, colWidths=widths)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", 6.9), ("ALIGN", (right_from, 0), (-1, -1), "RIGHT"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1.6),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6), ("LEFTPADDING", (0, 0), (-1, -1), 3),
          ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d5d5d5"))]
    if head:
        st += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 6.9), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("BACKGROUND", (0, 0), (-1, 0), NAVY)]
    t.setStyle(TableStyle(st))
    return t


def img(fig, w, h):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=220)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w * inch, height=h * inch)


def pillar_chart(r, w=3.3, h=1.35):
    fig, ax = plt.subplots(figsize=(w, h))
    labs = ["Returns", "Growth", "Value", "Risk"]
    vals = [None if r["ranks"][k] is None else 100 * r["ranks"][k] for k in Mo.PILLARS]
    for i, v in enumerate(vals):
        ax.barh(i, 100, color="#eceff4", height=0.55)
        if v is not None:
            col = "#1a7f5a" if v >= 66 else "#b07400" if v >= 33 else "#c0392b"
            ax.barh(i, v, color=col, height=0.55)
            if v > 88:
                ax.text(v - 2, i, f"{v:.0f}", va="center", ha="right", fontsize=6.5, color="white")
            else:
                ax.text(v + 2, i, f"{v:.0f}", va="center", fontsize=6.5)
    ax.set_yticks(range(4), labs, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 50, 100])
    ax.tick_params(axis="x", labelsize=5.5)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_title("Rank among 94 industries (100 = best)", fontsize=6.5, loc="left")
    fig.tight_layout(pad=0.3)
    return img(fig, w, h)


def map_chart(r, allr, w=3.6, h=2.9):
    fig, ax = plt.subplots(figsize=(w, h))
    pts = [x for x in allr if x["spread"] is not None and x["rel_multiple"] is not None]
    clipx = lambda v: max(0.1, min(v, 4))
    clipy = lambda v: max(-0.2, min(v, 0.5)) * 100
    ax.scatter([clipx(x["rel_multiple"]) for x in pts], [clipy(x["spread"]) for x in pts], s=8, color="#c7cedb",
               edgecolor="none")
    if r in pts:
        ax.scatter([clipx(r["rel_multiple"])], [clipy(r["spread"])], s=55, color=VC[r["verdict"]], edgecolor="white",
                   zorder=3)
    ax.axvline(1, color="#888", lw=0.7, ls=":")
    ax.axhline(0, color="#888", lw=0.7, ls=":")
    ax.set_xscale("log")
    ax.set_xticks([0.25, 0.5, 1, 2, 4], ["0.25x", "0.5x", "1x", "2x", "4x"])
    ax.minorticks_off()
    ax.tick_params(labelsize=5.5)
    ax.set_xlabel("Multiple relative to the median industry (log)", fontsize=6)
    ax.set_ylabel("Return spread, pp", fontsize=6)
    kw = dict(fontsize=5.3, color="#777")
    ax.text(0.11, 46, "Quality at a discount", **kw)
    ax.text(3.9, 46, "Quality, priced for it", ha="right", **kw)
    ax.text(0.11, -18, "Cheap for a reason", **kw)
    ax.text(3.9, -18, "Expensive, no returns", ha="right", **kw)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.3)
    return img(fig, w, h)


def bullets(r, m):
    s = m["summary"]
    fin = r["financial"]
    out = []
    mult = (f"P/B {xm(r['pb'])} ({r['rel_multiple']:.2f}x the median financial industry)" if fin and r["rel_multiple"]
            else f"EV/EBITDA {xm(r['ev_ebitda'])} ({r['rel_multiple']:.2f}x the median industry)" if r["rel_multiple"]
            else "no meaningful multiple")
    ret = (f"ROE {pc(r['roe'])} vs a {pc(r['cost_of_equity'])} cost of equity" if fin else
           f"ROIC {pc(r['roic'])} vs a {pc(r['cost_of_capital'])} cost of capital")
    out.append(f"<b>{r['verdict']}.</b> {ret} (spread {pc(r['spread'], sign=True)}); {mult}.")
    out.append(f"<b>Size.</b> {int(r['firms'])} US-listed firms, {bn(r['market_cap'])} of market cap "
               f"({pc(r['share_of_market_cap'])} of the market, #{r['size_rank']} of 94), {bn(r['revenue'])} of revenue.")
    out.append(f"<b>Growth.</b> Revenue {pc(r['rev_cagr_5y'])} a year over five years; analysts expect EPS growth of "
               f"{pc(r['eps_growth_next5'])} a year for the next five.")
    out.append(f"<b>Score {r['score']:.0f}/100</b>, #{r['score_rank']} of {sum(x['score'] is not None for x in m['industries'])} industries "
               f"(average rank on returns, growth, value and risk)." if r["score"] is not None else "No score.")
    return out


def story(r, m):
    tot = m["totals"]
    mk = tot["Total Market (without financials)"] if not r["financial"] else tot["Total Market"]
    st = []
    head = Table([[Paragraph(r["industry"], S["title"]),
                   Paragraph(f"<b>{r['verdict']}</b>", ParagraphStyle("v", fontName="Helvetica-Bold", fontSize=9.5,
                                                                         textColor=colors.HexColor(VC[r["verdict"]]),
                                                                         alignment=2)),
                   Paragraph(f"<b>{r['score']:.0f}</b>/100" if r["score"] is not None else "n/a",
                             ParagraphStyle("sc", fontName="Helvetica", fontSize=13, alignment=2))]],
                 colWidths=[4.1 * inch, 2.2 * inch, 0.8 * inch])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, NAVY),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    st.append(head)
    st.append(Paragraph(f"Industry tear sheet | US-listed companies | Damodaran industry data, {m['data_date']} | "
                        f"{'financial industry: returns on equity, P/B' if r['financial'] else 'non-financial industry: returns on capital, EV/EBITDA'}",
                        S["sub"]))
    st.append(Spacer(1, 4))
    left = [Paragraph("Decide in 30 seconds", S["h"])] + [Paragraph(b, S["body"]) for b in bullets(r, m)]
    lt = Table([[x] for x in left], colWidths=[3.75 * inch])
    lt.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    st.append(Table([[lt, pillar_chart(r)]], colWidths=[3.8 * inch, 3.3 * inch],
                    style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    st.append(Spacer(1, 3))

    # size + valuation
    size = [["Size", ""], ["Firms", f"{int(r['firms'])}"], ["Market cap", bn(r["market_cap"])],
            ["Enterprise value", bn(r["ev"])], ["Revenue", bn(r["revenue"])], ["EBITDA", bn(r["ebitda"])],
            ["Net income", bn(r["net_income"])], ["Share of US market cap", pc(r["share_of_market_cap"])],
            ["Average company age", f"{r['age']:.0f} years"]]
    fin = r["financial"]
    val = [["Valuation", "Industry", "Market", "Rank*"],
           ["EV/EBITDA", "n/m" if fin else xm(r["ev_ebitda"]), xm(mk["ev_ebitda"]) if not fin else "n/m", ""],
           ["EV/Sales", "n/m" if fin else xm(r["ev_sales"]), xm(mk["ev_sales"]) if not fin else "n/m", ""],
           ["P/E", xm(r["pe"]), xm(mk["pe"]), ""], ["P/B", xm(r["pb"]), xm(mk["pb"]), ""],
           ["Relative multiple", f"{r['rel_multiple']:.2f}x" if r["rel_multiple"] else "n/a", "1.00x",
            rk(r["ranks"]["value"])]]
    st.append(Table([[tbl(size, [1.9 * inch, 1.6 * inch]), tbl(val, [1.15 * inch, 0.8 * inch, 0.8 * inch, 0.6 * inch])]],
                    colWidths=[3.6 * inch, 3.5 * inch], style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                                                             ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    st.append(Spacer(1, 4))
    prof = [["Profitability and returns", "Industry", "Market"],
            ["Gross margin", pc(r["gross_margin"]), pc(mk["gross_margin"])],
            ["EBITDA margin", "n/m" if fin else pc(r["ebitda_margin"]), "n/m" if fin else pc(mk["ebitda_margin"])],
            ["Operating margin", "n/m" if fin else pc(r["operating_margin"]), "n/m" if fin else pc(mk["operating_margin"])],
            ["Net margin", pc(r["net_margin"]), pc(mk["net_margin"])], ["ROE", pc(r["roe"]), pc(mk["roe"])],
            ["ROIC (after tax)", "n/m" if fin else pc(r["roic"]), "n/m" if fin else pc(mk["roic"])],
            ["Return spread (rank*)", f"{pc(r['spread'], sign=True)} ({rk(r['ranks']['returns'])})", ""]]
    grw = [["Growth and risk", "Industry", "Market"],
           ["Revenue CAGR, 5 years (rank*)", f"{pc(r['rev_cagr_5y'])} ({rk(r['ranks']['growth'])})", pc(mk["rev_cagr_5y"])],
           ["Net income CAGR, 5 years", pc(r["ni_cagr_5y"]), pc(mk["ni_cagr_5y"])],
           ["Expected EPS growth, 5 years", pc(r["eps_growth_next5"]), pc(mk["eps_growth_next5"])],
           ["Beta (rank*)", f"{r['beta']:.2f} ({rk(r['ranks']['risk'])})", f"{mk['beta']:.2f}"],
           ["Std. dev. of stock returns", pc(r["std_dev"]), pc(mk["std_dev"])],
           ["Debt / capital", pc(r["debt_weight"]), pc(mk["debt_weight"])],
           ["Cost of capital / equity", f"{pc(r['cost_of_capital'])} / {pc(r['cost_of_equity'])}",
            f"{pc(mk['cost_of_capital'])} / {pc(mk['cost_of_equity'])}"]]
    st.append(Table([[tbl(prof, [1.6 * inch, 1.05 * inch, 0.85 * inch]), tbl(grw, [1.65 * inch, 1.05 * inch, 0.8 * inch])]],
                    colWidths=[3.6 * inch, 3.5 * inch], style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                                                             ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    st.append(Spacer(1, 4))

    # map + companies/deals
    comp = [["Companies in my universe", "Mkt cap", "P/E", "House"]]
    for c in sorted(r["companies"], key=lambda c: -(c["market_cap_usd_bn"] or 0))[:7]:
        comp.append([Paragraph(f"{c['name']} ({c['ticker']})", S["cell"]),
                     f"${c['market_cap_usd_bn']:,.0f}bn" if c["market_cap_usd_bn"] else "n/a",
                     xm(c["pe"]) if c["pe"] and c["pe"] > 0 else "n/m", c["house_rating"]])
    if len(comp) == 1:
        comp.append([Paragraph("None of the 85 companies is classified here.", S["cell"]), "", "", ""])
    ct = tbl(comp, [1.75 * inch, 0.6 * inch, 0.45 * inch, 0.45 * inch])
    ct.setStyle(TableStyle([("TEXTCOLOR", (3, i), (3, i), colors.HexColor(RC.get(row[3], "#333")))
                            for i, row in enumerate(comp[1:], 1) if row[3] in RC]))
    dl = [["Deals by my universe (SEC filings)", "Year", "Equity", "Premium"]]
    for d in r["deals"][:5]:
        dl.append([Paragraph(f"{d['acquirer']} / {d['target']}", S["cell"]), d["announced"][:4], bn(d["equity_value_m"]),
                   pc(d["premium"], 0)])
    if len(dl) == 1:
        dl.append([Paragraph("No deal in the 43-deal database.", S["cell"]), "", "", ""])
    right = Table([[ct], [Spacer(1, 3)], [tbl(dl, [1.75 * inch, 0.4 * inch, 0.6 * inch, 0.5 * inch])]],
                  style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0)])
    st.append(Table([[map_chart(r, m["industries"]), right]], colWidths=[3.75 * inch, 3.35 * inch],
                    style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    st.append(Spacer(1, 4))
    st.append(Paragraph(
        "*Rank among the 94 industries, 0 = worst and 100 = best (higher spread and growth, lower relative multiple and "
        "beta rank higher). Aggregates: sums over the industry's firms (market cap / net income, and so on). Market = "
        f"{'total US market' if fin else 'US market without financials'}. Sources: Damodaran Online, industry data for "
        f"US firms, {m['data_date']} (pages.stern.nyu.edu/~adamodar: DollarUS, wacc, histgr); companies and house ratings "
        "from the comparable-companies and equity-research projects; deals from the precedent-transactions project "
        "(github.com/tomasalarcon10). Illustrative analysis, not investment advice.", S["small"]))
    return st


def build_one(r, m):
    REP.mkdir(exist_ok=True)
    path = REP / f"{slug(r['industry'])}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, leftMargin=0.65 * inch, rightMargin=0.65 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.45 * inch, title=f"Industry tear sheet: {r['industry']}",
                            author="Tomas Alarcon")
    doc.build(story(r, m))
    return path


def build_book(m, paths, cover_pages=2):
    s = m["summary"]
    cover = REP / "_cover.pdf"
    st = [Paragraph("Industry tear sheets: 94 US industries on one page each", S["title"]),
          Paragraph(f"Damodaran industry data, {m['data_date']} | {s['firms']:,} US-listed firms | "
                    f"${s['market_cap_tn']:.1f}tn of market cap", S["sub"]), Spacer(1, 8)]
    vc = s["verdicts"]
    st.append(Paragraph(
        f"Each sheet answers one question fast: is this industry earning more than its cost of capital, and is the "
        f"market already paying for it? {vc['Quality at a discount']} industries earn a positive spread at a multiple "
        f"below the median industry, {vc['Quality, priced for it']} earn it at a premium multiple, "
        f"{vc['Cheap for a reason']} are cheap without the returns and {vc['Expensive without returns']} are expensive "
        "without them. The score averages each industry's rank on returns, growth, value and risk.", S["body"]))
    st.append(Spacer(1, 6))
    data = [["#", "Industry", "Score", "Verdict", "Mkt cap", "Spread", "Rel. multiple", "Page"]]
    order = sorted(m["industries"], key=lambda r: (r["score_rank"] if r.get("score_rank") else 999))
    page_of = {r["industry"]: i + 1 + cover_pages
               for i, r in enumerate(sorted(m["industries"], key=lambda r: r["industry"].lower()))}
    for r in order:
        data.append([r.get("score_rank", ""), Paragraph(r["industry"], S["cell"]),
                     f"{r['score']:.0f}" if r["score"] is not None else "n/a",
                     Paragraph(r["verdict"], ParagraphStyle("vv", parent=S["cell"], textColor=colors.HexColor(VC[r["verdict"]]))),
                     bn(r["market_cap"]), pc(r["spread"], sign=True), f"{r['rel_multiple']:.2f}x" if r["rel_multiple"] else "n/a",
                     page_of[r["industry"]]])
    t = tbl(data, [0.3 * inch, 2.2 * inch, 0.45 * inch, 1.45 * inch, 0.8 * inch, 0.6 * inch, 0.75 * inch, 0.4 * inch], 2)
    t.setStyle(TableStyle([("ALIGN", (3, 0), (3, -1), "LEFT")]))
    st.append(t)
    doc = SimpleDocTemplate(str(cover), pagesize=LETTER, leftMargin=0.65 * inch, rightMargin=0.65 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.45 * inch)
    doc.build(st)
    from pypdf import PdfReader
    n = len(PdfReader(str(cover)).pages)
    if n != cover_pages:
        cover.unlink()
        return build_book(m, paths, n)
    w = PdfWriter()
    w.append(str(cover))
    for p in paths:  # paths come in the same order as page_of (industry name, case-insensitive)
        w.append(str(p))
    w.add_metadata({"/Title": "Industry tear sheets: 94 US industries", "/Author": "Tomas Alarcon"})
    w.write(str(REP / "Industry_Tear_Sheets_Book.pdf"))
    cover.unlink()


def main(argv):
    m = json.load(open(ROOT / "outputs" / "metrics.json"))
    inds = m["industries"]
    if len(argv) > 1:
        r = next(x for x in inds if x["industry"].lower() == argv[1].lower())
        print(build_one(r, m))
        return
    paths = [build_one(r, m) for r in sorted(inds, key=lambda r: r["industry"].lower())]
    build_book(m, paths)
    print("tear sheets", len(paths))


if __name__ == "__main__":
    main(sys.argv)
