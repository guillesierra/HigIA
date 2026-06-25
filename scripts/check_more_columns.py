"""Check ALL columns of ATC XLSX files for DDD, PVPIVA, and additional metrics."""
import pandas as pd
from pathlib import Path

f = list(Path("data/raw/atc_xlsx").glob("*.xlsx"))[0]
df = pd.read_excel(str(f), header=None)
print(f"{f.name}: {df.shape} ({df.shape[1]} columns)")

# Show raw data for rows 3-10, all columns
for i in range(min(15, len(df))):
    row_vals = []
    for j in range(df.shape[1]):
        v = df.iloc[i, j]
        if str(v) not in ("nan", "None", ""):
            row_vals.append(f"  col{j}: {str(v)[:80]}")
    if row_vals:
        print(f"\nRow {i}:")
        print("\n".join(row_vals))

# Also check rows 8-20 (data rows) for patterns
print("\n=== Data rows (10-25) ===")
for i in range(8, min(25, len(df))):
    vals = []
    for j in range(df.shape[1]):
        v = df.iloc[i, j]
        s = str(v).strip()
        if s not in ("nan", "", "None"):
            vals.append(f"c{j}={s[:40]}")
    if vals:
        print(f"  Row{i}: {' | '.join(vals)}")

# Try SNS API directly
print("\n=== SNS Portal API ===")
import sys
sys.path.insert(0, "backend")
from app.scrapers.base import BaseScraper

class Api(BaseScraper):
    source_name="a"; base_url=""; start_url=""
    raw_subdir="api_test"; parser_version="a"
    def parse(self, limit=10, **kw): return []

a = Api(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

apis = [
    "https://pestadistico.inteligenciadegestion.sanidad.gob.es/publicoSNS/api/indicadores",
    "https://pestadistico.inteligenciadegestion.sanidad.gob.es/publicoSNS/api/datos?indicador=consumo_farmaceutico",
    "https://pestadistico.inteligenciadegestion.sanidad.gob.es/publicoSNS/D/consumo-farmaceutico-en-el-sns/consumo-en-recetas-medicas-sns/consumo-medicamentos-por-atc/nota-metodologica",
]
for u in apis:
    r = a.fetch_url(u)
    ct = (r.content_type or "")[:60]
    print(f"  [{r.status_code}] {ct} | {len(r.text or '')}B | {u}")
    if r.status_code == 200 and "json" in ct:
        import json
        d = json.loads(r.text)
        print(f"    Keys: {list(d.keys())[:10] if isinstance(d, dict) else f'list of {len(d)}'}")
