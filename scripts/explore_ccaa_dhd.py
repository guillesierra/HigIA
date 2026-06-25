"""Explore CCAA_INGESA and ATC for regional DHD/PVP/DDD data + reparse XLSX for PVPIVA columns."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
import urllib3
urllib3.disable_warnings()

BASE = "https://www.sanidad.gob.es"

class E(BaseScraper):
    source_name = "e"; base_url = BASE; start_url = ""
    raw_subdir = "explore_ccaa"; parser_version = "e"
    def parse(self, limit=10, **kw): return []

s = E(delay_seconds=0.2, verify_ssl=False, respect_robots=False)

print("=== 1. CCAA_INGESA link exploration ===")
# Check if there are subpages with data
urls = [
    f"{BASE}/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/2024/home.htm",
    f"{BASE}/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/home.htm",
]
for u in urls:
    r = s.fetch_url(u)
    if r.status_code == 200 and r.text:
        soup = BeautifulSoup(r.text, "html.parser")
        print(f"\n{u}")
        # Show all links
        for a in soup.select("a[href]")[:30]:
            href = a.get("href", "").strip()
            text = a.get_text(" ", strip=True)[:80]
            full = s.absolutize(href, u)
            ext = Path(href.split("?")[0]).suffix.lower()
            print(f"  [{ext or 'page'}] {text[:60]} -> {full[:120]}")

print("\n=== 2. Try CCAA XLSX pattern ===")
# Try common patterns for CCAA-level data
months = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
          "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]
for year in [2024, 2023, 2022]:
    for month in months[:1]:  # Just test one month each
        xlsx_url = f"{BASE}/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/docs/{month}_{year}_CCAA.xlsx"
        dl = s.fetch_url(xlsx_url, ".xlsx")
        if dl.status_code == 200:
            print(f"  FOUND: {xlsx_url}")

print("\n=== 3. CCAA_INGESA docs directory exploration ===")
# Try to list the docs directory
docs_url = f"{BASE}/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/docs/"
r = s.fetch_url(docs_url)
if r.status_code in (200, 403):
    print(f"  Docs dir: {r.status_code} ({len(r.text or '')}B)")

print("\n=== 4. Re-parse ATC XLSX for PVPIVA (amount) and more DDD columns ===")
import pandas as pd
xlsx_dir = Path("data/raw/atc_xlsx")
files = sorted(xlsx_dir.glob("*.xlsx"))
print(f"Files: {len(files)}")

# Check one file deeper - look at all rows and columns
f = files[0]
df = pd.read_excel(str(f), header=None)
print(f"\n{f.name}: {df.shape}")
# Show all non-null values to understand full structure
for i in range(len(df)):
    row = [str(v)[:50] for v in df.iloc[i].values if str(v) != "nan"]
    if row: print(f"  {i}: {row}")

# Check if any sheets have PVPIVA data
# Also check sheets from files with "ATC2" pattern (might have different structure)
for f in files:
    if "ATC2" in f.name.upper():
        df2 = pd.read_excel(str(f), header=None)
        print(f"\n{f.name}: {df2.shape}")
        for i in range(min(10, len(df2))):
            row = [str(v)[:60] for v in df2.iloc[i].values if str(v) != "nan"]
            if row: print(f"  {i}: {row}")
        break
