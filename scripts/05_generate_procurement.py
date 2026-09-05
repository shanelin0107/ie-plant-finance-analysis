"""
05_generate_procurement.py
--------------------------
Add the PROCUREMENT / supplier-spend layer for Meridian Precision Manufacturing.
Grounded in two real anchors:
  * anchor_ppi.csv   -> real FRED commodity prices drive unit prices & PPV
  * fact_site_costs  -> plants' real-anchored Raw Materials actuals are the control
                        total; direct-material purchases RECONCILE to them.

Concepts a procurement/BA analyst reports on, all present here:
  - spend by supplier / commodity / category (Pareto tail)
  - Purchase Price Variance (PPV) = (actual price - standard price) x qty
  - realized savings vs prior-year baseline
  - supplier concentration / single-source risk
  - on-contract vs off-contract ("maverick") spend

Outputs (Tableau-ready):
  data/processed/dim_supplier.csv
  data/processed/fact_procurement.csv
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROC = os.path.join(ROOT, "data", "processed")
rng = np.random.default_rng(4242)

dim_site = pd.read_csv(os.path.join(PROC, "dim_site.csv"), dtype={"naics3": str})
costs = pd.read_csv(os.path.join(PROC, "fact_site_costs.csv"), parse_dates=["month"])
ppi = pd.read_csv(os.path.join(PROC, "anchor_ppi.csv"), parse_dates=["month"])
ppi_idx = ppi.pivot(index="month", columns="commodity", values="ppi_index_2022_01")

# --- suppliers ---------------------------------------------------------------
# name, commodity, category, country, tier, single_source, contract
SUPPLIERS = [
    # Direct materials
    ("SUP-STL1", "Great Lakes Steel Co.",   "Steel & Metal", "Direct Materials", "USA",    "Strategic",     False, True),
    ("SUP-STL2", "Rio Grande Metals",       "Steel & Metal", "Direct Materials", "Mexico", "Preferred",     False, True),
    ("SUP-STL3", "Keystone Alloy Supply",   "Steel & Metal", "Direct Materials", "USA",    "Transactional", False, False),
    ("SUP-RES1", "Gulf Coast Polymers",     "Plastic Resin", "Direct Materials", "USA",    "Strategic",     False, True),
    ("SUP-RES2", "Pacific Resin Traders",   "Plastic Resin", "Direct Materials", "Taiwan", "Preferred",     False, True),
    ("SUP-SEM1", "Formosa Semiconductor",   "Semiconductors","Direct Materials", "Taiwan", "Strategic",     True,  True),
    ("SUP-SEM2", "Anchor Microelectronics", "Semiconductors","Direct Materials", "USA",    "Preferred",     False, True),
    ("SUP-ELE1", "Shenzhen Circuit Works",  "Electrical/Electronic","Direct Materials","China","Strategic", False, True),
    ("SUP-ELE2", "Lone Star Connectors",    "Electrical/Electronic","Direct Materials","USA","Preferred",   False, True),
    ("SUP-ELE3", "Vertex Components",       "Electrical/Electronic","Direct Materials","USA","Transactional",False,False),
    # MRO
    ("SUP-MRO1", "Fastline Industrial MRO", "MRO", "MRO", "USA", "Preferred",     False, True),
    ("SUP-MRO2", "Toolcraft Supply",        "MRO", "MRO", "USA", "Transactional", False, False),
    ("SUP-MRO3", "Sunbelt Facility Parts",  "MRO", "MRO", "USA", "Transactional", False, False),
    # Freight
    ("SUP-FRT1", "Continental Freightways", "Freight (Diesel)", "Logistics", "USA", "Strategic",   False, True),
    ("SUP-FRT2", "RedRiver Logistics",      "Freight (Diesel)", "Logistics", "USA", "Preferred",   False, True),
    ("SUP-FRT3", "QuickHaul Carriers",      "Freight (Diesel)", "Logistics", "USA", "Transactional",False,False),
]
dim_supplier = pd.DataFrame(SUPPLIERS, columns=[
    "supplier_id", "supplier_name", "commodity", "category", "country",
    "tier", "is_single_source", "contract_on_file"])
dim_supplier.to_csv(os.path.join(PROC, "dim_supplier.csv"), index=False)

by_comm = {c: dim_supplier[dim_supplier.commodity == c].supplier_id.tolist()
           for c in dim_supplier.commodity.unique()}
sup_meta = dim_supplier.set_index("supplier_id").to_dict("index")

# supplier price premium vs market (strategic negotiate down; transactional pay up)
TIER_PREMIUM = {"Strategic": 0.965, "Preferred": 1.00, "Transactional": 1.06}

# --- plant commodity mix (direct materials) ---------------------------------
PLANT_MIX = {
    "P-TOL": {"Steel & Metal": .75, "Electrical/Electronic": .15, "Plastic Resin": .10},
    "P-GRP": {"Steel & Metal": .50, "Electrical/Electronic": .40, "Plastic Resin": .10},
    "P-PHX": {"Steel & Metal": .45, "Electrical/Electronic": .45, "Plastic Resin": .10},
    "P-AUS": {"Semiconductors": .50, "Electrical/Electronic": .40, "Plastic Resin": .10},
    "P-GRN": {"Steel & Metal": .55, "Electrical/Electronic": .30, "Plastic Resin": .15},
    "P-FRS": {"Plastic Resin": .80, "Steel & Metal": .10, "Electrical/Electronic": .10},
}
# share of a commodity's spend that goes to each of its suppliers (dominant + tail)
SPLIT = {
    "Steel & Metal":         {"SUP-STL1": .60, "SUP-STL2": .28, "SUP-STL3": .12},
    "Plastic Resin":         {"SUP-RES1": .65, "SUP-RES2": .35},
    "Semiconductors":        {"SUP-SEM1": .80, "SUP-SEM2": .20},   # single-source heavy
    "Electrical/Electronic": {"SUP-ELE1": .55, "SUP-ELE2": .30, "SUP-ELE3": .15},
}

rows = []


def add(month, site_id, sup, comm, qty, market, std_price, act_price, baseline, on_contract):
    m = sup_meta[sup]
    actual = qty * act_price
    standard = qty * std_price
    rows.append([
        month.strftime("%Y-%m-01"), site_id, sup, m["supplier_name"], comm,
        m["category"], m["country"], m["tier"], bool(m["is_single_source"]),
        bool(on_contract), int(qty), round(market, 2),
        round(std_price, 4), round(act_price, 4), round(baseline, 4),
        round(actual, 2), round(standard, 2),
        round(actual - standard, 2),          # PPV (unfavorable if +)
        round((baseline - act_price) * qty, 2)  # savings vs baseline (favorable if +)
    ])


# --- direct materials: reconcile to each plant's Raw Materials actual ---------
rm = costs[costs.cost_category == "Raw Materials"][["month", "site_id", "actual_usd"]]
rm = rm.set_index(["month", "site_id"]).actual_usd.to_dict()

# nominal unit prices per commodity (arbitrary $/unit at 2022-01 index=100)
BASE_PRICE = {"Steel & Metal": 1.10, "Plastic Resin": 0.85,
              "Semiconductors": 4.20, "Electrical/Electronic": 2.30}

for site_id, mix in PLANT_MIX.items():
    for month in ppi_idx.index:
        total_rm = rm.get((month, site_id))
        if total_rm is None:
            continue
        year = month.year
        for comm, wt in mix.items():
            comm_spend = total_rm * wt
            market = ppi_idx.loc[month, comm]
            base = BASE_PRICE[comm]
            # standard price: classic standard-cost roll = prior calendar year's
            # average market. Rising commodities (electronics) then show unfavorable
            # PPV; falling ones (steel) show favorable — the real story.
            prev = ppi_idx[ppi_idx.index.year == year - 1][comm]
            std_market = prev.mean() if len(prev) else ppi_idx[ppi_idx.index.year == year][comm].mean()
            std_price = base * std_market / 100
            for sup, sh in SPLIT[comm].items():
                prem = TIER_PREMIUM[sup_meta[sup]["tier"]]
                act_price = base * market / 100 * prem * rng.normal(1, 0.015)
                # STORY: re-source Gulf Coast Polymers -> Pacific mid-2023 lowers plastic price
                if comm == "Plastic Resin" and sup == "SUP-RES2" and month >= pd.Timestamp("2023-07-01"):
                    act_price *= 0.93
                baseline = base * (ppi_idx.loc[pd.Timestamp(year-1,1,1), comm]
                                   if pd.Timestamp(year-1,1,1) in ppi_idx.index else market) / 100 * prem
                spend = comm_spend * sh
                qty = max(spend / act_price, 1)
                on_contract = bool(sup_meta[sup]["contract_on_file"])
                add(month, site_id, sup, comm, qty, market, std_price, act_price, baseline, on_contract)

# --- MRO spend: shared, ~ tied to Consumables+Maintenance, with maverick leakage
mro_pool = costs[costs.cost_category.isin(["Consumables & Tooling", "Maintenance & Repair"])]
mro_by = mro_pool.groupby(["month", "site_id"]).actual_usd.sum() * 0.45  # ~45% is bought-in parts
for (month, site_id), amt in mro_by.items():
    market = ppi_idx.loc[month, "Electrical/Electronic"]  # MRO parts track equipment PPI
    # 70% on-contract to Fastline, rest split to transactional (maverick, higher price)
    for sup, sh, on in [("SUP-MRO1", .70, True), ("SUP-MRO2", .18, False), ("SUP-MRO3", .12, False)]:
        prem = TIER_PREMIUM[sup_meta[sup]["tier"]]
        act_price = 1.0 * market / 100 * prem * rng.normal(1, 0.02)
        prev = ppi_idx[ppi_idx.index.year == month.year - 1]["Electrical/Electronic"]
        std_market = prev.mean() if len(prev) else market
        std_price = 1.0 * std_market / 100
        baseline = 1.0 * market / 100  # baseline = market (no negotiated edge on MRO)
        qty = max(amt * sh / act_price, 1)
        add(month, site_id, sup, "MRO", qty, market, std_price, act_price, baseline, on)

# --- Freight: tied to Freight & Logistics line, driven by real diesel PPI -----
frt = costs[costs.cost_category == "Freight & Logistics"].groupby(["month", "site_id"]).actual_usd.sum()
for (month, site_id), amt in frt.items():
    market = ppi_idx.loc[month, "Freight (Diesel)"]
    for sup, sh, on in [("SUP-FRT1", .55, True), ("SUP-FRT2", .30, True), ("SUP-FRT3", .15, False)]:
        prem = TIER_PREMIUM[sup_meta[sup]["tier"]]
        act_price = 1.0 * market / 100 * prem * rng.normal(1, 0.02)
        prev = ppi_idx[ppi_idx.index.year == month.year - 1]["Freight (Diesel)"]
        std_market = prev.mean() if len(prev) else market
        std_price = 1.0 * std_market / 100
        baseline = 1.0 * market / 100 * prem
        qty = max(amt * sh / act_price, 1)
        add(month, site_id, sup, "Freight (Diesel)", qty, market, std_price, act_price, baseline, on)

cols = ["month", "site_id", "supplier_id", "supplier_name", "commodity", "category",
        "country", "tier", "is_single_source", "on_contract", "qty", "market_ppi_index",
        "standard_unit_price", "actual_unit_price", "baseline_unit_price",
        "actual_spend", "standard_spend", "ppv_usd", "savings_usd"]
fact = pd.DataFrame(rows, columns=cols)
fact.to_csv(os.path.join(PROC, "fact_procurement.csv"), index=False)

# --- reconciliation check ----------------------------------------------------
dm = fact[fact.category == "Direct Materials"].actual_spend.sum()
rm_total = costs[costs.cost_category == "Raw Materials"].actual_usd.sum()
print(f"suppliers={len(dim_supplier)}  procurement_rows={len(fact):,}")
print(f"total procurement spend = ${fact.actual_spend.sum()/1e6:,.1f}M")
print(f"  direct materials = ${dm/1e6:,.1f}M  vs Raw Materials cost line ${rm_total/1e6:,.1f}M "
      f"(reconcile diff {abs(dm-rm_total)/rm_total*100:.2f}%)")
print(f"total PPV = ${fact.ppv_usd.sum()/1e6:+,.1f}M   "
      f"realized savings = ${fact.savings_usd.sum()/1e6:+,.1f}M")
print("wrote dim_supplier.csv, fact_procurement.csv")
