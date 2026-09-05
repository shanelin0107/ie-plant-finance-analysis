"""
04_fetch_ppi.py
---------------
Download REAL commodity price signals from FRED (St. Louis Fed) — keyless CSV —
to anchor the procurement module's prices and price variance (PPV). These are the
actual Producer Price Indexes a buyer at an electronics contract manufacturer
watches (steel chassis, plastic enclosures, semiconductors, electrical parts,
and diesel for freight).

Output (committed, small):
  data/processed/anchor_ppi.csv   month x commodity, real PPI level + index(=100 @ 2022-01)
"""
import io
import os
import urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROC = os.path.join(ROOT, "data", "processed")
os.makedirs(PROC, exist_ok=True)

# commodity label -> (FRED series id, description)
SERIES = {
    "Steel & Metal":     ("WPU101",          "PPI: Iron and steel"),
    "Plastic Resin":     ("WPU066",          "PPI: Plastic resins and materials"),
    "Semiconductors":    ("PCU334413334413", "PPI: Semiconductors"),
    "Electrical/Electronic": ("WPU117",      "PPI: Electrical machinery and equipment"),
    "Freight (Diesel)":  ("WPU057303",       "PPI: No. 2 diesel fuel"),
}
COSD, COED = "2021-06-01", "2024-12-01"


def fetch(series_id):
    url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
           f"&cosd={COSD}&coed={COED}")
    with urllib.request.urlopen(url, timeout=30) as r:
        raw = r.read().decode()
    df = pd.read_csv(io.StringIO(raw))
    df.columns = ["month", "ppi"]
    df["month"] = pd.to_datetime(df["month"])
    df["ppi"] = pd.to_numeric(df["ppi"], errors="coerce")
    return df.dropna()


frames = []
for label, (sid, desc) in SERIES.items():
    df = fetch(sid)
    base = df.loc[df.month == "2022-01-01", "ppi"]
    base = float(base.iloc[0]) if len(base) else float(df.ppi.iloc[0])
    df["commodity"] = label
    df["series_id"] = sid
    df["ppi_index_2022_01"] = (df.ppi / base * 100).round(2)
    frames.append(df)
    print(f"{label:22} {sid:16} {len(df):>3} mo  "
          f"{df.ppi.iloc[0]:.1f} -> {df.ppi.iloc[-1]:.1f}  "
          f"({(df.ppi.iloc[-1]/df.ppi.iloc[0]-1)*100:+.0f}% over window)")

out = pd.concat(frames, ignore_index=True)[
    ["month", "commodity", "series_id", "ppi", "ppi_index_2022_01"]]
out.to_csv(os.path.join(PROC, "anchor_ppi.csv"), index=False)
print(f"\nwrote {len(out)} rows -> {os.path.join(PROC, 'anchor_ppi.csv')}")
print("source: FRED (fred.stlouisfed.org), public, keyless")
