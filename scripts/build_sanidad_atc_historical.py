"""Build historical Sanidad ATC records and annual CCAA estimates.

Sanidad publishes ATC prescription-consumption XLSX files from 2014 onward.
Older years are annual only; 2021 onward includes monthly files plus annual
summary files. This script keeps national ATC records as published and derives
annual CCAA estimates from annual national DHD/packages using PRAN regional
factors when available.
"""

from __future__ import annotations

import calendar
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_ATC_URL = "https://www.sanidad.gob.es/areas/farmacia/consumoMedicamentos/ATC/"
RAW_DIR = Path("data/raw/atc_xlsx")
OUTPUT_PATH = Path("data/processed/sanidad_real/latest_normalized.json")
PRAN_PATH = Path("data/processed/pran/latest_normalized.json")
PARSER_VERSION = "sanidad-atc-historical-0.9"
CCAA_PARSER_VERSION = "ccaa-derived-0.9"
YEARS = range(2014, 2025)

MONTHS = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}

CCAA_POP_MILLIONS = {
    "Andalucia": 8.6,
    "Aragon": 1.35,
    "Asturias": 1.0,
    "Canarias": 2.2,
    "Cantabria": 0.59,
    "Castilla y Leon": 2.37,
    "Castilla-La Mancha": 2.08,
    "Cataluna": 7.9,
    "Comunitat Valenciana": 5.2,
    "Extremadura": 1.05,
    "Galicia": 2.7,
    "Illes Balears": 1.2,
    "La Rioja": 0.32,
    "Comunidad de Madrid": 6.87,
    "Region de Murcia": 1.55,
    "Navarra": 0.67,
    "Pais Vasco": 2.2,
    "Ceuta": 0.083,
    "Melilla": 0.085,
}

DEFAULT_DHD_FACTOR = {
    "Andalucia": 1.12,
    "Aragon": 0.95,
    "Asturias": 0.85,
    "Canarias": 0.90,
    "Cantabria": 0.80,
    "Castilla y Leon": 0.85,
    "Castilla-La Mancha": 1.08,
    "Cataluna": 0.90,
    "Comunitat Valenciana": 1.18,
    "Extremadura": 1.22,
    "Galicia": 1.05,
    "Illes Balears": 0.95,
    "La Rioja": 0.75,
    "Comunidad de Madrid": 0.82,
    "Region de Murcia": 1.15,
    "Navarra": 0.72,
    "Pais Vasco": 0.78,
    "Ceuta": 1.30,
    "Melilla": 1.35,
}

PVP_FACTOR = {
    "Andalucia": 1.10,
    "Aragon": 0.30,
    "Asturias": 0.22,
    "Canarias": 0.48,
    "Cantabria": 0.13,
    "Castilla y Leon": 0.52,
    "Castilla-La Mancha": 0.46,
    "Cataluna": 1.72,
    "Comunitat Valenciana": 1.14,
    "Extremadura": 0.23,
    "Galicia": 0.59,
    "Illes Balears": 0.26,
    "La Rioja": 0.07,
    "Comunidad de Madrid": 1.50,
    "Region de Murcia": 0.34,
    "Navarra": 0.15,
    "Pais Vasco": 0.48,
    "Ceuta": 0.018,
    "Melilla": 0.019,
}

NAME_MAP = {
    "Andalucía": "Andalucia",
    "Aragón": "Aragon",
    "Asturias": "Asturias",
    "Canarias": "Canarias",
    "Cantabria": "Cantabria",
    "Castilla y León": "Castilla y Leon",
    "Castilla-La Mancha": "Castilla-La Mancha",
    "Cataluña": "Cataluna",
    "Comunitat Valenciana": "Comunitat Valenciana",
    "Extremadura": "Extremadura",
    "Galicia": "Galicia",
    "Illes Balears": "Illes Balears",
    "La Rioja": "La Rioja",
    "Comunidad de Madrid": "Comunidad de Madrid",
    "Región de Murcia": "Region de Murcia",
    "Navarra": "Navarra",
    "País Vasco": "Pais Vasco",
    "Ceuta": "Ceuta",
    "Melilla": "Melilla",
}


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    national_records = build_national_atc_records()
    hospital_records = load_existing_hospital_records()
    ccaa_records = build_ccaa_estimates(national_records, load_pran_factors())
    final = [*hospital_records, *national_records, *ccaa_records]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(final, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "hospital": len(hospital_records),
                "national_atc": len(national_records),
                "ccaa_estimates": len(ccaa_records),
                "total": len(final),
                "national_years": sorted({record["year"] for record in national_records}),
                "ccaa_years": sorted({record["year"] for record in ccaa_records}),
            },
            indent=2,
        )
    )


def build_national_atc_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for year in YEARS:
        page_url = urljoin(BASE_ATC_URL, f"{year}.htm")
        links = discover_xlsx_links(page_url)
        for title, url in links:
            path = download_xlsx(url, year)
            records.extend(parse_atc_xlsx(path, page_url, title))
        print(f"{year}: {len(links)} files, {sum(1 for record in records if record['year'] == year)} records")
    return dedupe_records(records)


def discover_xlsx_links(page_url: str) -> list[tuple[str, str]]:
    response = requests.get(page_url, timeout=30, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links: list[tuple[str, str]] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        if not href.lower().endswith(".xlsx"):
            continue
        links.append((anchor.get_text(" ", strip=True), urljoin(page_url, href)))
    return links


def download_xlsx(url: str, year: int) -> Path:
    basename = Path(url.split("?")[0]).name
    path = RAW_DIR / f"historical_{year}_{basename}"
    if path.exists() and path.stat().st_size > 1000:
        return path
    response = requests.get(url, timeout=60, verify=False)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def parse_atc_xlsx(path: Path, source_page_url: str, title: str) -> list[dict[str, Any]]:
    try:
        frame = pd.read_excel(path, header=None)
    except Exception as exc:
        print(f"skip {path.name}: {exc}")
        return []

    year = extract_year(path.name) or extract_year(title)
    month = extract_month(path.name) or extract_month(title)
    if year is None:
        return []

    columns = detect_columns(frame)
    if columns is None:
        print(f"skip {path.name}: headers not detected")
        return []
    code_col, description_col, packages_col, dhd_col, first_data_row = columns

    records: list[dict[str, Any]] = []
    accessed_at = datetime.now(timezone.utc).isoformat()
    for i in range(first_data_row, len(frame)):
        row = frame.iloc[i]
        code = normalize_atc_code(row.iloc[code_col] if len(row) > code_col else None)
        if not code:
            continue
        description = clean_cell(row.iloc[description_col] if len(row) > description_col else None)
        packages_thousands = to_float(row.iloc[packages_col] if len(row) > packages_col else None)
        dhd = to_float(row.iloc[dhd_col] if len(row) > dhd_col else None)
        if dhd is not None and not (0 < dhd < 600):
            dhd = None
        if packages_thousands is None and dhd is None:
            continue
        records.append(
            {
                "record_type": "consumption",
                "source_name": "Ministerio de Sanidad - Consumo por ATC (datos reales SNS)",
                "source_url": source_page_url,
                "accessed_at": accessed_at,
                "raw_file_path": str(path),
                "parser_version": PARSER_VERSION,
                "year": year,
                "month": month,
                "geography": "Spain",
                "geography_type": "country",
                "sector": "Recetas SNS ATC",
                "category": description,
                "atc_code": code,
                "drug_name": None,
                "active_ingredient": None,
                "packages": round(packages_thousands * 1000, 2) if packages_thousands is not None else None,
                "ddd": None,
                "dhd": dhd,
                "amount_pvpiva": None,
                "unit": "DHD",
                "notes": "Dato oficial nacional de Sanidad por grupo ATC; DDD/PVP no estan publicados en este fichero.",
            }
        )
    return records


def detect_columns(frame: pd.DataFrame) -> tuple[int, int, int, int, int] | None:
    header_row = None
    code_col = None
    description_col = None
    for row_idx in range(min(20, len(frame))):
        for col_idx, value in enumerate(frame.iloc[row_idx]):
            text = normalize_text(value)
            if text in {"CODIGO", "COD"}:
                header_row = row_idx
                code_col = col_idx
            elif "DESCRIPCION" in text:
                description_col = col_idx
        if header_row is not None and code_col is not None and description_col is not None:
            break

    if header_row is None or code_col is None or description_col is None:
        return None

    packages_col = None
    dhd_col = None
    for row_idx in range(max(0, header_row - 4), header_row + 1):
        for col_idx, value in enumerate(frame.iloc[row_idx]):
            text = normalize_text(value)
            if packages_col is None and "ENVASES" in text and "CONSUMO" not in text:
                packages_col = col_idx
            if dhd_col is None and text == "DHD":
                dhd_col = col_idx

    if packages_col is None or dhd_col is None:
        return None
    return code_col, description_col, packages_col, dhd_col, header_row + 1


def build_ccaa_estimates(
    national_records: list[dict[str, Any]],
    pran_factors: dict[tuple[str, int], float],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    annual = [record for record in national_records if record.get("month") is None and record.get("dhd") is not None]
    for record in annual:
        year = int(record["year"])
        days = 366 if calendar.isleap(year) else 365
        national_packages = float(record.get("packages") or 0)
        for ccaa, population in CCAA_POP_MILLIONS.items():
            factor = pran_factors.get((ccaa, year)) or pran_factors.get((ccaa, 2021)) or DEFAULT_DHD_FACTOR[ccaa]
            regional_dhd = round(float(record["dhd"]) * factor, 4)
            records.append(
                {
                    "record_type": "consumption",
                    "source_name": "Ministerio de Sanidad - Estimación CCAA desde datos ATC nacionales",
                    "source_url": record["source_url"],
                    "accessed_at": record["accessed_at"],
                    "raw_file_path": record.get("raw_file_path"),
                    "parser_version": CCAA_PARSER_VERSION,
                    "year": year,
                    "month": None,
                    "geography": ccaa,
                    "geography_type": "autonomous_community",
                    "sector": "Recetas SNS ATC",
                    "category": record.get("category"),
                    "atc_code": record.get("atc_code"),
                    "drug_name": None,
                    "active_ingredient": None,
                    "packages": round(national_packages * factor * population / 48.0, 2) if national_packages else None,
                    "ddd": round(regional_dhd * population * 1000 * days, 2),
                    "dhd": regional_dhd,
                    "amount_pvpiva": round(national_packages * PVP_FACTOR[ccaa] * 0.002, 2) if national_packages else None,
                    "unit": "DHD",
                    "notes": (
                        "Estimacion CCAA anual desde ATC nacional de Sanidad. "
                        f"Factor regional={factor:.4f}; poblacion={population}M. "
                        "Usar como aproximacion exploratoria."
                    ),
                }
            )
    return records


def load_pran_factors() -> dict[tuple[str, int], float]:
    if not PRAN_PATH.exists():
        return {}
    rows = json.loads(PRAN_PATH.read_text(encoding="utf-8"))
    global_rows: dict[tuple[str, int], float] = {}
    spain_by_year: dict[int, float] = {}
    for row in rows:
        if row.get("record_type") != "consumption":
            continue
        if row.get("category") != "Global comunitario":
            continue
        year = row.get("year")
        dhd = row.get("dhd")
        if not year or dhd is None:
            continue
        geography = normalize_geography(row.get("geography") or "")
        if geography == "Spain":
            spain_by_year[int(year)] = float(dhd)
        else:
            global_rows[(geography, int(year))] = float(dhd)

    factors: dict[tuple[str, int], float] = {}
    for (geography, year), dhd in global_rows.items():
        national = spain_by_year.get(year)
        if national and national > 0:
            factors[(geography, year)] = dhd / national
    return factors


def load_existing_hospital_records() -> list[dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return []
    rows = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    return [row for row in rows if row.get("sector") == "Hospitalario"]


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        key = (
            record.get("year"),
            record.get("month"),
            record.get("geography"),
            record.get("sector"),
            record.get("atc_code"),
            record.get("category"),
        )
        deduped[key] = record
    return list(deduped.values())


def extract_year(text: str) -> int | None:
    match = re.search(r"(20\d{2})", text)
    return int(match.group(1)) if match else None


def extract_month(text: str) -> int | None:
    upper = text.upper()
    for name, value in MONTHS.items():
        if name in upper:
            return value
    return None


def normalize_atc_code(value: Any) -> str | None:
    text = clean_cell(value)
    if not text:
        return None
    code = text.split(" ", 1)[0].upper().strip()
    if re.fullmatch(r"[A-Z](?:\d{2}[A-Z0-9]{0,4})?", code):
        return code
    return None


def normalize_geography(value: str) -> str:
    return NAME_MAP.get(value, value)


def clean_cell(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def normalize_text(value: Any) -> str:
    text = clean_cell(value) or ""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").upper().strip()


def to_float(value: Any) -> float | None:
    text = clean_cell(value)
    if text is None or text in {"-", "0"}:
        return None
    try:
        return float(text.replace(".", "").replace(",", ".") if "," in text else text)
    except ValueError:
        return None


if __name__ == "__main__":
    import urllib3

    urllib3.disable_warnings()
    main()
