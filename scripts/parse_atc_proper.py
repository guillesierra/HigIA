"""Parse ATC XLSX files with their specific structure and merge with hospital data."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pandas as pd

def _safe_float(val):
    if val is None: return None
    try:
        s = str(val).strip()
        if s in ("", "nan", "None", "-"): return None
        return float(s)
    except (ValueError, TypeError): return None

MONTH_MAP = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}

records = []
xlsx_dir = Path("data/raw/atc_xlsx")
files = sorted(xlsx_dir.glob("*.xlsx"))

for f in files:
    fn = f.name.upper()
    
    # Extract year and month from filename
    year_match = re.search(r'(20[12]\d)', fn)
    if not year_match:
        continue
    year = int(year_match.group(1))
    
    month = None
    for mname, mnum in MONTH_MAP.items():
        if mname in fn:
            month = mnum
            break
    
    try:
        df = pd.read_excel(str(f), header=None)
    except Exception:
        continue
    
    if df.shape[0] < 8 or df.shape[1] < 4:
        continue
    
    # Find header row (contains "GRUPO ATC")
    header_row = None
    for i in range(min(10, len(df))):
        row_text = " ".join(str(v) for v in df.iloc[i].values if str(v) != "nan")
        if "GRUPO ATC" in row_text or "CODIGO ATC" in row_text:
            header_row = i
            break
    
    if header_row is None:
        continue
    
    # Data rows start after header
    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]
        first_cell = str(row.iloc[0]).strip()
        
        # Skip empty rows, header rows, title rows
        if not first_cell or first_cell == "nan" or first_cell.startswith("CONSUMO") or first_cell.startswith("GRUPO"):
            continue
        
        atc_code_or_name = first_cell
        
        # Try to extract values from columns
        # Structure: col0=ATC, col1=monthly_envases, col2=monthly_DHD, col3=acc_envases, col4=acc_DHD, ...
        monthly_envases = _safe_float(row.iloc[1]) if len(row) > 1 else None
        monthly_dhd = _safe_float(row.iloc[2]) if len(row) > 2 else None
        acc_envases = _safe_float(row.iloc[3]) if len(row) > 3 else None
        acc_dhd = _safe_float(row.iloc[4]) if len(row) > 4 else None
        
        if monthly_envases is None and monthly_dhd is None:
            continue
        
        records.append({
            "record_type": "consumption",
            "source_name": "Ministerio de Sanidad - Consumo por ATC (datos reales SNS)",
            "source_url": f"https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/ATC/{year}.htm",
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": "sanidad-atc-v2-0.8",
            "year": year,
            "month": month,
            "geography": "Spain",
            "geography_type": "country",
            "sector": "Recetas SNS ATC",
            "atc_code": atc_code_or_name if re.match(r'^[A-Z]\d', atc_code_or_name.upper()) else None,
            "drug_name": atc_code_or_name if not re.match(r'^[A-Z]\d', atc_code_or_name.upper()) else None,
            "active_ingredient": None,
            "packages": monthly_envases,
            "ddd": None,
            "dhd": monthly_dhd,
            "amount_pvpiva": None,
            "notes": f"Acc envases: {acc_envases}, Acc DHD: {acc_dhd}" if acc_envases or acc_dhd else None,
        })

    if len(records) % 1000 == 0:
        print(f"  Parsed {len(records)} records... ({f.name})")

print(f"\nATC records: {len(records)}")

# Merge with existing hospital data
outdir = Path("data/processed/sanidad_real")
outdir.mkdir(parents=True, exist_ok=True)
epath = outdir / "latest_normalized.json"

existing = []
if epath.exists():
    existing = json.loads(epath.read_text(encoding="utf-8"))

# Remove old ATC records (keep only hospital + community + any non-ATC)
kept = [r for r in existing if r.get("sector") != "Recetas SNS ATC"]
print(f"Removed {len(existing) - len(kept)} old ATC records")
print(f"Kept {len(kept)} hospital/community records")

all_recs = kept + records
epath.write_text(json.dumps(all_recs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"Final: {len(all_recs)} records ({len(kept)} existing + {len(records)} new ATC)")

# Verify
atc_with_dhd = [r for r in records if r.get("dhd") is not None]
atc_with_packs = [r for r in records if r.get("packages") is not None]
print(f"ATC with DHD: {len(atc_with_dhd)}, with packages: {len(atc_with_packs)}")
if atc_with_dhd:
    print(f"Sample DHD: {atc_with_dhd[0]}")
if atc_with_packs:
    print(f"Sample packs: {atc_with_packs[0]}")
