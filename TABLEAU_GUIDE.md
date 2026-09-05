# Tableau Public build guide

Goal: turn the tidy CSVs into an interactive **Site Spend & Budget Variance** dashboard
and publish a public link for the portfolio. All inputs are in `data/processed/`
(produced by the three scripts).

## 0. Data sources
Connect these CSVs. `fact_site_costs.csv` is the primary source; relate the others by
the keys noted (Tableau *relationships*, not physical joins).

- `fact_site_costs.csv` — **primary**. One row per month × site × cost_category, with
  `actual_usd`, `budget_usd`, `variance_usd`, `variance_pct`.
- `dim_site.csv` — one row per site (type, region, tenure, headcount, sqft). Relate on `site_id`.
- `fact_production.csv` — month × plant units. Relate on `site_id` + `month`.

Create two calculated fields up front:
- `Variance $` = `SUM([actual_usd]) - SUM([budget_usd])`
- `Favorable?` = `IF [Variance $] <= 0 THEN "Favorable" ELSE "Unfavorable" END`
  (diverging color: green = favorable/under, red = unfavorable/over)

## 1. KPI row (fact_site_costs)
Four BAN tiles:
- `SUM([actual_usd])` → **$1.34B actual (3 yr)**
- `SUM([budget_usd])` → **$1.31B budget**
- `Variance $` → **+$24.1M**, formatted with sign; color by `Favorable?`
- `Variance $ / SUM([budget_usd])` → **+1.8%**

## 2. Variance by cost category — the driver bar (fact_site_costs)
Bar. Rows = `cost_category`, Columns = `Variance $`, Color = `Favorable?`.
Sort descending by variance. This is the "materials +$15.8M" chart — the first thing
leadership should see.

## 3. Variance by site (fact_site_costs + dim_site)
Horizontal bar. Rows = `site_name`, Columns = `Variance $`, Color = `Favorable?`.
Add `site_type` to Detail; expose it as a **dashboard filter** (Plant/Office/DC).

## 4. Unit cost trend (fact_site_costs + fact_production)
Line. Columns = `MONTH([month])` (continuous), Rows =
`SUM([actual_usd]) / SUM([units_produced])`, Color = `site_name`. Filter to
`site_type = "Plant"`. This exposes Austin's scale improvement and Grand Rapids' drift.

## 5. Efficiency scatter (fact_site_costs + dim_site)
Scatter. Columns = `SUM([actual_usd]) / SUM([headcount]) / 3` (annual cost/head),
Rows = `SUM([actual_usd]) / SUM([sqft]) / 3` (annual cost/sqft), Size = `headcount`,
Color = `site_type`, Label = `site_name`.
> Add a caption: cost/head is **not** comparable across subsectors — Austin (NAICS 334)
> is high because electronics labor really costs ~$100k/employee in Census data.

## 6. Actual vs budget over time (fact_site_costs)
Dual line, `MONTH([month])` on Columns; `SUM([actual_usd])` and `SUM([budget_usd])`.
Shade the gap where actual > budget.

## 7. Assemble the dashboard
- KPI row across the top.
- Row 2: category-driver bar (left) + variance-by-site bar (right).
- Row 3: unit-cost trend (left) + efficiency scatter (right).
- Global filters: `site_type`, `region`, `MONTH(month)` range, `cost_group`.
- Add a text box crediting the real anchors: *"Labor & establishment counts: U.S.
  Census CBP 2022. Cost structure: ASM 2021 / ACES 2022. Company data synthetic."*

## 8. Procurement dashboard (second dashboard, `fact_procurement.csv` + `dim_supplier.csv`)
A separate tab for the "buyer" story. Relate `fact_procurement` to `dim_supplier` on `supplier_id`.

- **Spend Pareto:** bar of `SUM([actual_spend])` by `supplier_name` (sorted desc) +
  a running-total-% line (Table Calc → Running Total → % of Total). Reference line at 80%.
- **PPV by commodity:** bar, Rows = `commodity`, Columns = `SUM([ppv_usd])`, color by
  sign (green = favorable/negative). This is the steel-favorable / electrical-unfavorable split.
- **Realized savings:** bar of `SUM([savings_usd])` by `QUARTER([month])`.
- **Supplier concentration:** bar of spend share by supplier within each `commodity`
  (or load `supplier_concentration.csv` for the HHI directly). Flag `is_single_source`.
- **Maverick spend:** stacked bar `SUM([actual_spend])` by `category`, color = `on_contract`.
- Global filters: `commodity`, `category`, `tier`, `country`, `MONTH(month)`.
- Callout: prices are driven by **real FRED PPI**; direct-material spend **reconciles
  to the Raw Materials cost line** in the finance dashboard.

## 9. Publish
Server → Tableau Public → Save. Copy the link into the portfolio and the repo.
