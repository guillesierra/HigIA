"""Full scrape of ALL hospital consumption data 2017-2026."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper

BASE = "https://www.sanidad.gob.es"

class Crawler(BaseScraper):
    source_name = "c"; base_url = BASE; start_url = ""
    raw_subdir = "hospital_full"; parser_version = "c"
    def parse(self, limit=10, **kw): return []

crawler = Crawler(delay_seconds=0.15, verify_ssl=False)

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

CCAA_MAP = {
    "andalucia": "Andalucia", "aragon": "Aragon", "asturias": "Asturias",
    "baleares": "Illes Balears", "illes balears": "Illes Balears",
    "canarias": "Canarias", "cantabria": "Cantabria",
    "castilla y leon": "Castilla y Leon", "castilla la mancha": "Castilla-La Mancha",
    "cataluna": "Cataluna", "catalunya": "Cataluna",
    "comunitat valenciana": "Comunitat Valenciana", "comunidad valenciana": "Comunitat Valenciana",
    "c.valenciana": "Comunitat Valenciana",
    "extremadura": "Extremadura", "galicia": "Galicia",
    "madrid": "Comunidad de Madrid", "comunidad de madrid": "Comunidad de Madrid",
    "murcia": "Region de Murcia", "region de murcia": "Region de Murcia",
    "navarra": "Navarra", "pais vasco": "Pais Vasco", "euskadi": "Pais Vasco",
    "la rioja": "La Rioja", "rioja": "La Rioja",
    "ceuta": "Ceuta", "melilla": "Melilla", "ingesa": "Spain",
}
SKIP_WORDS = {"comunidad", "total", "datos", "acumulado", "numero", "num."}

def parse_ccaa(raw):
    t = re.sub(r"\s+", " ", str(raw).strip().lower())
    t = re.sub(r"^\d+\s*", "", t)
    if any(w in t for w in SKIP_WORDS):
        return None
    for k, v in CCAA_MAP.items():
        if k in t:
            return v
    return None

def clean_num(s):
    if not s: return None
    s = str(s).strip().replace(".", "").replace(",", ".")
    try: return float(s)
    except: return None

records = []
total_pages = 0
empty_pages = 0

for year in range(2017, 2027):
    for mi, month_name in enumerate(MONTHS_ES):
        month_num = mi + 1
        if year == 2026 and month_num > 3:
            continue

        url = f"{BASE}/areas/farmacia/consumoMedicamentos/hospitalario/{year}/{month_name}.htm"
        result = crawler.fetch_url(url)
        if result.status_code != 200 or not result.text:
            continue

        soup = BeautifulSoup(result.text, "html.parser")
        tables = soup.select("table")
        if not tables:
            continue

        total_pages += 1
        page_records = 0

        for table in tables:
            rows_data = []
            for tr in table.select("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.select("td, th")]
                if cells:
                    rows_data.append(cells)

            if len(rows_data) < 3:
                continue

            for row in rows_data:
                if len(row) < 2:
                    continue
                ccaa = parse_ccaa(row[0])
                if not ccaa:
                    continue

                monthly = clean_num(row[1]) if len(row) > 1 else None
                accumulated = clean_num(row[2]) if len(row) > 2 else None
                interannual = clean_num(row[3]) if len(row) > 3 else None

                if monthly is not None and monthly > 0:
                    notes_parts = []
                    if accumulated is not None: notes_parts.append(f"Acum: {accumulated}")
                    if interannual is not None: notes_parts.append(f"Interanual: {interannual}")
                    
                    records.append({
                        "record_type": "consumption",
                        "source_name": "Ministerio de Sanidad - Consumo hospitalario SNS",
                        "source_url": url,
                        "accessed_at": datetime.now(timezone.utc).isoformat(),
                        "raw_file_path": result.raw_file_path,
                        "parser_version": "sanidad-hospital-0.6",
                        "year": year, "month": month_num,
                        "geography": ccaa,
                        "geography_type": "country" if ccaa == "Spain" else "autonomous_community",
                        "sector": "Hospitalario",
                        "atc_code": None, "drug_name": None, "active_ingredient": None,
                        "packages": monthly, "ddd": None, "dhd": None, "amount_pvpiva": None,
                        "notes": "; ".join(notes_parts) if notes_parts else None,
                    })
                    page_records += 1

        if page_records == 0:
            empty_pages += 1

        print(f"  {year}/{month_name}: {page_records} records", end="\r")

print(f"\n\nTotal pages scraped: {total_pages}")
print(f"Pages with no parsable data: {empty_pages}")
print(f"Total hospital records: {len(records)}")

# Save
outdir = Path("data/processed/sanidad_real")
outdir.mkdir(parents=True, exist_ok=True)
outpath = outdir / "latest_normalized.json"
outpath.write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"Saved to {outpath} ({outpath.stat().st_size:,} bytes)")

# By year stats
by_year = {}
for r in records:
    y = r["year"]
    by_year[y] = by_year.get(y, 0) + 1
print(f"\nBy year: {dict(sorted(by_year.items()))}")
