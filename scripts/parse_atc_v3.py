"""REPARSE ATC XLSX - fix year extraction, ATC code mapping, DHD cleanup."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import pandas as pd

MONTH_MAP = {"ENERO":1,"FEBRERO":2,"MARZO":3,"ABRIL":4,"MAYO":5,"JUNIO":6,
             "JULIO":7,"AGOSTO":8,"SEPTIEMBRE":9,"OCTUBRE":10,"NOVIEMBRE":11,"DICIEMBRE":12}

def safe_float(val):
    if val is None: return None
    try:
        s = str(val).strip()
        if s in ("","nan","None","-"): return None
        return float(s)
    except: return None

records = []
xlsx_dir = Path("data/raw/atc_xlsx")
files = sorted(xlsx_dir.glob("*.xlsx"))
print(f"Files: {len(files)}")

SKIP_FIRST_COLS = {"codigo","código","cod","cod.","grupo atc1","grupo atc2","grupo atc","total","subtotal","total nacional"}

for fi, f in enumerate(files):
    fn = f.name.upper()
    
    # Extract year: match _2024_ or _2023_ pattern (NOT the timestamp prefix)
    ym = re.search(r'_(20[12]\d)_', fn)
    if not ym:
        ym = re.search(r'(20[12]\d)', fn.replace(str(f.stat().st_mtime)[:4], ""))
    if not ym:
        continue
    year = int(ym.group(1))
    
    month = None
    for mn, mv in MONTH_MAP.items():
        if mn in fn: month = mv; break
    
    try: df = pd.read_excel(str(f), header=None)
    except: continue
    
    if df.shape[0] < 8: continue
    
    # Find header row
    header_row = None
    for i in range(min(12, len(df))):
        row_t = " ".join(str(v) for v in df.iloc[i].values if str(v) != "nan")
        if "GRUPO ATC" in row_t or "CODIGO ATC" in row_t or "SUBGRUPO" in row_t:
            header_row = i
            break
    if header_row is None: continue
    
    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]
        first = str(row.iloc[0]).strip()
        
        if not first or first == "nan": continue
        first_lower = first.lower().strip()
        # Skip header/metadata rows
        if any(w in first_lower for w in SKIP_FIRST_COLS): continue
        if first_lower.startswith("consumo"): continue
        if first_lower.startswith("grupo"): continue
        if first_lower.startswith("nota"): continue
        
        # Determine if first cell is an ATC code or a drug name
        is_atc = bool(re.match(r'^[A-Z]\d{2}', first.upper()))
        atc_code = first if is_atc else None
        drug_name = first if not is_atc else None
        
        # Try to get DHD from col 2 (monthly DHD) or col 4 (acc DHD)
        dhd_raw = safe_float(row.iloc[2]) if len(row) > 2 else None
        dhd = dhd_raw
        
        # If DHD > 100, try accumulated DHD column (might be col 4)
        if dhd is not None and dhd > 100:
            dhd2 = safe_float(row.iloc[4]) if len(row) > 4 else None
            if dhd2 is not None and 0 < dhd2 < 100:
                dhd = dhd2
            elif len(row) > 5:
                # Try alternative columns for files with different layouts
                for ci in [1,3,5,7]:
                    alt = safe_float(row.iloc[ci]) if len(row) > ci else None
                    if alt is not None and 0.001 < alt < 200:
                        dhd = alt
                        break
        
        # Also try to get packages
        packages = None
        for ci in [1, 3, 5, 7, 9]:
            val = safe_float(row.iloc[ci]) if len(row) > ci else None
            if val is not None and val > 0.01 and val < 100000:  # packages in thousands
                packages = val
                break
        
        if dhd is None and packages is None: continue
        if dhd is not None and (dhd <= 0.001 or dhd > 200): continue
        
        records.append({
            "record_type": "consumption",
            "source_name": "Ministerio de Sanidad - Consumo por ATC (datos reales SNS)",
            "source_url": f"https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/ATC/{year}.htm",
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": "sanidad-atc-v3-0.8",
            "year": year, "month": month,
            "geography": "Spain", "geography_type": "country",
            "sector": "Recetas SNS ATC",
            "atc_code": atc_code,
            "drug_name": drug_name,
            "active_ingredient": None,
            "packages": packages,
            "ddd": None,
            "dhd": dhd,
            "amount_pvpiva": None,
            "notes": None,
        })

print(f"\nATC records: {len(records)}")

# Show stats
yrs = {}; [yrs.update({r['year']:yrs.get(r['year'],0)+1}) for r in records]
print(f"Years: {dict(sorted(yrs.items()))}")

with_atc = sum(1 for r in records if r['atc_code'])
with_drug = sum(1 for r in records if r['drug_name'])
with_dhd = sum(1 for r in records if r['dhd'] is not None)
with_packs = sum(1 for r in records if r['packages'] is not None)
print(f"ATC codes: {with_atc}, Drug names: {with_drug}, DHD: {with_dhd}, Packages: {with_packs}")

if with_dhd:
    dhds = [r['dhd'] for r in records if r['dhd'] is not None]
    print(f"DHD: {min(dhds):.2f} - {max(dhds):.2f}, avg {sum(dhds)/len(dhds):.2f}")

# Merge with hospital
outdir = Path("data/processed/sanidad_real")
outdir.mkdir(parents=True, exist_ok=True)
epath = outdir / "latest_normalized.json"
existing = json.loads(epath.read_text(encoding="utf-8")) if epath.exists() else []
kept = [r for r in existing if r.get("sector") != "Recetas SNS ATC"]
all_recs = kept + records
epath.write_text(json.dumps(all_recs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"\nFinal: {len(kept)} existing + {len(records)} ATC = {len(all_recs)} total")
