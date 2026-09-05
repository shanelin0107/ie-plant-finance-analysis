"""
02_generate_company.py
----------------------
Generate the SYNTHETIC company: Meridian Precision Manufacturing Co., a fictional
mid-size precision-components maker with multiple plants, offices and distribution
centers. Costs are grounded in the REAL Census anchors from 01_build_anchors.py:

  * Each plant is tied to a real NAICS manufacturing subsector, and its labor cost
    uses that subsector's REAL payroll-per-employee from CBP 2022.
  * Non-labor cost buckets are sized using the ASM/ACES cost-structure shares.

Everything else (headcounts, the specific sites, month-to-month movements, budgets
and the deliberate "stories" a cost analyst is meant to find) is invented and
reproducible via a fixed random seed. This file is clearly synthetic.

Outputs (Tableau-ready, tidy/long):
  data/processed/dim_site.csv          one row per site
  data/processed/fact_production.csv   month x plant, units produced
  data/processed/fact_site_costs.csv   month x site x cost_category, actual+budget
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROC = os.path.join(ROOT, "data", "processed")
rng = np.random.default_rng(20260905)

# --- real labor anchor -------------------------------------------------------
labor = pd.read_csv(os.path.join(PROC, "anchor_labor_by_subsector.csv"),
                    dtype={"naics3": str})
PAY_PER_EMP = dict(zip(labor.naics3, labor.payroll_per_emp_usd))  # real $/emp/yr

MONTHS = pd.date_range("2022-01-01", "2024-12-01", freq="MS")
REGION = {"OH": "Midwest", "MI": "Midwest", "IL": "Midwest",
          "TX": "South", "GA": "South", "NC": "South",
          "CA": "West", "AZ": "West",
          "MA": "Northeast", "PA": "Northeast"}

# --- site master -------------------------------------------------------------
# type: Plant / Office / DC (distribution center)
SITES = [
    # id     name                     type     city          st  naics3 head  sqft   tenure  opened
    ("P-TOL", "Toledo Metal Works",    "Plant", "Toledo",     "OH", "332", 420, 210000, "Owned",  2004),
    ("P-GRP", "Grand Rapids Machining","Plant", "Grand Rapids","MI","333", 360, 175000, "Owned",  2009),
    ("P-AUS", "Austin Electronics",    "Plant", "Austin",     "TX", "334", 300, 140000, "Leased", 2018),
    ("P-GRN", "Greenville Drivetrain", "Plant", "Greenville", "SC", "336", 480, 260000, "Owned",  2001),
    ("P-FRS", "Fresno Polymers",       "Plant", "Fresno",     "CA", "326", 240, 120000, "Leased", 2014),
    ("P-PHX", "Phoenix Precision",     "Plant", "Phoenix",    "AZ", "333", 210, 98000,  "Leased", 2020),
    ("D-MEM", "Memphis DC",            "DC",    "Memphis",    "TN", None,  95,  180000, "Leased", 2016),
    ("D-REN", "Reno DC",               "DC",    "Reno",       "NV", None,  70,  150000, "Leased", 2019),
    ("O-CHI", "Corporate HQ",          "Office","Chicago",    "IL", None,  180, 45000,  "Leased", 2011),
    ("O-BOS", "Boston R&D",            "Office","Boston",     "MA", None,  120, 38000,  "Leased", 2017),
    ("O-CLT", "Charlotte Sales",       "Office","Charlotte",  "NC", None,  55,  16000,  "Leased", 2021),
]
dim = pd.DataFrame(SITES, columns=[
    "site_id", "site_name", "site_type", "city", "state",
    "naics3", "headcount", "sqft", "tenure", "opened_year"])
dim["region"] = dim.state.map(REGION).fillna("South")
dim["subsector"] = dim.naics3.map(dict(zip(labor.naics3, labor.subsector)))
dim.to_csv(os.path.join(PROC, "dim_site.csv"), index=False)

# --- cost category taxonomy per site type -----------------------------------
# category -> (cost_group, base share of that site's monthly non-labor spend)
PLANT_CATS = {
    "Direct Labor":        ("COGS",     None),   # from real anchor
    "Indirect Labor":      ("COGS",     None),   # from real anchor
    "Raw Materials":       ("COGS",     0.46),
    "Consumables & Tooling":("COGS",    0.06),
    "Utilities":           ("Overhead", 0.10),
    "Maintenance & Repair":("Overhead", 0.09),
    "Depreciation":        ("Overhead", 0.09),
    "Facilities":          ("Overhead", 0.07),
    "Freight & Logistics": ("Overhead", 0.07),
    "IT & Systems":        ("Overhead", 0.03),
    "Other Overhead":      ("Overhead", 0.03),
}
OFFICE_CATS = {
    "Salaries & Benefits": ("G&A",      None),
    "Facilities":          ("G&A",      0.34),
    "IT & Systems":        ("G&A",      0.20),
    "Travel & Entertainment":("G&A",    0.16),
    "Professional Services":("G&A",     0.16),
    "Utilities":           ("G&A",      0.08),
    "Other G&A":           ("G&A",      0.06),
}
DC_CATS = {
    "Warehouse Labor":     ("Overhead", None),
    "Facilities":          ("Overhead", 0.30),
    "Freight & Logistics": ("Overhead", 0.30),
    "Equipment & Maint.":  ("Overhead", 0.14),
    "Utilities":           ("Overhead", 0.14),
    "IT & Systems":        ("Overhead", 0.07),
    "Other Overhead":      ("Overhead", 0.05),
}


def seasonal(month, kind):
    """Return a multiplicative seasonal factor."""
    m = month.month
    if kind == "utility":                       # summer + winter peaks
        return 1.0 + 0.28 * np.cos((m - 7) / 12 * 2 * np.pi) * -1 \
                   + 0.10 * np.cos((m - 1) / 12 * 2 * np.pi)
    if kind == "production":                     # Q4 push, summer dip
        return 1.0 + 0.08 * np.cos((m - 11) / 12 * 2 * np.pi)
    return 1.0


def inflation(month, annual=0.06):
    """Cumulative cost inflation since 2022-01 (materials/energy ran hot)."""
    dt = (month.year - 2022) * 12 + (month.month - 1)
    return (1 + annual / 12) ** dt


# --- production (plants only) ------------------------------------------------
prod_rows = []
plant_base_units = {"P-TOL": 42000, "P-GRP": 30000, "P-AUS": 18000,
                    "P-GRN": 55000, "P-FRS": 26000, "P-PHX": 15000}
for _, s in dim[dim.site_type == "Plant"].iterrows():
    base = plant_base_units[s.site_id]
    for month in MONTHS:
        t = (month.year - 2022) * 12 + (month.month - 1)
        trend = 1.0
        if s.site_id == "P-AUS":        # Austin ramping hard (new-ish plant)
            trend = 1.0 + 0.014 * t
        elif s.site_id == "P-GRP":      # Grand Rapids softening demand
            trend = 1.0 - 0.004 * t
        units = base * trend * seasonal(month, "production") * rng.normal(1, 0.04)
        prod_rows.append((month, s.site_id, max(int(units), 0)))
prod = pd.DataFrame(prod_rows, columns=["month", "site_id", "units_produced"])
prod.to_csv(os.path.join(PROC, "fact_production.csv"), index=False)
units_lookup = {(r.month, r.site_id): r.units_produced for r in prod.itertuples()}

# --- cost fact table ---------------------------------------------------------
rows = []


def add(month, s, cat, group, actual, budget):
    rows.append([month.strftime("%Y-%m-01"), s.site_id, s.site_name, s.site_type,
                 s.city, s.state, s.region, s.naics3, s.subsector,
                 int(s.headcount), int(s.sqft), cat, group,
                 round(actual, 2), round(budget, 2)])


for _, s in dim.iterrows():
    # annual merit raise on labor
    for month in MONTHS:
        yr_idx = month.year - 2022
        merit = (1.035) ** yr_idx
        t = (month.year - 2022) * 12 + (month.month - 1)

        if s.site_type == "Plant":
            monthly_pay = PAY_PER_EMP[s.naics3] / 12 * s.headcount * merit
            direct = monthly_pay * 0.72
            indirect = monthly_pay * 0.28
            units = units_lookup[(month, s.site_id)]
            # materials scale with production + inflation; ~ $ per unit
            mat_per_unit = {"332": 22, "333": 34, "334": 61, "336": 41, "326": 18}[s.naics3]
            materials = units * mat_per_unit * inflation(month)
            nonlabor_base = materials / PLANT_CATS["Raw Materials"][1]  # back out total non-labor

            cats = {}
            cats["Direct Labor"] = (direct, direct)
            cats["Indirect Labor"] = (indirect, indirect)
            for cat, (grp, share) in PLANT_CATS.items():
                if cat in ("Direct Labor", "Indirect Labor"):
                    continue
                base = nonlabor_base * share
                bud = base
                act = base
                if cat == "Raw Materials":
                    act = materials
                    bud = units * mat_per_unit * 1.03  # budget set at modest inflation
                elif cat == "Utilities":
                    act = base * seasonal(month, "utility") * inflation(month, 0.05)
                    bud = base * 1.02
                    if s.site_id == "P-FRS" and month.year == 2023 and month.month in (7, 8, 9):
                        act *= 1.45          # STORY: Fresno summer-2023 energy spike
                elif cat == "Maintenance & Repair":
                    bud = base
                    if s.site_id == "P-TOL":
                        act = base * (1.0 + 0.010 * t) * rng.normal(1.05, 0.05)  # STORY: aging Toledo line
                    else:
                        act = base * rng.normal(1.0, 0.06)
                elif cat == "Facilities":
                    act = bud = base
                    if s.tenure == "Owned":
                        act = bud = base * 0.6   # owned = lower cash facilities cost
                elif cat == "Depreciation":
                    act = bud = base            # deterministic
                else:
                    act = base * rng.normal(1.0, 0.05)
                # materials/scrap overrun story at Fresno
                if cat == "Raw Materials" and s.site_id == "P-FRS" and month >= pd.Timestamp("2023-06-01"):
                    act *= 1.07                   # STORY: scrap/yield problem
                cats[cat] = (act, bud)

            for cat, (act, bud) in cats.items():
                add(month, s, cat, PLANT_CATS[cat][0], act, bud)

        elif s.site_type == "Office":
            monthly_pay = (135000 if s.site_id == "O-BOS" else 118000) / 12 * s.headcount * merit
            gna_base = monthly_pay * 0.55   # non-salary G&A as fraction of salary
            add(month, s, "Salaries & Benefits", "G&A", monthly_pay, monthly_pay)
            for cat, (grp, share) in OFFICE_CATS.items():
                if cat == "Salaries & Benefits":
                    continue
                base = gna_base * share
                bud = base
                act = base * rng.normal(1.0, 0.05)
                if cat == "Facilities":
                    act = bud = base
                elif cat == "Utilities":
                    act = base * seasonal(month, "utility") * 0.9
                    bud = base
                elif cat == "Travel & Entertainment" and s.site_id == "O-CHI":
                    # STORY: HQ return-to-travel blows the T&E budget through 2024
                    ramp = 1.0 + (0.5 if month.year == 2024 else 0.15 if month.year == 2023 else 0.0)
                    act = base * ramp * rng.normal(1.05, 0.08)
                    bud = base * 1.05
                add(month, s, cat, "G&A", act, bud)

        elif s.site_type == "DC":
            monthly_pay = 58000 / 12 * s.headcount * merit
            base_total = monthly_pay / 0.42   # labor ~42% of DC spend
            add(month, s, "Warehouse Labor", "Overhead", monthly_pay, monthly_pay)
            for cat, (grp, share) in DC_CATS.items():
                if cat == "Warehouse Labor":
                    continue
                base = base_total * share
                bud = base
                act = base * rng.normal(1.0, 0.05)
                if cat == "Freight & Logistics":
                    act = base * inflation(month, 0.08) * rng.normal(1.0, 0.06)  # fuel-driven
                    bud = base * 1.03
                elif cat == "Facilities":
                    act = bud = base
                    if s.site_id == "D-MEM" and month >= pd.Timestamp("2023-07-01"):
                        act = bud = base * 0.85   # STORY: renegotiated Memphis lease (favorable)
                elif cat == "Utilities":
                    act = base * seasonal(month, "utility")
                    bud = base
                add(month, s, cat, "Overhead", act, bud)

cols = ["month", "site_id", "site_name", "site_type", "city", "state", "region",
        "naics3", "subsector", "headcount", "sqft", "cost_category", "cost_group",
        "actual_usd", "budget_usd"]
fact = pd.DataFrame(rows, columns=cols)
fact["variance_usd"] = (fact.actual_usd - fact.budget_usd).round(2)
fact["variance_pct"] = np.where(fact.budget_usd != 0,
                                (fact.variance_usd / fact.budget_usd * 100).round(2), 0)
fact.to_csv(os.path.join(PROC, "fact_site_costs.csv"), index=False)

# --- console summary ---------------------------------------------------------
tot_act = fact.actual_usd.sum()
tot_bud = fact.budget_usd.sum()
print(f"sites={len(dim)}  months={len(MONTHS)}  fact_rows={len(fact):,}")
print(f"total actual = ${tot_act/1e6:,.1f}M  budget = ${tot_bud/1e6:,.1f}M  "
      f"variance = ${(tot_act-tot_bud)/1e6:+,.1f}M ({(tot_act/tot_bud-1)*100:+.1f}%)")
print("\nby site_type (actual $M):")
print((fact.groupby("site_type").actual_usd.sum() / 1e6).round(1).to_string())
print("\nwrote dim_site.csv, fact_production.csv, fact_site_costs.csv ->", PROC)
