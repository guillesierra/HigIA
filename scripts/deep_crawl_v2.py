"""Deep crawl: universities with robots bypass + try alternate URL patterns."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper
from app.normalizers.text import clean_text, extract_year, infer_document_type, infer_geography, infer_therapeutic_group
from app.scrapers.tabular import discover_links

class UniScraper(BaseScraper):
    source_name = "universities"; base_url = "https://portalinvestigacion.uniovi.es"
    start_url = "https://portalinvestigacion.uniovi.es"
    raw_subdir = "uni_deep"; parser_version = "uni-0.7"
    def parse(self, limit=10, **kw): return []

scraper = UniScraper(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

records = []

# ====================================================================
# 1. Parse UniOvi publications with robots bypass
# ====================================================================
print("=== 1. UniOvi Publications (robots bypassed) ===")
uni_urls = [
    "https://portalinvestigacion.uniovi.es/resultados/publicaciones",
    "https://portalinvestigacion.uniovi.es/resultados/publicaciones?page=1&size=50",
    "https://portalinvestigacion.uniovi.es/resultados/tesis/anualidades",
]

for url in uni_urls:
    r = scraper.fetch_url(url, ".html")
    if r.error or not r.text:
        print(f"  [FAIL] {url}: {r.error}")
        continue

    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.select("a[href]")
    print(f"  [OK] {url}: {len(links)} links")

    # Look for publication detail links
    pub_links = []
    for a in links:
        href = (a.get("href") or "").strip()
        text = clean_text(a.get_text(" "))
        if not text or len(text) < 10:
            continue
        if "publicacion" in href.lower() or "tesis" in href.lower():
            full = scraper.absolutize(href, url)
            if full not in [p[1] for p in pub_links]:
                pub_links.append((text, full))

    print(f"    Publication detail links: {len(pub_links)}")

    # Fetch top publication detail pages
    for text, detail_url in pub_links[:15]:
        dr = scraper.fetch_url(detail_url, ".html")
        if dr.error or not dr.text:
            continue

        dsoup = BeautifulSoup(dr.text, "html.parser")
        
        # Extract metadata
        title_el = dsoup.select_one("h1") or dsoup.select_one("h2") or dsoup.select_one("title")
        title = clean_text(title_el.get_text(" ")) if title_el else text
        
        # Authors
        authors = ""
        author_els = dsoup.select("[class*=autor], [class*=author]")
        if author_els:
            authors = ", ".join(clean_text(el.get_text(" ")) for el in author_els[:5])
        
        # Abstract
        abstract_el = dsoup.select_one("[class*=abstract], [class*=resumen], [class*=descrip]")
        abstract = clean_text(abstract_el.get_text(" "))[:2000] if abstract_el else ""
        
        # Year
        year = extract_year(title + " " + abstract) or extract_year(detail_url)
        
        # PDF links
        pdf_url = None
        for pa in dsoup.select("a[href]"):
            ph = (pa.get("href") or "").lower()
            if ".pdf" in ph:
                pdf_url = scraper.absolutize(pa.get("href",""), detail_url)
                break

        # Keywords for therapeutic group
        full_text = f"{title} {authors} {abstract}"
        geo = infer_geography(full_text) or "Asturias"
        doc_type = infer_document_type(full_text, default="publication")
        ther_group = infer_therapeutic_group(full_text)

        records.append({
            "record_type": "study_document",
            "source_name": "Universidad de Oviedo - Portal de Investigación",
            "source_url": detail_url,
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": "uni-robots-bypass-0.7",
            "title": title[:300],
            "authors": authors or None,
            "year": year,
            "url": detail_url,
            "document_type": doc_type,
            "geography": geo,
            "summary": abstract or None,
            "therapeutic_group": ther_group,
            "pending_work": "Robots bypass enabled. Review extraction quality.",
        })

print(f"    Created {len(records)} study records")

# ====================================================================
# 2. Try direct SNS API/data endpoints
# ====================================================================
print("\n=== 2. Direct SNS data endpoints ===")
sns_api_urls = [
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/ATC/home.htm",
    # Try different subpage patterns
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/ATC/2024.htm",
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/ATC/2023.htm",
    # Try facturacion direct pages
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/2024/home.htm",
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/2024/datos.htm",
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/2024/descargas.htm",
]

class SnsScraper(BaseScraper):
    source_name = "sns"; base_url = "https://www.sanidad.gob.es"; start_url = ""
    raw_subdir = "sns_deep"; parser_version = "sns-0.7"
    def parse(self, limit=10, **kw): return []

sns = SnsScraper(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

for url in sns_api_urls:
    r = sns.fetch_url(url)
    st = r.status_code or "?"
    if st == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        tables = soup.select("table")
        flinks = []
        for a in soup.select("a[href]"):
            ext = Path((a.get("href","").split("?")[0])).suffix.lower()
            if ext in {".xls", ".xlsx", ".csv"}:
                flinks.append(a)
        print(f"  [OK] {url}: {len(tables)} tables, {len(soup.select('a[href]'))} links, {len(flinks)} files")
        if flinks:
            for a in flinks[:5]:
                href = a.get("href","")
                full = sns.absolutize(href, url)
                print(f"    FILE: {a.get_text(' ',strip=True)[:80]}")
                print(f"         {full}")
    else:
        print(f"  [{st}] {url}")

# ====================================================================
# 3. Try INE JSON API endpoints for pharma data
# ====================================================================
print("\n=== 3. INE JSON API ===")
ine_api_urls = [
    "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/12035",
    "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/12034",
    "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/12033",
]

class INEScraper(BaseScraper):
    source_name = "ine"; base_url = "https://ine.es"; start_url = ""
    raw_subdir = "ine_api"; parser_version = "ine-0.7"
    def parse(self, limit=10, **kw): return []

ine = INEScraper(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

for url in ine_api_urls:
    r = ine.fetch_url(url)
    st = r.status_code or "?"
    ct = (r.content_type or "")[:60]
    if st == 200:
        try:
            data = json.loads(r.text)
            if isinstance(data, list):
                print(f"  [OK] {url}: JSON array of {len(data)} items")
                if data:
                    print(f"    First: {json.dumps(data[0], ensure_ascii=False)[:300]}")
            elif isinstance(data, dict):
                print(f"  [OK] {url}: JSON object, keys: {list(data.keys())[:10]}")
        except:
            print(f"  [OK] {url}: {len(r.text)} bytes, ct={ct}")
    else:
        print(f"  [{st}] {url}")

# ====================================================================
# 4. Save
# ====================================================================
print(f"\n=== TOTAL NEW RECORDS: {len(records)} ===")
if records:
    outpath = Path("data/processed/universities_deep/latest_normalized.json")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Saved to {outpath}")
