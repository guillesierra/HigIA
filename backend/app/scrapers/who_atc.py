from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Any

from bs4 import BeautifulSoup

from app.normalizers.text import clean_text, normalize_name
from app.scrapers.base import BaseScraper, ScrapedResource


WHO_ATC_SEED = "https://atcddd.fhi.no/atc_ddd_index/"
WHO_ATC_URLS = [
    WHO_ATC_SEED,
    "https://atcddd.fhi.no/atc_ddd_index/?code=A&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=B&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=C&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=D&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=G&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=H&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=J&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=L&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=M&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=N&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=P&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=R&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=S&showdescription=no",
    "https://atcddd.fhi.no/atc_ddd_index/?code=V&showdescription=no",
]

ATC_CODE_RE = re.compile(r"\b([A-Z][0-9]{2}[A-Z]{0,2}[0-9]{0,2})\b")
DDD_RE = re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:g|mg|mcg|µg|U|MU|TU|mmol)\b", re.IGNORECASE)
KNOWN_NON_DRUG_TERMS = {"tabletter", "tablets", "injection", "oral", "topical", "solution", "cream", "ointment", "all"}

EMBEDDED_ATC_NAMES: dict[str, str] = {
    "A02BC": "Proton pump inhibitors",
    "C10AA": "HMG CoA reductase inhibitors",
    "J01C": "Beta-lactam antibacterials, penicillins",
    "J01D": "Other beta-lactam antibacterials",
    "J01E": "Sulfonamides and trimethoprim",
    "J01F": "Macrolides, lincosamides and streptogramins",
    "J01G": "Aminoglycoside antibacterials",
    "J01M": "Quinolone antibacterials",
    "J01X": "Other antibacterials",
    "J01CA": "Penicillins with extended spectrum",
    "J01CR": "Combinations of penicillins",
    "J01DD": "Third-generation cephalosporins",
    "J01EE": "Combinations of sulfonamides",
    "J01FA": "Macrolides",
    "J01FF": "Lincosamides",
    "J01GB": "Other aminoglycosides",
    "J01MA": "Fluoroquinolones",
    "J01XD": "Imidazole derivatives",
    "J01XA": "Glycopeptide antibacterials",
    "M01A": "Antiinflammatory and antirheumatic products, non-steroids",
    "N02B": "Other analgesics and antipyretics",
    "N02BE": "Anilides",
    "N05B": "Anxiolytics",
    "N05BA": "Benzodiazepine derivatives",
    "N05C": "Hypnotics and sedatives",
    "N06A": "Antidepressants",
    "N06AB": "Selective serotonin reuptake inhibitors",
    "R03A": "Adrenergics, inhalants",
    "R03AC": "Selective beta-2-adrenoreceptor agonists",
    "A10B": "Blood glucose lowering drugs, excl. insulins",
    "A10BA": "Biguanides",
    "C07A": "Beta blocking agents",
    "C08C": "Selective calcium channel blockers with mainly vascular effect",
    "C09A": "ACE inhibitors, plain",
    "C09C": "Angiotensin II receptor blockers (ARBs), plain",
 }


def detect_atc_codes_in_text(text: str) -> list[str]:
    return sorted(set(ATC_CODE_RE.findall(text or "")))


def _extract_atc_table_rows(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in soup.select("table"):
        for tr in table.select("tr"):
            cells = [clean_text(td.get_text(" ")) for td in tr.select("td, th")]
            if len(cells) < 3:
                continue
            code_match = ATC_CODE_RE.search(cells[0])
            if not code_match:
                continue
            code = code_match.group(1)
            name = cells[1] if len(cells) > 1 else ""
            ddd_cell = cells[2] if len(cells) > 2 else ""
            ddd_value: str | None = None
            ddd_unit: str | None = None
            ddd_match = DDD_RE.search(ddd_cell)
            if ddd_match:
                ddd_value = ddd_match.group(1)
                ddd_unit = ddd_match.group(2)
            admin_route = cells[3] if len(cells) > 3 else ""
            note = cells[4] if len(cells) > 4 else ""
            level = 1 + sum(1 for ch in code if ch.isalpha())
            parent_code = code[:-1] if len(code) > 1 and code[-1].isalpha() else (code[:-2] if len(code) > 2 else None)
            rows.append({
                "code": code,
                "name": name,
                "level": level,
                "parent_code": parent_code,
                "ddd": ddd_value,
                "ddd_unit": ddd_unit,
                "admin_route": clean_text(admin_route) or None,
                "note": clean_text(note) or None,
            })
    return rows


class WhoAtcScraper(BaseScraper):
    source_name = "WHO ATC/DDD index"
    base_url = WHO_ATC_SEED
    start_url = WHO_ATC_SEED
    raw_subdir = "who_atc"
    parser_version = "who-atc-0.4"

    def parse(self, limit: int = 50, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        seen_codes: set[str] = set()

        for url in WHO_ATC_URLS:
            page = self.fetch_url(url, ".html")
            if page.error:
                resources.append(self.error_resource(url, "who_atc_fetch_failed", page.error))
                continue
            resources.append(
                ScrapedResource(
                    source_name=self.source_name,
                    source_url=url,
                    resource_type="atc_index_page",
                    title=f"WHO ATC Index: {url}",
                    url=url,
                    accessed_at=page.accessed_at,
                    raw_path=page.raw_file_path,
                    content_text=clean_text((page.text or "")[:2000]),
                    metadata={"index_url": url},
                    parser_version=self.parser_version,
                )
            )
            if page.text:
                soup = BeautifulSoup(page.text, "html.parser")
                atc_rows = _extract_atc_table_rows(soup, self.base_url)
                for row in atc_rows:
                    if row["code"] in seen_codes:
                        continue
                    seen_codes.add(row["code"])
                    resources.append(
                        ScrapedResource(
                            source_name=self.source_name,
                            source_url=url,
                            resource_type="atc_code",
                            title=row["name"],
                            url=url,
                            accessed_at=page.accessed_at,
                            raw_path=page.raw_file_path,
                            metadata={
                                "atc_code": row["code"],
                                "atc_name": row["name"],
                                "level": row["level"],
                                "parent_code": row["parent_code"],
                                "ddd": row["ddd"],
                                "ddd_unit": row["ddd_unit"],
                                "admin_route": row["admin_route"],
                                "note": row["note"],
                            },
                            parser_version=self.parser_version,
                        )
                    )
            if len(resources) >= limit:
                break
        return resources[:limit]

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            if resource.resource_type == "atc_code":
                metadata = resource.metadata or {}
                rows.append({
                    "record_type": "atc_code",
                    "code": metadata.get("atc_code", ""),
                    "name": metadata.get("atc_name", resource.title),
                    "level": metadata.get("level"),
                    "parent_code": metadata.get("parent_code"),
                    "ddd": metadata.get("ddd"),
                    "ddd_unit": metadata.get("ddd_unit"),
                    "admin_route": metadata.get("admin_route"),
                    "note": metadata.get("note"),
                    **resource.traceability(),
                })
            else:
                rows.append({
                    "record_type": resource.resource_type,
                    "title": resource.title,
                    "url": resource.url,
                    "metadata": resource.metadata,
                    **resource.traceability(),
                })
        return rows


def get_embedded_atc_codes() -> list[dict[str, Any]]:
    results = []
    for code, name in EMBEDDED_ATC_NAMES.items():
        level = 1 + sum(1 for ch in code if ch.isalpha())
        parent_code = code[:-1] if len(code) > 1 and code[-1].isalpha() else (code[:-2] if len(code) > 2 else None)
        results.append({
            "code": code,
            "name": name,
            "level": level,
            "parent_code": parent_code,
            "ddd": None,
            "ddd_unit": None,
        })
    return results
