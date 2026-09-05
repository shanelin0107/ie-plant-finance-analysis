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
>   **ACES 2022** ($314.3B capex). See [`scripts/01_build_anchors.py`](scripts/01_build_anchors.py).
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
│   ├── 01_build_anchors.py     # REAL Census anchors -> data/processed/anchor_*.csv
│   ├── 02_generate_company.py  # synthetic company grounded in the anchors
│   └── 03_analysis.py          # BA views + figures + findings
├── data/
│   ├── raw/                    # cbp22st.txt (89 MB, gitignored, re-downloadable)
│   └── processed/              # anchors + dim_site, fact_production, fact_site_costs
├── figures/                    # 5 analysis charts (PNG)
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

# 3. analysis + figures
python scripts/03_analysis.py
```

## Tableau
`fact_site_costs.csv` is a tidy long table built for Tableau — see
[`TABLEAU_GUIDE.md`](TABLEAU_GUIDE.md) for the sheet-by-sheet build (KPI row, variance
waterfall, unit-cost trend, efficiency scatter, and a site/category filter).
