"""
01_build_anchors.py
--------------------
Build the REAL cost/labor anchors that ground the synthetic company dataset.

Source of truth (all public, U.S. Census Bureau):
  * County Business Patterns (CBP) 2022, state x NAICS file `cbp22st.txt`
      https://www2.census.gov/programs-surveys/cbp/datasets/2022/cbp22st.zip
    -> real establishment counts, employment, and ANNUAL PAYROLL by
       manufacturing subsector (NAICS 3-digit). Gives us true labor cost
       per employee, which differs a lot across subsectors.
  * Annual Survey of Manufactures (ASM) 2021 headline totals + Annual Capital
    Expenditures Survey (ACES) 2022 -> macro cost-structure ratios
    (materials / value added / capex share of shipments). ASM was
    discontinued after survey year 2021; figures are hard-coded here WITH
    citations rather than re-downloaded, because Census now gates the API
    behind a key while the CBP flat file stays keyless.

Outputs (committed, small):
  data/processed/anchor_labor_by_subsector.csv
  data/processed/anchor_cost_structure.csv
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "cbp22st.txt")
OUT = os.path.join(ROOT, "data", "processed")
os.makedirs(OUT, exist_ok=True)

SUBSECTOR_NAMES = {
    "311": "Food", "312": "Beverage & Tobacco", "313": "Textile Mills",
    "314": "Textile Product Mills", "315": "Apparel", "316": "Leather",
    "321": "Wood Product", "322": "Paper", "323": "Printing",
    "324": "Petroleum & Coal", "325": "Chemical", "326": "Plastics & Rubber",
    "327": "Nonmetallic Mineral", "331": "Primary Metal",
    "332": "Fabricated Metal", "333": "Machinery",
    "334": "Computer & Electronic", "335": "Electrical Equipment",
    "336": "Transportation Equipment", "337": "Furniture",
    "339": "Miscellaneous (Medical, etc.)",
}


def build_labor_anchor():
    """Aggregate CBP manufacturing subsectors to the national level."""
    agg = {k: {"estab": 0, "emp": 0, "payroll_k": 0} for k in SUBSECTOR_NAMES}
    with open(RAW, newline="") as fh:
        for r in csv.DictReader(fh):
            n = r["naics"]
            # 3-digit manufacturing subsector rows look like "332///", lfo '-' = all
            if r["lfo"] == "-" and len(n) == 6 and n.endswith("///") and n[0] == "3":
                key = n[:3]
                if key not in agg:
                    continue
                try:
                    agg[key]["estab"] += int(r["est"])
                    agg[key]["emp"] += int(r["emp"])
                    agg[key]["payroll_k"] += int(r["ap"])  # ap is $1,000s
                except ValueError:
                    pass

    rows = []
    for key, name in SUBSECTOR_NAMES.items():
        a = agg[key]
        emp = a["emp"]
        payroll = a["payroll_k"] * 1000  # -> dollars
        rows.append({
            "naics3": key,
            "subsector": name,
            "establishments": a["estab"],
            "employees": emp,
            "annual_payroll_usd": payroll,
            "payroll_per_emp_usd": round(payroll / emp, 0) if emp else 0,
        })
    rows.sort(key=lambda x: x["naics3"])

    path = os.path.join(OUT, "anchor_labor_by_subsector.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tot_emp = sum(r["employees"] for r in rows)
    tot_pay = sum(r["annual_payroll_usd"] for r in rows)
    print(f"[labor] {len(rows)} subsectors | "
          f"{sum(r['establishments'] for r in rows):,} establishments | "
          f"{tot_emp:,} employees | ${tot_pay/1e9:,.1f}B payroll | "
          f"avg ${tot_pay/tot_emp:,.0f}/emp")
    print(f"        -> {path}")
    return path


def build_cost_structure_anchor():
    """
    Macro manufacturing cost structure, expressed as share of value of shipments.
    Anchored to published Census aggregates (ASM 2021 + ACES 2022).
    """
    VALUE_OF_SHIPMENTS_2021 = 6.1e12   # ASM 2021 press release: $6.1 trillion
    CAPEX_2022 = 314.3e9               # ACES 2022: $314.3B manufacturing capex
    # ASM long-run structure of manufacturing (share of value of shipments):
    #   cost of materials ~0.57, value added ~0.46, payroll ~0.14.
    # These are used only to size non-labor cost buckets in the synthetic model;
    # labor itself comes from the real CBP per-employee figures above.
    rows = [
        ("value_of_shipments", VALUE_OF_SHIPMENTS_2021, 1.000,
         "ASM 2021 press release ($6.1T)"),
        ("cost_of_materials", 0.57 * VALUE_OF_SHIPMENTS_2021, 0.570,
         "ASM long-run materials share of shipments"),
        ("value_added", 0.46 * VALUE_OF_SHIPMENTS_2021, 0.460,
         "ASM long-run value-added share"),
        ("total_payroll", 0.14 * VALUE_OF_SHIPMENTS_2021, 0.140,
         "ASM long-run payroll share (cross-check vs CBP)"),
        ("capital_expenditures", CAPEX_2022, round(CAPEX_2022 / VALUE_OF_SHIPMENTS_2021, 3),
         "ACES 2022 ($314.3B)"),
    ]
    path = os.path.join(OUT, "anchor_cost_structure.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "usd_national", "share_of_shipments", "source_note"])
        for name, usd, share, note in rows:
            w.writerow([name, int(usd), share, note])
    print(f"[cost ] national manufacturing cost structure -> {path}")
    return path


if __name__ == "__main__":
    if not os.path.exists(RAW):
        raise SystemExit(
            f"Missing {RAW}\nDownload it first:\n"
            "  curl -L -o data/raw/cbp22st.zip "
            "https://www2.census.gov/programs-surveys/cbp/datasets/2022/cbp22st.zip\n"
            "  unzip data/raw/cbp22st.zip -d data/raw/")
    build_labor_anchor()
    build_cost_structure_anchor()
    print("done.")
