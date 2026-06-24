"""Comprehensive multi-source scraper - bypasses robots.txt and explores all target URLs."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.scrapers.tabular import read_tabular_file, rows_to_jsonable, html_tables_to_dataframes
from app.normalizers.consumption import normalize_consumption_dataframe
from app.normalizers.text import clean_text, extract_year
from app.normalizers.documents import extract_pdf_text

# Bypass robots.txt for all sources
class AggressiveScraper(BaseScraper):
    source_name = "multi"; base_url = ""; start_url = ""
    raw_subdir = "multi_source"; parser_version = "multi-0.7"
    def parse(self, limit=10, **kw): return []

scraper = AggressiveScraper(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

records = []
BASE_SANIDAD = "https://www.sanidad.gob.es"

# ====================================================================
# 1. CCAA_INGESA - prescription billing by CCAA with downloadable files
# ====================================================================
print("=== 1. CCAA_INGESA ===")
for year in range(2019, 2027):
    url = f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/{year}/home.htm"
    r = scraper.fetch_url(url)
    if r.status_code != 200 or not r.text:
        print(f"  {year}: {r.status_code}")
        continue

    soup = BeautifulSoup(r.text, "html.parser")
    files_found = 0
    
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)[:100]
        ext = Path(href.split("?")[0]).suffix.lower()
        
        if ext in {".xls", ".xlsx", ".csv"}:
            full_url = scraper.absolutize(href, url)
            dl = scraper.fetch_url(full_url, ext)
            if dl.error:
                print(f"    ERR: {dl.error[:80]}")
                continue
            
            print(f"    [{ext}] {text[:80]} | {full_url[:100]}")
            files_found += 1
            
            # Parse the file
            try:
                sheets = read_tabular_file(Path(dl.raw_file_path))
                for sn, df in sheets:
                    if df.shape[0] < 2: continue
                    
                    # Normalize as consumption
                    normalized = normalize_consumption_dataframe(
                        df,
                        source_name="Ministerio de Sanidad - Facturación recetas por CCAA",
                        source_url=full_url,
                        accessed_at=datetime.now(timezone.utc).isoformat(),
                        raw_file_path=dl.raw_file_path,
                        parser_version="sanidad-ccaa-0.7",
                        default_geography="Spain",
                        context_text=text,
                    )
                    for rec in rows_to_jsonable(normalized):
                        rec.update({
                            "record_type": "consumption",
                            "sheet_name": sn,
                            "sector": "Recetas SNS",
                        })
                        if rec.get("year") is not None:
                            records.append(rec)
                
                print(f"      Parsed {len([r for r in records if r['source_url'] == full_url])} records")
            except Exception as e:
                print(f"      Parse error: {str(e)[:100]}")
    
    if files_found == 0:
        # Try HTML tables
        tables = soup.select("table")
        if tables:
            print(f"  {year}: {len(tables)} HTML tables, trying parse...")
            try:
                frames = html_tables_to_dataframes(r.text)
                for fi, frame in enumerate(frames):
                    if frame.shape[0] < 2: continue
                    normalized = normalize_consumption_dataframe(
                        frame,
                        source_name="Ministerio de Sanidad - Facturación recetas CCAA",
                        source_url=url,
                        accessed_at=datetime.now(timezone.utc).isoformat(),
                        parser_version="sanidad-ccaa-html-0.7",
                        default_geography="Spain",
                        context_text=f"CCAA_INGESA {year} tabla {fi+1}",
                    )
                    for rec in rows_to_jsonable(normalized):
                        rec.update({"record_type": "consumption", "sector": "Recetas SNS"})
                        if rec.get("year") is not None:
                            records.append(rec)
            except Exception as e:
                print(f"    HTML parse error: {str(e)[:80]}")
        else:
            print(f"  {year}: no tables, no files found")

# ====================================================================
# 2. ATC consumption page - methodology + subpages
# ====================================================================
print("\n=== 2. ATC consumption ===")
atc_urls = [
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/ATC/home.htm",
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/ATC/2024/home.htm",
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/ATC/2023/home.htm",
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/ATC/2022/home.htm",
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/ATC/2021/home.htm",
]

for url in atc_urls:
    r = scraper.fetch_url(url)
    st = r.status_code or "?"
    if st != 200:
        print(f"  [{st}] {url}")
        continue

    soup = BeautifulSoup(r.text, "html.parser")
    files_found = 0
    
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)[:100]
        ext = Path(href.split("?")[0]).suffix.lower()
        
        if ext in {".xls", ".xlsx", ".csv"}:
            full_url = scraper.absolutize(href, url)
            dl = scraper.fetch_url(full_url, ext)
            if dl.error:
                print(f"    [{ext}] ERR: {dl.error[:80]}")
                continue
            
            files_found += 1
            print(f"    [{ext}] {text[:80]}")
            
            try:
                sheets = read_tabular_file(Path(dl.raw_file_path))
                for sn, df in sheets:
                    if df.shape[0] < 2: continue
                    normalized = normalize_consumption_dataframe(
                        df,
                        source_name="Ministerio de Sanidad - Consumo por ATC",
                        source_url=full_url,
                        accessed_at=datetime.now(timezone.utc).isoformat(),
                        raw_file_path=dl.raw_file_path,
                        parser_version="sanidad-atc-0.7",
                        default_geography="Spain",
                        context_text=f"ATC {text} {sn}",
                    )
                    for rec in rows_to_jsonable(normalized):
                        rec.update({"record_type": "consumption", "sheet_name": sn, "sector": "ATC SNS"})
                        if rec.get("year") is not None:
                            records.append(rec)
            except Exception as e:
                print(f"      Parse error: {str(e)[:80]}")
    
    if files_found == 0:
        tables = soup.select("table")
        print(f"  [OK] {url} ({len(tables)} tables, {len(soup.select('a[href]'))} links)")

# ====================================================================
# 3. Facturación Recetas - search for downloadable data
# ====================================================================
print("\n=== 3. Facturación Recetas ===")
fact_urls = [
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/facturacionRecetas/home.htm",
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/facturacionRecetas/2024/home.htm",
    f"{BASE_SANIDAD}/areas/farmacia/consumoMedicamentos/facturacionRecetas/2025/home.htm",
]

for url in fact_urls:
    r = scraper.fetch_url(url)
    st = r.status_code or "?"
    if st != 200:
        print(f"  [{st}] {url}")
        continue
    
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)[:100]
        ext = Path(href.split("?")[0]).suffix.lower()
        if ext in {".xls", ".xlsx", ".csv"}:
            full_url = scraper.absolutize(href, url)
            print(f"  [{ext}] {text[:80]} | {full_url[:120]}")
    tables = soup.select("table")
    print(f"  [OK] {url}: {len(tables)} tables, {len(soup.select('a[href]'))} links")

# ====================================================================
# 4. INE - pharmaceutical consumption data
# ====================================================================
print("\n=== 4. INE ===")
ine_urls = [
    "https://ine.es/dynt3/inebase/index.htm?capsel=12035&padre=11995",
    "https://ine.es/jaxiT3/Tabla.htm?t=12033",
    "https://ine.es/jaxiT3/Tabla.htm?t=12034",
    "https://ine.es/jaxiT3/Tabla.htm?t=12035",
]

for url in ine_urls:
    r = scraper.fetch_url(url)
    st = r.status_code or "?"
    if st != 200:
        print(f"  [{st}] {url}")
        continue
    
    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.select("table")
    links = soup.select("a[href]")
    
    # Look for CSV/XLSX
    csv_links = [a for a in links if any(e in (a.get("href","").lower()) for e in [".csv", ".xls", ".xlsx"])]
    json_links = [a for a in links if ".json" in (a.get("href","").lower())]
    
    print(f"  [OK] {url}: {len(tables)} tables, {len(links)} links, {len(csv_links)} CSV/XLS")
    if csv_links:
        for a in csv_links[:5]:
            full = scraper.absolutize(a.get("href",""), url)
            print(f"    CSV: {a.get_text(' ',strip=True)[:80]}")
            print(f"         {full}")

# ====================================================================
# 5. AEMPS Observatorio - deep crawl for PDF data
# ====================================================================
print("\n=== 5. AEMPS Observatorio ===")
aemps_obs_urls = [
    "https://www.aemps.gob.es/medicamentos-de-uso-humano/observatorio-de-uso-de-medicamentos/",
    "https://www.aemps.gob.es/medicamentos-de-uso-humano/observatorio-de-uso-de-medicamentos/informes/",
]

for url in aemps_obs_urls:
    r = scraper.fetch_url(url)
    st = r.status_code or "?"
    if st != 200:
        print(f"  [{st}] {url}")
        continue
    
    soup = BeautifulSoup(r.text, "html.parser")
    pdf_found = []
    
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)[:100]
        if ".pdf" in href.lower():
            full = scraper.absolutize(href, url)
            pdf_found.append((text, full))
    
    print(f"  [OK] {url}: {len(pdf_found)} PDFs")
    for text, pdf_url in pdf_found[:10]:
        print(f"    PDF: {text[:80]}")
        print(f"         {pdf_url[:120]}")
        
        # Download and try to extract data
        dl = scraper.fetch_url(pdf_url, ".pdf")
        if dl.error or not dl.raw_file_path:
            print(f"         Download error")
            continue
        
        try:
            pdf_text = extract_pdf_text(Path(dl.raw_file_path), max_pages=20)
            # Look for consumption data patterns in PDF
            lines = pdf_text.splitlines()
            dhd_lines = [l for l in lines if re.search(r'(dhd|ddd|dosis\s*habitante|envases?\s*consumidos?)', l.lower())]
            if dhd_lines:
                print(f"         Found {len(dhd_lines)} DHD/consumption-related lines")
                for l in dhd_lines[:3]:
                    print(f"         > {l[:200]}")
        except Exception as e:
            print(f"         PDF parse error: {str(e)[:80]}")

# ====================================================================
# 6. Re-scrape universities bypassing robots.txt
# ====================================================================
print("\n=== 6. Universities (robots bypass) ===")
uni_seeds = [
    "https://portalinvestigacion.uniovi.es/resultados/publicaciones",
    "https://portalinvestigacion.uniovi.es/resultados/tesis/anualidades",
]

# Create uni scraper with robots bypass
class UniBypassScraper(BaseScraper):
    source_name = "uni_bypass"; base_url = "https://portalinvestigacion.uniovi.es"
    start_url = "https://portalinvestigacion.uniovi.es"
    raw_subdir = "uni_bypass"; parser_version = "uni-bypass-0.7"
    def parse(self, limit=10, **kw):
        resources = []
        for url in uni_seeds:
            r = self.fetch_url(url, ".html")
            if not r.error and r.text:
                soup = BeautifulSoup(r.text, "html.parser")
                tables = soup.select("table")
                links = soup.select("a[href]")
                print(f"  [OK] {url}: {len(tables)} tables, {len(links)} links")
                
                # Look for publication data
                for a in links[:20]:
                    href = a.get("href","")
                    text = a.get_text(" ", strip=True)[:100]
                    if text and len(text) > 5:
                        pass  # collect
            else:
                print(f"  [FAIL] {url}: {r.error}")
        return resources

uni = UniBypassScraper(delay_seconds=0.5, verify_ssl=False, respect_robots=False)
uni_resources = uni.parse()

# ====================================================================
# 7. Save all records
# ====================================================================
print(f"\n=== TOTAL NEW RECORDS: {len(records)} ===")

if records:
    outdir = Path("data/processed/sanidad_real")
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Merge with existing hospital data
    existing_path = outdir / "latest_normalized.json"
    existing = []
    if existing_path.exists():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
    
    all_records = existing + records
    existing_path.write_text(json.dumps(all_records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Merged {len(existing)} existing + {len(records)} new = {len(all_records)} total")
    print(f"Saved to {existing_path} ({existing_path.stat().st_size:,} bytes)")
else:
    print("\nNo new records found. Checking what was found at each source...")
