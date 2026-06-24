"""Download and parse ALL ATC XLSX files from 2022-2024 - REAL consumption data by ATC code."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.scrapers.tabular import read_tabular_file, rows_to_jsonable
from app.normalizers.consumption import normalize_consumption_dataframe

BASE = "https://www.sanidad.gob.es"

class ATCScraper(BaseScraper):
    source_name = "atc"; base_url = BASE; start_url = ""
    raw_subdir = "atc_xlsx"; parser_version = "atc-0.7"
    def parse(self, limit=10, **kw): return []

scraper = ATCScraper(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

records = []
total_downloaded = 0
total_parsed = 0

def parse_xlsx_file(path, source_url, context):
    global total_parsed
    local = []
    try:
        sheets = read_tabular_file(Path(path))
        for sn, df in sheets:
            if df.shape[0] < 2:
                continue
            
            if total_parsed <= 2:
                print(f"    {Path(path).name}: {df.shape}, cols={list(df.columns)[:10]}")
                print(f"    Head:\n{df.head(2).to_string()}")
            
            normalized = normalize_consumption_dataframe(
                df,
                source_name="Ministerio de Sanidad - Consumo por ATC (datos reales SNS)",
                source_url=source_url,
                accessed_at=datetime.now(timezone.utc).isoformat(),
                raw_file_path=path,
                parser_version="sanidad-atc-real-0.7",
                default_geography="Spain",
                context_text=f"{context} {sn}",
            )
            for rec in rows_to_jsonable(normalized):
                rec.update({"record_type": "consumption", "sheet_name": sn, "sector": "Recetas SNS ATC"})
                if rec.get("year") is not None:
                    local.append(rec)
        
        total_parsed += 1
    except Exception as e:
        print(f"    ERROR: {str(e)[:100]}")
    return local

SPANISH_MONTHS_UC = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
                      "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]

# Scan each year page for XLSX links
for year in [2024, 2023, 2022]:
    page_url = f"{BASE}/areas/farmacia/consumoMedicamentos/ATC/{year}.htm"
    r = scraper.fetch_url(page_url)
    
    if r.status_code == 200 and r.text:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href.lower().endswith(".xlsx"):
                continue
            text = a.get_text(" ", strip=True)
            full_url = scraper.absolutize(href, page_url)
            dl = scraper.fetch_url(full_url, ".xlsx")
            if dl.error:
                continue
            total_downloaded += 1
            local = parse_xlsx_file(dl.raw_file_path, full_url, f"{text}")
            records.extend(local)
        print(f"  {year}: page OK, {total_downloaded} files so far, {len(records)} records parsed")
    else:
        print(f"  {year}: {r.status_code} - trying direct URLs")
        for month in SPANISH_MONTHS_UC:
            for var in ["ATC", "ATC1", "ATC2", "ATC3"]:
                url = f"{BASE}/areas/farmacia/consumoMedicamentos/ATC/docs/{month}_{year}_{var}.xlsx"
                dl = scraper.fetch_url(url, ".xlsx")
                if dl.status_code == 200 and dl.raw_file_path:
                    total_downloaded += 1
                    local = parse_xlsx_file(dl.raw_file_path, url, f"{month} {year}")
                    records.extend(local)

print(f"\n=== RESULTS: {total_downloaded} files, {len(records)} records ===")

if records:
    outdir = Path("data/processed/sanidad_real")
    outdir.mkdir(parents=True, exist_ok=True)
    
    epath = outdir / "latest_normalized.json"
    existing = []
    if epath.exists():
        existing = json.loads(epath.read_text(encoding="utf-8"))
    
    all_recs = existing + records
    epath.write_text(json.dumps(all_recs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Merged: {len(existing)} + {len(records)} = {len(all_recs)} total")
    
    # Stats
    by_sector = {}
    for r in all_recs:
        s = r.get("sector","?")
        by_sector[s] = by_sector.get(s,0)+1
    print(f"Sectors: {by_sector}")
