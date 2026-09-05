"""
06_procurement_analysis.py
--------------------------
The procurement/BA pass: spend Pareto, PPV by commodity, realized savings,
supplier concentration & single-source risk, and maverick (off-contract) spend.
Writes figures + prints findings.
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

f = pd.read_csv(os.path.join(PROC, "fact_procurement.csv"), parse_dates=["month"])
ppi = pd.read_csv(os.path.join(PROC, "anchor_ppi.csv"), parse_dates=["month"])

INK, GRID = "#1f2a37", "#e5e7eb"
FAV, UNFAV, ACC = "#2e7d5b", "#c0392b", "#2563eb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK,
                     "axes.grid": True, "grid.color": GRID, "figure.dpi": 120})


# === 1. Spend Pareto by supplier ============================================
sp = f.groupby("supplier_name").actual_spend.sum().sort_values(ascending=False)
cum = sp.cumsum() / sp.sum() * 100
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(range(len(sp)), sp.values / 1e6, color=ACC)
ax.set_xticks(range(len(sp))); ax.set_xticklabels(sp.index, rotation=45, ha="right", fontsize=7)
ax.set_ylabel("Spend ($M)")
ax2 = ax.twinx(); ax2.plot(range(len(sp)), cum.values, color=UNFAV, marker="o", ms=3)
ax2.axhline(80, color=INK, ls="--", lw=1); ax2.set_ylabel("Cumulative %"); ax2.set_ylim(0, 105)
ax2.grid(False)
n80 = int((cum <= 80).sum()) + 1
ax.set_title(f"Supplier Spend Pareto — {n80} of {len(sp)} suppliers = 80% of spend",
             weight="bold")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "06_spend_pareto.png")); plt.close(fig)

# === 2. PPV by commodity =====================================================
ppv = f.groupby("commodity").ppv_usd.sum().sort_values() / 1e6
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(ppv.index, ppv.values, color=[FAV if v < 0 else UNFAV for v in ppv.values])
ax.axvline(0, color=INK, lw=1)
ax.set_title("Purchase Price Variance by Commodity  (green = favorable / paid below standard)",
             weight="bold")
ax.set_xlabel("PPV ($M) = (actual − standard price) × qty")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "07_ppv_by_commodity.png")); plt.close(fig)

# === 3. Realized savings over time ==========================================
sav = f.groupby(f.month.dt.to_period("Q")).savings_usd.sum() / 1e6
sav.index = sav.index.to_timestamp()
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(sav.index, sav.values, width=70, color=[FAV if v >= 0 else UNFAV for v in sav.values])
ax.axhline(0, color=INK, lw=1)
ax.set_title("Realized Savings vs Prior-Year Baseline (quarterly)", weight="bold")
ax.set_ylabel("Savings ($M)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "08_savings_trend.png")); plt.close(fig)

# === 4. Supplier concentration by commodity (single-source risk) ============
def hhi(series):
    s = series / series.sum()
    return (s ** 2).sum() * 10000  # 0..10000

conc = []
for comm, g in f[f.category == "Direct Materials"].groupby("commodity"):
    by_sup = g.groupby("supplier_name").actual_spend.sum()
    top = by_sup.max() / by_sup.sum() * 100
    ss = g[g.is_single_source].actual_spend.sum() / g.actual_spend.sum() * 100
    conc.append((comm, hhi(by_sup), top, ss, g.actual_spend.sum() / 1e6))
conc = pd.DataFrame(conc, columns=["commodity", "hhi", "top_share", "single_src_share", "spend_m"])
conc = conc.sort_values("hhi", ascending=False)
fig, ax = plt.subplots(figsize=(9, 5))
colors = [UNFAV if h > 2500 else (ACC if h > 1500 else FAV) for h in conc.hhi]
ax.barh(conc.commodity, conc.hhi, color=colors)
ax.axvline(2500, color=INK, ls="--", lw=1)
ax.text(2550, -0.4, "HHI 2500 = highly concentrated", fontsize=8)
ax.set_title("Direct-Material Supplier Concentration (HHI) — single-source risk", weight="bold")
ax.set_xlabel("Herfindahl-Hirschman Index (spend share²)")
for y, (h, t) in enumerate(zip(conc.hhi, conc.top_share)):
    ax.text(h + 40, y, f"top {t:.0f}%", va="center", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "09_supplier_concentration.png")); plt.close(fig)

# === 5. On-contract vs maverick spend =======================================
mav = f.groupby("on_contract").actual_spend.sum() / 1e6
# price penalty measured within MRO, where on- and off-contract buy the same base good
mro = f[f.commodity == "MRO"].assign(
    paid_vs_market=lambda d: d.actual_unit_price / (d.market_ppi_index / 100))
mav_price = mro.groupby("on_contract").paid_vs_market.mean()

# === Findings ================================================================
print("=" * 68)
print("PROCUREMENT FINDINGS — Meridian Precision Manufacturing")
print("=" * 68)
tot = f.actual_spend.sum()
print(f"Total managed spend ${tot/1e6:,.1f}M across {f.supplier_name.nunique()} suppliers.")
print(f"  Direct Materials ${f[f.category=='Direct Materials'].actual_spend.sum()/1e6:,.1f}M | "
      f"MRO ${f[f.category=='MRO'].actual_spend.sum()/1e6:,.1f}M | "
      f"Logistics ${f[f.category=='Logistics'].actual_spend.sum()/1e6:,.1f}M\n")

print(f"1. Spend is concentrated: {n80} of {len(sp)} suppliers = 80% of spend "
      f"(top supplier {sp.index[0]} ${sp.iloc[0]/1e6:.1f}M).")

print(f"2. Total PPV ${f.ppv_usd.sum()/1e6:+.1f}M. By commodity:")
for c, v in ppv.items():
    print(f"     {c:24} ${v:+.1f}M  ({'favorable' if v<0 else 'UNFAVORABLE'})")

print(f"3. Realized savings ${f.savings_usd.sum()/1e6:+.1f}M vs prior-year baseline "
      f"(steel/plastic deflation + re-sourcing captured).")

risk = conc.iloc[0]
print(f"4. Single-source risk: {risk.commodity} HHI {risk.hhi:.0f}, top supplier {risk.top_share:.0f}%. "
      f"Formosa Semiconductor is single-source on ${f[f.is_single_source].actual_spend.sum()/1e6:.1f}M.")

on = mav.get(True, 0); off = mav.get(False, 0)
penalty = (mav_price.get(False, 1) / mav_price.get(True, 1) - 1) * 100
print(f"5. Maverick spend: ${off:.1f}M off-contract ({off/(on+off)*100:.0f}% of spend), "
      f"paid ~{penalty:.0f}% above contract rates -> savings leakage.")

conc.to_csv(os.path.join(PROC, "supplier_concentration.csv"), index=False)
sp.to_frame("spend_usd").to_csv(os.path.join(PROC, "supplier_spend.csv"))
print(f"\nWrote figures 06-09 -> {FIG}")
print("Wrote supplier_concentration.csv, supplier_spend.csv")
