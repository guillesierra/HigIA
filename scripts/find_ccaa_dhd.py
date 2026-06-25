"""Try SNS portal and other sources for CCAA-level DHD, DDD, PVPIVA data."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.scrapers.base import BaseScraper
import urllib3; urllib3.disable_warnings()

class A(BaseScraper):
    source_name="a"; base_url=""; start_url=""
    raw_subdir="sns_api2"; parser_version="a"
    def parse(self, limit=10, **kw): return []

a = A(delay_seconds=0.3, verify_ssl=False, respect_robots=False)

# Try SNS portal - the JS app likely calls JSON APIs
base = "https://pestadistico.inteligenciadegestion.sanidad.gob.es"

apis = [
    # Common SNS API patterns
    f"{base}/publicoSNS/api/indicadores/list",
    f"{base}/publicoSNS/api/datos/consulta",
    f"{base}/publicoSNS/api/v1/indicadores",
    f"{base}/publicoSNS/api/v1/datos",
    f"{base}/publicoSNS/api/catalog",
    # Direct data endpoint patterns
    f"{base}/publicoSNS/D/consumo-farmaceutico-en-el-sns/consumo-en-recetas-medicas-sns/consumo-medicamentos-por-atc/datos",
    f"{base}/publicoSNS/S/consulta",
    # REST API
    f"{base}/api/publico/indicadores",
    f"{base}/api/publico/consulta",
    # JSON data
    f"{base}/publicoSNS/D/consumo-farmaceutico-en-el-sns/consumo-en-recetas-medicas-sns/datos.json",
    # Alternative portal
    "https://www.sanidad.gob.es/estadEstudios/estadisticas/estadisticas/estMinisterio/indicadoresSalud.htm",
]

for u in apis:
    r = a.fetch_url(u)
    ct = (r.content_type or "")[:60]
    code = r.status_code or "?"
    size = len(r.text or "")
    print(f"  [{code}] {ct} | {size}B | {u}")
    if code == 200 and size > 100:
        if "json" in ct or u.endswith(".json"):
            try:
                d = json.loads(r.text)
                if isinstance(d, dict): print(f"    Keys: {list(d.keys())[:8]}")
                elif isinstance(d, list): print(f"    Array[{len(d)}], first: {json.dumps(d[0],ensure_ascii=False)[:200] if d else 'empty'}")
            except: pass
        elif size < 500:
            print(f"    Body: {r.text[:300]}")

# Try CCAA_INGESA with different URL patterns
print("\n=== CCAA Facturacion alternative URLs ===")
ccaa_urls = [
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/2024/enero.pdf",
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/docs/2024_CCAA.xlsx",
    "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/CCAA_INGESA/docs/CCAA_2024.xlsx",
]
for u in ccaa_urls:
    r = a.fetch_url(u, Path(u).suffix)
    print(f"  [{r.status_code}] {u}")

# Try the facturacion recetas main page for XLSX files
print("\n=== Facturacion Recetas direct XLSX ===")
from bs4 import BeautifulSoup
fact_url = "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/facturacionRecetas/home.htm"
r = a.fetch_url(fact_url)
if r.status_code == 200 and r.text:
    soup = BeautifulSoup(r.text, "html.parser")
    all_hrefs = [(a.get("href",""), a.get_text(" ",strip=True)[:80]) for a in soup.select("a[href]")]
    print(f"  Links: {len(all_hrefs)}")
    # Show content-relevant links
    for href, text in all_hrefs:
        if any(kw in (href+text).lower() for kw in ["xls","csv","pdf","datos","descarg","factur","2024","2023","2022"]):
            print(f"    {text[:60]} -> {href[:120]}")
