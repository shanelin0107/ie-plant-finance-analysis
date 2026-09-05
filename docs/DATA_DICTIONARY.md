# Data dictionary

Legend: **REAL** = downloaded from U.S. Census; **SYNTH** = generated (seeded);
**DERIVED** = computed from the columns.

## data/processed/anchor_labor_by_subsector.csv — REAL
U.S. Census County Business Patterns 2022 (`cbp22st.txt`), aggregated to national
3-digit manufacturing subsectors.

| column | type | source | notes |
|---|---|---|---|
| naics3 | str | REAL | 3-digit NAICS manufacturing subsector code |
| subsector | str | REAL | human label |
| establishments | int | REAL | # of establishments (physical sites) nationwide |
| employees | int | REAL | mid-March employment |
| annual_payroll_usd | int | REAL | total annual payroll, USD |
| payroll_per_emp_usd | float | DERIVED | payroll / employees — the labor anchor |

## data/processed/anchor_cost_structure.csv — REAL
Macro manufacturing cost structure (ASM 2021 shipments $6.1T; ACES 2022 capex
$314.3B; ASM long-run shares for materials/value-added/payroll).

| column | type | notes |
|---|---|---|
| metric | str | value_of_shipments, cost_of_materials, value_added, total_payroll, capital_expenditures |
| usd_national | int | national dollars |
| share_of_shipments | float | fraction of value of shipments |
| source_note | str | citation |

## data/processed/dim_site.csv — SYNTH
One row per site of the fictional company.

| column | type | notes |
|---|---|---|
| site_id | str | e.g. `P-TOL` (P=plant, O=office, D=DC) |
| site_name, city, state, region | str | location |
| site_type | str | Plant / Office / DC |
| naics3 | str | plants only — links to the real labor anchor |
| subsector | str | plants only |
| headcount | int | site headcount |
| sqft | int | site floor area |
| tenure | str | Owned / Leased |
| opened_year | int | |

## data/processed/fact_production.csv — SYNTH
| column | type | notes |
|---|---|---|
| month | date | month start |
| site_id | str | plants only |
| units_produced | int | monthly output (seasonal + trend + noise) |

## data/processed/fact_site_costs.csv — SYNTH + DERIVED (primary fact table)
One row per month × site × cost_category. Labor lines use the **real** per-employee
rate; everything else is modeled around the real cost-structure shares.

| column | type | notes |
|---|---|---|
| month | date | month start |
| site_id … subsector | | denormalized site attributes (see dim_site) |
| headcount, sqft | int | denormalized for easy Tableau ratios |
| cost_category | str | GL account (e.g. Raw Materials, Maintenance & Repair, Travel & Entertainment) |
| cost_group | str | COGS / Overhead / G&A |
| actual_usd | float | SYNTH — actual spend |
| budget_usd | float | SYNTH — planned spend |
| variance_usd | float | DERIVED — actual − budget (positive = over budget = unfavorable) |
| variance_pct | float | DERIVED — variance / budget × 100 |

## Deliberate signals to find (for reviewers)
These are intentionally seeded so the analysis has something to catch:
1. Toledo (P-TOL) Maintenance & Repair trending unfavorable (aging line).
2. Fresno (P-FRS) summer-2023 utilities spike + post-June-2023 materials/scrap overrun.
3. HQ (O-CHI) Travel & Entertainment over budget, worst in 2024.
4. Austin (P-AUS) unit cost improving as volume ramps.
5. Memphis DC (D-MEM) facilities step-down after a mid-2023 lease renegotiation.
6. Portfolio-wide materials inflation as the dominant unfavorable driver.
