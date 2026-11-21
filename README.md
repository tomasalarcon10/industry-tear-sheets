# Industry Tear Sheets

**Question:** can a whole industry be summarised on one page, well enough to decide quickly whether it deserves a closer look?

This project moves from companies to industries. It is a generator of one-page PDF tear sheets for all 94 US industries in Aswath Damodaran's January 2026 industry data, which covers 5,994 US-listed firms with $69.8tn of market cap. Each sheet answers one question first: **is this industry earning more than its cost of capital, and is the market already paying for it?** Below that answer come:

- the size of the industry;
- valuation against the market and against other industries;
- profitability and returns;
- growth and risk;
- a map of all 94 industries with this one highlighted;
- the companies from my 85-company universe that belong to the industry, with their house rating from my [equity-research](https://github.com/tomasalarcon10/equity-research) project;
- the acquisitions in it from my [precedent-transactions](https://github.com/tomasalarcon10/precedent-transactions) project.

All numbers come from `outputs/metrics.json`.

## Key results

- **Verdicts.**
  - 43 industries earn more than their cost of capital and trade below the median industry multiple (*Quality at a discount*).
  - 36 earn it at a premium multiple (*Quality, priced for it*).
  - 3 are cheap without the returns (*Cheap for a reason*).
  - 11 are expensive without them (*Expensive without returns*).
  - Electronics (Consumer & Office) has negative EBITDA, so it gets no verdict.
- **Highest scores:** Cable TV (79), Precious Metals (78) and Hospitals/Healthcare Facilities (77). They have positive spreads, low relative multiples and low betas.
- **Lowest score:** Auto & Truck (11), which has a negative spread at more than 4x the median industry's EV/EBITDA.
- **Size is not quality.** The five largest industries are Semiconductor ($7.86tn), Software (System & Application) ($7.00tn), Software (Entertainment) ($5.56tn), Computers/Peripherals ($4.33tn) and Retail (General) ($3.97tn). All five sit in *Quality, priced for it*.
- **Featured: Semiconductor.** It is the largest US industry (11.3% of market cap).
  - ROIC is 35.0% against a 10.6% cost of capital, a +24.4 pp spread and the 94th percentile on returns.
  - EV/EBITDA is 35.0x, 2.61x the median industry.
  - Its beta of 1.52 is among the highest.
  - The score is 39/100 (#78 of 94): an excellent business at a full price.

## Method

| Piece | Definition |
|---|---|
| Aggregates | Damodaran sums over the industry's firms, so ratios are market cap / net income, EV / EBITDA and so on; large firms weigh more |
| Return spread | ROIC (EBIT x (1 - tax) / invested capital) minus cost of capital; for the 9 financial industries, ROE minus cost of equity |
| Relative multiple | EV/EBITDA over the median non-financial industry (13.4x); for financials, P/B over the median financial industry (2.29x) |
| Verdict | spread above or below 0 x relative multiple above or below 1x |
| Ranks | share of industries with a strictly lower value (reversed for the multiple and beta), 0 to 100 |
| Score | average rank on returns (spread), growth (5-year revenue CAGR), value (relative multiple) and risk (beta) |

The companies are mapped to their Damodaran industry by my [dcf-valuation](https://github.com/tomasalarcon10/dcf-valuation) project; three companies without a DCF are mapped by hand in `src/collect.py`. Deal targets are mapped by hand in `data/deal_industry_map.json`.

## Files

| Path | Contents |
|---|---|
| `src/tear_sheet.py` | The generator. Run `python tear_sheet.py "Semiconductor"` for one sheet, or with no argument for all 94 plus the book. |
| `reports/<industry>.pdf` | 94 one-page tear sheets |
| `reports/Industry_Tear_Sheets_Book.pdf` | Ranked index (score, verdict, size, spread, multiple, page) followed by every sheet |
| `excel/Industry_<industry>.xlsx` | The tear sheet in cells, with the Damodaran inputs for all 94 industries. Every multiple, return, rank, score and verdict is a formula; type another industry name in B2 and the sheet updates. Blue cells are inputs, black cells formulas, green cells links, yellow cells key outputs. |
| `excel/Industry_Database.xlsx` | All 94 industries with every derived metric |
| `dashboard.html` | Pick an industry; re-weight the four score pillars to re-rank all 94; click any bubble on the map to load that industry |
| `data/raw/` | Damodaran DollarUS, wacc and histgr tables as published (January 2026) |
| `src/model.py`, `src/build_excel.py`, `src/charts.py` | Metrics and ranks (`outputs/metrics.json`), Excel, charts and dashboard |
| `outputs/charts/` | `industry_map`, `industry_scores`, `industry_space_3d`, `industry_size` (PNG and interactive HTML) |
| `tests/` | 99 pytest checks (`test_model.py`) and an Excel/Python parity script (`parity.py`) |

## Charts

![Industry map](outputs/charts/industry_map.png)
![3D](outputs/charts/industry_space_3d.png)
![Scores](outputs/charts/industry_scores.png)
![Size](outputs/charts/industry_size.png)

## Reproduce

```bash
pip install -r requirements.txt
cd src
python collect.py        # joins the universe and the deals (needs the sibling repositories; outputs included)
python model.py
python tear_sheet.py
python build_excel.py    # recalculate in Excel or LibreOffice
python charts.py
cd .. && pytest -q tests/test_model.py && python tests/parity.py
```

## Verification

- **Excel vs Python.** `tests/parity.py` compares 1,316 values from the 94 recalculated workbooks with the Python model: multiples, returns, spread, relative multiple, the four ranks, score and verdict. There are no mismatches; the largest gap is 5e-15.
- **Data checks (pytest).**
  - All three source tables have 94 industries plus 2 totals.
  - Industry market caps sum to the market total.
  - Every ratio, rank, score and verdict reproduces.
  - The median relative multiple is exactly 1x in both groups.
- **Dashboard.** A headless-browser check reproduces the score of all 94 industries in the dashboard's JavaScript.

## Limitations

- **US firms only.** Damodaran also publishes global industry tables, but only as spreadsheets that this pipeline does not read.
- **"Market size" means listed firms.** It is the revenue and market cap of US-listed firms in the industry, not the total addressable market. Private companies and foreign competitors are outside it.
- **Aggregate ratios are dominated by the largest firms.** Semiconductor is close to NVIDIA plus a long tail.
- **Damodaran's expected-growth columns can be extreme** for small or cyclical industries (for example Air Transport). The score therefore uses the historical revenue CAGR; expected EPS growth is shown for information.
- **Financial industries** report EBITDA and margins that are not meaningful; their sheets show n/m and use ROE and P/B instead.
- **Illustrative analysis, not investment advice.**

## Development process and use of AI

I chose to move this project from companies to industries, set the one question each page must answer and designed the verdict and score. Claude (Anthropic) was used as a research and coding assistant. It read the three Damodaran tables and wrote the generator, model, Excel, chart and dashboard code under my instructions. It also ran the tests, the Excel recalculation and parity check, and the browser check. I reviewed the sheets, the mappings and the wording before publishing.
