"""
03_analysis.py
--------------
The Business-Analyst pass over the generated data: the views a manufacturing
cost / FP&A analyst actually builds. Prints findings to the console and writes
figures/ + a processed/findings summary that back the README and Tableau story.
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
os.makedirs(FIG, exist_ok=True)

fact = pd.read_csv(os.path.join(PROC, "fact_site_costs.csv"), parse_dates=["month"])
prod = pd.read_csv(os.path.join(PROC, "fact_production.csv"), parse_dates=["month"])

INK, GRID = "#1f2a37", "#e5e7eb"
FAV, UNFAV = "#2e7d5b", "#c0392b"      # favorable (under budget) / unfavorable
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK,
                     "axes.grid": True, "grid.color": GRID, "figure.dpi": 120})


def money(ax, axis="y"):
    fmt = mtick.FuncFormatter(lambda v, _: f"${v/1e6:,.1f}M")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


# === 1. Budget vs Actual by site ============================================
by_site = (fact.groupby(["site_id", "site_name", "site_type"])
           [["actual_usd", "budget_usd", "variance_usd"]].sum().reset_index())
by_site["variance_pct"] = by_site.variance_usd / by_site.budget_usd * 100
by_site = by_site.sort_values("variance_usd")

fig, ax = plt.subplots(figsize=(9, 5))
colors = [UNFAV if v > 0 else FAV for v in by_site.variance_usd]
ax.barh(by_site.site_name, by_site.variance_usd / 1e6, color=colors)
ax.axvline(0, color=INK, lw=1)
ax.set_title("3-Year Budget Variance by Site  (red = over budget)", weight="bold")
ax.set_xlabel("Actual − Budget ($M)")
for y, (v, p) in enumerate(zip(by_site.variance_usd, by_site.variance_pct)):
    ax.text(v/1e6 + (0.1 if v >= 0 else -0.1), y, f"{p:+.1f}%",
            va="center", ha="left" if v >= 0 else "right", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "01_variance_by_site.png")); plt.close(fig)

# === 2. Variance by cost category (company-wide driver bridge) ===============
by_cat = (fact.groupby("cost_category")[["variance_usd"]].sum()
          .sort_values("variance_usd").reset_index())
fig, ax = plt.subplots(figsize=(9, 5))
colors = [UNFAV if v > 0 else FAV for v in by_cat.variance_usd]
ax.barh(by_cat.cost_category, by_cat.variance_usd / 1e6, color=colors)
ax.axvline(0, color=INK, lw=1)
ax.set_title("Where the Variance Comes From — by Cost Category", weight="bold")
ax.set_xlabel("Actual − Budget ($M), 3-yr total")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "02_variance_by_category.png")); plt.close(fig)

# === 3. Cost per unit by plant over time ====================================
plant = fact[fact.site_type == "Plant"]
pcost = plant.groupby(["month", "site_id", "site_name"]).actual_usd.sum().reset_index()
pcost = pcost.merge(prod, on=["month", "site_id"])
pcost["cost_per_unit"] = pcost.actual_usd / pcost.units_produced
fig, ax = plt.subplots(figsize=(9, 5))
for name, g in pcost.groupby("site_name"):
    ax.plot(g.month, g.cost_per_unit, label=name, lw=1.6)
ax.set_title("Unit Cost Trend by Plant  ($ / unit produced)", weight="bold")
ax.set_ylabel("$ per unit"); ax.legend(fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "03_cost_per_unit.png")); plt.close(fig)

# === 4. Benchmark: $/headcount and $/sqft ===================================
bench = (fact.groupby(["site_id", "site_name", "site_type", "headcount", "sqft"])
         .actual_usd.sum().reset_index())
bench["annual_per_head"] = bench.actual_usd / 3 / bench.headcount
bench["annual_per_sqft"] = bench.actual_usd / 3 / bench.sqft
fig, ax = plt.subplots(figsize=(9, 5))
tcolor = {"Plant": "#2563eb", "Office": "#9333ea", "DC": "#f59e0b"}
for t, g in bench.groupby("site_type"):
    ax.scatter(g.annual_per_sqft, g.annual_per_head, s=g.headcount, alpha=.75,
               color=tcolor[t], label=t, edgecolor=INK, linewidth=.5)
    for _, r in g.iterrows():
        ax.annotate(r.site_name, (r.annual_per_sqft, r.annual_per_head),
                    fontsize=7, xytext=(4, 4), textcoords="offset points")
ax.set_title("Site Cost Efficiency  (bubble = headcount)", weight="bold")
ax.set_xlabel("Annual cost per sq ft"); ax.set_ylabel("Annual cost per head")
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1e3:,.0f}k"))
ax.legend(); fig.tight_layout()
fig.savefig(os.path.join(FIG, "04_efficiency_bubble.png")); plt.close(fig)

# === 5. Monthly actual vs budget trend ======================================
mtrend = fact.groupby("month")[["actual_usd", "budget_usd"]].sum().reset_index()
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(mtrend.month, mtrend.budget_usd, label="Budget", color=INK, ls="--", lw=1.4)
ax.plot(mtrend.month, mtrend.actual_usd, label="Actual", color=UNFAV, lw=1.8)
ax.fill_between(mtrend.month, mtrend.budget_usd, mtrend.actual_usd,
                where=mtrend.actual_usd >= mtrend.budget_usd, color=UNFAV, alpha=.12)
money(ax); ax.set_title("Company Monthly Spend: Actual vs Budget", weight="bold")
ax.legend(); fig.tight_layout()
fig.savefig(os.path.join(FIG, "05_actual_vs_budget_trend.png")); plt.close(fig)

# === 6. Findings ============================================================
print("=" * 68)
print("KEY FINDINGS — Meridian Precision Manufacturing (FY2022–2024)")
print("=" * 68)
tot_a, tot_b = fact.actual_usd.sum(), fact.budget_usd.sum()
print(f"Portfolio: ${tot_a/1e6:,.1f}M actual vs ${tot_b/1e6:,.1f}M budget "
      f"({(tot_a/tot_b-1)*100:+.1f}%, ${(tot_a-tot_b)/1e6:+.1f}M).\n")

worst = by_site.iloc[-1]
print(f"1. Biggest overspend: {worst.site_name} "
      f"${worst.variance_usd/1e6:+.1f}M ({worst.variance_pct:+.1f}%).")

# Toledo maintenance trend
tol = fact[(fact.site_id == "P-TOL") & (fact.cost_category == "Maintenance & Repair")]
tol_y = tol.groupby(tol.month.dt.year).variance_usd.sum() / 1e3
print(f"2. Toledo Maintenance variance climbing: "
      + ", ".join(f"{y} ${v:+.0f}k" for y, v in tol_y.items()) + " (aging line).")

# Fresno utilities spike + scrap
frs = fact[(fact.site_id == "P-FRS")]
frs_u = frs[(frs.cost_category == "Utilities") & (frs.month.dt.year == 2023)
            & (frs.month.dt.month.isin([7, 8, 9]))].variance_usd.sum() / 1e3
print(f"3. Fresno summer-2023 energy spike: ${frs_u:+.0f}k unfavorable in Q3 alone.")

# HQ T&E
te = fact[(fact.site_id == "O-CHI") & (fact.cost_category == "Travel & Entertainment")]
te24 = te[te.month.dt.year == 2024].variance_usd.sum() / 1e3
print(f"4. HQ Travel & Entertainment 2024 overspend: ${te24:+.0f}k (return-to-travel).")

# Austin unit-cost improvement
aus = pcost[pcost.site_id == "P-AUS"].sort_values("month")
print(f"5. Austin unit cost improved {aus.cost_per_unit.iloc[0]:.0f} -> "
      f"{aus.cost_per_unit.iloc[-1]:.0f} $/unit as volume ramped (scale economies).")

# Memphis lease win
mem = fact[(fact.site_id == "D-MEM") & (fact.cost_category == "Facilities")]
before = mem[mem.month < "2023-07-01"].actual_usd.mean()
after = mem[mem.month >= "2023-07-01"].actual_usd.mean()
print(f"6. Memphis DC lease renegotiation cut facilities ${before/1e3:.0f}k -> "
      f"${after/1e3:.0f}k/mo (-{(1-after/before)*100:.0f}%).")

bench.sort_values("annual_per_head").to_csv(
    os.path.join(PROC, "site_efficiency_benchmark.csv"), index=False)
by_site.to_csv(os.path.join(PROC, "budget_variance_by_site.csv"), index=False)
print(f"\nWrote 5 figures -> {FIG}")
print("Wrote budget_variance_by_site.csv, site_efficiency_benchmark.csv")
