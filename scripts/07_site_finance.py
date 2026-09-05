"""
07_site_finance.py
------------------
The SITE-FINANCE view: treat every location (plant, office, DC) as a financial
unit and answer the questions a *site finance* analyst owns, across the whole
portfolio rather than deep inside one plant:

  * each site's OpEx composition / mini-P&L (cost structure differs by site type)
  * corporate-overhead ALLOCATION: push HQ cost onto operating sites by headcount
    to get each site's FULLY-LOADED cost and fully-loaded cost per head
  * facilities efficiency: owned vs leased, cost per sq ft

Outputs:
  data/processed/site_pnl.csv          fully-loaded cost per site
  figures/10_site_opex_composition.png
  figures/11_fully_loaded_cost_per_head.png
  figures/12_facilities_owned_vs_leased.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROC = os.path.join(ROOT, "data", "processed")
FIG = os.path.join(ROOT, "figures")

costs = pd.read_csv(os.path.join(PROC, "fact_site_costs.csv"), parse_dates=["month"])
dim = pd.read_csv(os.path.join(PROC, "dim_site.csv"))

INK, GRID = "#1f2a37", "#e5e7eb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK,
                     "axes.grid": True, "grid.color": GRID, "figure.dpi": 120})
TCOLOR = {"Plant": "#2563eb", "Office": "#9333ea", "DC": "#f59e0b"}

# --- roll GL accounts up into P&L buckets -----------------------------------
BUCKET = {
    "Direct Labor": "Labor", "Indirect Labor": "Labor", "Salaries & Benefits": "Labor",
    "Warehouse Labor": "Labor",
    "Raw Materials": "Materials", "Consumables & Tooling": "Materials",
    "Facilities": "Facilities",
    "Utilities": "Utilities",
    "Maintenance & Repair": "Maintenance", "Equipment & Maint.": "Maintenance",
    "Freight & Logistics": "Logistics",
    "Depreciation": "Depreciation",
    "IT & Systems": "Other G&A/IT", "Professional Services": "Other G&A/IT",
    "Travel & Entertainment": "Other G&A/IT", "Other Overhead": "Other G&A/IT",
    "Other G&A": "Other G&A/IT",
}
BUCKET_ORDER = ["Labor", "Materials", "Facilities", "Utilities", "Maintenance",
                "Logistics", "Depreciation", "Other G&A/IT"]
BCOLORS = dict(zip(BUCKET_ORDER, plt.cm.tab20(np.linspace(0, 1, len(BUCKET_ORDER)))))

costs["bucket"] = costs.cost_category.map(BUCKET)
site_bucket = (costs.groupby(["site_id", "site_name", "site_type", "bucket"])
               .actual_usd.sum().reset_index())

# === 1. Site OpEx composition (100% stacked) ================================
piv = site_bucket.pivot_table(index=["site_type", "site_name"], columns="bucket",
                              values="actual_usd", fill_value=0)
piv = piv[[b for b in BUCKET_ORDER if b in piv.columns]]
pct = piv.div(piv.sum(axis=1), axis=0) * 100
pct = pct.sort_index(level=0)
labels = [f"{name}" for (stype, name) in pct.index]

fig, ax = plt.subplots(figsize=(10, 5.5))
left = np.zeros(len(pct))
for b in pct.columns:
    ax.barh(range(len(pct)), pct[b], left=left, color=BCOLORS[b], label=b)
    left += pct[b].values
ax.set_yticks(range(len(pct))); ax.set_yticklabels(labels, fontsize=8)
ax.set_xlim(0, 100); ax.set_xlabel("% of site OpEx")
ax.set_title("Site OpEx Composition — cost structure by site (mini-P&L)", weight="bold")
ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12))
# site-type brackets on the left
for stype in pct.index.get_level_values(0).unique():
    ys = [i for i, (s, _) in enumerate(pct.index) if s == stype]
    ax.text(-8, np.mean(ys), stype, rotation=90, va="center", ha="center",
            fontsize=9, weight="bold", color=TCOLOR[stype])
fig.tight_layout(); fig.savefig(os.path.join(FIG, "10_site_opex_composition.png")); plt.close(fig)

# === 2. Corporate allocation -> fully-loaded cost per head ===================
# Corporate HQ (O-CHI) is corporate overhead; allocate it across the other
# (operating) sites. Classic site-finance "fully-loaded" view. Base = share of
# direct cost (standard for G&A), so the corporate load varies by site instead of
# being a flat per-head number.
annual = costs.groupby("site_id").actual_usd.sum() / 3  # avg annual direct cost
dim = dim.set_index("site_id")
corp_id = "O-CHI"
corp_pool = annual[corp_id]
op_sites = [s for s in annual.index if s != corp_id]
head = dim.loc[op_sites, "headcount"]
base = annual[op_sites]
alloc = corp_pool * base / base.sum()          # allocated corporate $ by cost share

pnl = pd.DataFrame({
    "site_name": dim.loc[op_sites, "site_name"],
    "site_type": dim.loc[op_sites, "site_type"],
    "headcount": head,
    "direct_annual_cost": annual[op_sites],
    "allocated_corporate": alloc,
})
pnl["fully_loaded_cost"] = pnl.direct_annual_cost + pnl.allocated_corporate
pnl["direct_per_head"] = pnl.direct_annual_cost / pnl.headcount
pnl["loaded_per_head"] = pnl.fully_loaded_cost / pnl.headcount
pnl = pnl.sort_values("loaded_per_head")
pnl.to_csv(os.path.join(PROC, "site_pnl.csv"))

fig, ax = plt.subplots(figsize=(10, 5.5))
y = range(len(pnl))
ax.barh(y, pnl.direct_per_head / 1e3, color="#2563eb", label="Direct site cost / head")
ax.barh(y, pnl.allocated_corporate / pnl.headcount / 1e3,
        left=pnl.direct_per_head / 1e3, color="#c0392b",
        label="Allocated corporate / head")
ax.set_yticks(list(y)); ax.set_yticklabels(pnl.site_name, fontsize=8)
ax.set_xlabel("Annual cost per head ($k)")
ax.set_title("Fully-Loaded Cost per Head by Site  (direct + allocated corporate)",
             weight="bold")
ax.legend(fontsize=8)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v:,.0f}k"))
fig.tight_layout(); fig.savefig(os.path.join(FIG, "11_fully_loaded_cost_per_head.png")); plt.close(fig)

# === 3. Facilities efficiency: owned vs leased ==============================
fac = costs[costs.cost_category == "Facilities"].groupby("site_id").actual_usd.sum() / 3
fdf = pd.DataFrame({
    "site_name": dim.site_name, "site_type": dim.site_type,
    "tenure": dim.tenure, "sqft": dim.sqft,
    "facilities_annual": fac}).dropna()
fdf["cost_per_sqft"] = fdf.facilities_annual / fdf.sqft
fdf = fdf.sort_values("cost_per_sqft")
fig, ax = plt.subplots(figsize=(9, 5.5))
mark = {"Owned": "o", "Leased": "s"}
for ten, g in fdf.groupby("tenure"):
    ax.barh(g.site_name, g.cost_per_sqft,
            color=["#2e7d5b" if ten == "Owned" else "#c0392b"] * len(g),
            label=ten, alpha=.85)
ax.set_xlabel("Facilities cost per sq ft / yr")
ax.set_title("Facilities Cost per Sq Ft — Owned vs Leased", weight="bold")
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(FIG, "12_facilities_owned_vs_leased.png")); plt.close(fig)

# === Findings ===============================================================
print("=" * 68)
print("SITE-FINANCE FINDINGS")
print("=" * 68)
print(f"Corporate HQ pool allocated to sites: ${corp_pool/1e6:,.1f}M/yr, "
      f"spread over {len(op_sites)} operating sites by direct-cost share.\n")
print("Fully-loaded cost per head (site finance's 'true' site cost):")
for _, r in pnl.sort_values("loaded_per_head", ascending=False).iterrows():
    print(f"  {r.site_name:24} {r.site_type:6} "
          f"direct ${r.direct_per_head/1e3:6.0f}k  + corp ${r.allocated_corporate/r.headcount/1e3:4.0f}k "
          f"= loaded ${r.loaded_per_head/1e3:6.0f}k")
own = fdf[fdf.tenure == "Owned"].cost_per_sqft.mean()
leas = fdf[fdf.tenure == "Leased"].cost_per_sqft.mean()
print(f"\nFacilities: owned avg ${own:,.0f}/sqft vs leased ${leas:,.0f}/sqft "
      f"({leas/own:.1f}x) — the lease vs own trade-off in cash terms.")
print(f"\nWrote figures 10-12 -> {FIG}")
print("Wrote site_pnl.csv")
