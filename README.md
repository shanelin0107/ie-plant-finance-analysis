# Multi-Site Manufacturing Spend — a cost analyst's teardown

A manufacturing **Finance / FP&A** analysis of a multi-site company: where the money
goes across **plants, offices and distribution centers**, where **actual beats or
busts budget**, and which sites are actually efficient once you normalize for what
they make.

The company is fictional, but its costs are **anchored to real U.S. Census data**, so
the numbers behave like a real portfolio.

> **Data honesty.** This is a *hybrid* dataset, and the seam is labeled on purpose:
> - **Real (downloaded, reproducible):** establishment counts and labor cost per
>   employee for every manufacturing subsector, from **Census County Business
>   Patterns 2022**; macro cost structure from **ASM 2021** ($6.1T shipments) and
>   **ACES 2022** ($314.3B capex); and real **commodity prices (FRED PPI)** for
>   steel, plastic resin, semiconductors, electrical parts and diesel that drive the
>   procurement module. See [`scripts/01_build_anchors.py`](scripts/01_build_anchors.py)
>   and [`scripts/04_fetch_ppi.py`](scripts/04_fetch_ppi.py).
> - **Synthetic (generated, seeded):** the specific company "Meridian Precision
>   Manufacturing," its 11 sites, and 36 months of actual-vs-budget cost lines. Each
>   plant is tied to a real NAICS subsector and pays its **real** per-employee labor
>   rate; the movements and the problems to find are invented. See
>   [`scripts/02_generate_company.py`](scripts/02_generate_company.py).
>
> Nothing real is fabricated; nothing synthetic is dressed up as real.

This is project #3 in an IE/operations portfolio, extending the story from **line
efficiency (MES)** → **energy (BDG2)** → **the financial layer**: the same plants,
now read through the general ledger.

---

## The business question

A cost analyst sitting in the corporate office has one recurring job: **explain the
variance.** Every month the portfolio spends ~$37M; the review deck has to answer

1. Are we over or under budget, and **which sites and cost drivers** caused it?
2. Which plants are **truly inefficient** vs. just making expensive products?
3. What's a **trend** (structural, act now) vs. **noise** (leave it alone)?

The dataset and dashboard are built to answer exactly those.

---

## Headline findings — Meridian Precision Manufacturing (FY2022–2024)

**Portfolio: $1,337.8M actual vs $1,313.7M budget → +1.8% ($+24.1M over).**
A calm-looking 1.8% at the top hides very different stories underneath.

**1. The overspend is a materials-inflation story, not a discipline story.**
Of the cost categories, **Raw Materials drove +$15.8M** of unfavorable variance,
Utilities +$3.2M, Maintenance +$1.9M — while overhead ran on plan. Input-cost
inflation, not loose spending, is the headline.

![Variance by category](figures/02_variance_by_category.png)

**2. One plant's maintenance is quietly compounding.**
Toledo Metal Works (owned, opened 2004) runs its Maintenance & Repair variance
**+$213k → +$489k → +$945k** across 2022→2024 — a classic aging-asset signature that
a % -of-total view hides. This is a capital-vs-repair decision waiting to be made.

![Variance by site](figures/01_variance_by_site.png)

**3. "Cost per head" lies unless you normalize for product mix.**
Raw annual cost/head runs from **$117k (Fresno)** to **$237k (Austin)** — but Austin
builds electronics (NAICS 334, a real ~$100k/employee payroll subsector) while Fresno
molds plastics (NAICS 326). The efficiency ranking only becomes fair after you anchor
each plant to its subsector — which is exactly why the real Census labor rates matter.

![Site efficiency](figures/04_efficiency_bubble.png)

**4. Unit economics move the right way where volume ramps.**
Austin's cost per unit improves as production scales, even against materials inflation
— the scale-economy signal survives. Grand Rapids, with softening volume, drifts the
other way.

![Unit cost by plant](figures/03_cost_per_unit.png)

**5. Two clean wins worth copying.**
HQ **Travel & Entertainment** blew through budget by **+$1.1M in 2024** (return-to-
travel) — a policy lever. And the **Memphis DC lease renegotiation cut facilities cost
−11%** mid-2023 — proof the portfolio *can* bend cost when someone acts.

![Actual vs budget trend](figures/05_actual_vs_budget_trend.png)

---

---

## Procurement & supplier spend — the buyer's view

The other half of a manufacturing analyst's job is **managed spend**: $357.2M flows
through 16 suppliers, and the direct-material portion **reconciles to the penny with
the Raw Materials cost line** above ($256.3M) — the two modules are one company, not
two spreadsheets. Prices are driven by **real FRED commodity indexes**.

**6. Spend is Pareto-concentrated — manage the vital few.**
**9 of 16 suppliers = 80% of spend**; Great Lakes Steel alone is $63.4M. That's where
category strategy and QBRs should go; the long tail is a consolidation target.

![Supplier spend Pareto](figures/06_spend_pareto.png)

**7. Purchase Price Variance splits exactly along the real commodity cycle.**
Net PPV is **−$19.7M favorable**, but it's two stories: **steel −$12.5M, freight
−$6.3M, plastic −$4.7M favorable** (those PPIs fell from their 2022 peaks), while
**electrical/electronic +$2.2M and MRO +$2.2M ran unfavorable** (electrical PPI rose
+16%). That unfavorable electronics line is the same pressure showing up as Austin's
material cost on the finance side — one root cause, two reports.

![PPV by commodity](figures/07_ppv_by_commodity.png)

**8. Single-source risk is concentrated in semiconductors.**
Semiconductors carry an **HHI of 6,800** (anything >2,500 is "highly concentrated"):
**Formosa Semiconductor is single-source on $21.8M**. Favorable price today doesn't
offset a supply-continuity risk on the highest-value input — a dual-source
recommendation writes itself.

![Supplier concentration](figures/09_supplier_concentration.png)

**9. $45.6M (13%) is maverick spend, bought ~6% over contract.**
Off-contract buying — mostly tail MRO — pays a measurable price penalty vs the
on-contract rate. Routing it onto existing agreements is a clean, self-funding savings
play, on top of the **$11.3M already realized** vs prior-year baseline.

![Realized savings](figures/08_savings_trend.png)

---

## Why this matters (IE / Finance reading)

- **Variance analysis is triage, not accounting.** The point isn't the $24.1M number;
  it's separating the *controllable* (T&E policy, a lease, a maintenance-vs-capital
  call) from the *market* (materials inflation you hedge, not scold).
- **Benchmarks need the right denominator.** $/head and $/sqft only compare sites
  fairly after normalizing for subsector — the reason this project spends effort on
  real Census labor anchors instead of a flat assumption.
- **Trends beat snapshots.** Toledo maintenance and HQ travel are invisible in a
  single month and obvious across 36. The dashboard is built time-first.

---

## Repo layout

```
ie-plant-finance-analysis/
├── scripts/
│   ├── 01_build_anchors.py         # REAL Census anchors -> anchor_labor/cost CSVs
│   ├── 02_generate_company.py      # synthetic company grounded in the anchors
│   ├── 03_analysis.py              # cost / budget-variance views + figures
│   ├── 04_fetch_ppi.py             # REAL FRED commodity PPI -> anchor_ppi.csv
│   ├── 05_generate_procurement.py  # supplier spend, reconciled to Raw Materials
│   └── 06_procurement_analysis.py  # PPV, savings, concentration, maverick + figures
├── data/
│   ├── raw/                    # cbp22st.txt (89 MB, gitignored, re-downloadable)
│   └── processed/              # anchors + dim_site/supplier, fact_* tables
├── figures/                    # 9 analysis charts (PNG)
├── TABLEAU_GUIDE.md            # build the interactive dashboard from the CSVs
└── docs/DATA_DICTIONARY.md     # every column, and which are real vs synthetic
```

## Reproduce

```bash
pip install -r requirements.txt

# 1. real anchor (downloads the keyless Census CBP flat file, ~12 MB zip)
curl -L -o data/raw/cbp22st.zip \
  https://www2.census.gov/programs-surveys/cbp/datasets/2022/cbp22st.zip
unzip -o data/raw/cbp22st.zip -d data/raw/
python scripts/01_build_anchors.py

# 2. generate the company (seeded -> identical every run)
python scripts/02_generate_company.py

# 3. cost / budget-variance analysis + figures
python scripts/03_analysis.py

# 4. procurement module: real commodity PPI -> supplier spend -> analysis
python scripts/04_fetch_ppi.py            # downloads real FRED PPI (keyless)
python scripts/05_generate_procurement.py # reconciles to Raw Materials
python scripts/06_procurement_analysis.py
```

## Tableau
`fact_site_costs.csv` is a tidy long table built for Tableau — see
[`TABLEAU_GUIDE.md`](TABLEAU_GUIDE.md) for the sheet-by-sheet build (KPI row, variance
waterfall, unit-cost trend, efficiency scatter, and a site/category filter).
