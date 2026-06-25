from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup

from app.normalizers.documents import extract_pdf_text
from app.normalizers.text import clean_text, extract_dates, normalize_drug_name, parse_date
from app.scrapers.base import BaseScraper, ScrapedResource


ACTIVE_INGREDIENT_CONTEXT_RE = re.compile(
    r"(?:principio activo|contienen|medicamentos? con|uso de)\s+([a-záéíóúñ][a-záéíóúñ0-9\s,\-/]{2,120})",
    re.IGNORECASE,
)
PHARMA_SUFFIX_RE = re.compile(r"\b[a-záéíóúñ]{5,}(?:mab|nib|pril|sartan|olol|azol|cillin|micina|xaban|prazol)\b", re.IGNORECASE)
ACTIVE_INGREDIENT_STOPWORDS = {
    "medicamentos", "pacientes", "tratamiento", "seguridad", "riesgo", "nueva", "informacion",
    "recomendaciones", "autorizacion", "administracion", "detectar", "el fin de prevenir",
    "gestionar posibles escaseces", "problemas de suministro", "es biologico",
    "los distintos medicamentos", "medicamentos ultima actualizacion",
    "productos sanitarios", "ipt previo",
}


class AempsSafetyAlertsScraper(BaseScraper):
    source_name = "AEMPS medicine safety notes"
    base_url = "https://www.aemps.gob.es"
    start_url = "https://www.aemps.gob.es/comunicacion/notas-de-seguridad/notas-informativas-de-seguridad-de-medicamentos-de-uso-humano/"
    raw_subdir = "aemps"
    parser_version = "aemps-safety-alerts-0.3"

    def parse(self, limit: int = 50, fetch_details: bool = True, **_: Any) -> list[ScrapedResource]:
        index = self.fetch_url(self.start_url, ".html")
        if index.error:
            return [self.error_resource(self.start_url, "index_fetch_failed", index.error)]

        soup = BeautifulSoup(index.text or "", "html.parser")
        resources: list[ScrapedResource] = []
        seen: set[str] = set()

        for link in soup.select("a[href]"):
            href = link.get("href")
            title = clean_text(link.get_text(" "))
            if not href or not title:
                continue
            url = self.absolutize(href, self.start_url)
            if url in seen or not self._looks_like_alert_link(url, title):
                continue
            seen.add(url)

            row_text = clean_text(link.parent.get_text(" ") if link.parent else title)
            alert_date = parse_date(row_text)
            raw_path = index.raw_file_path
            raw_text = row_text
            pdf_url = None
            pdf_raw_path = None
            pdf_text = None

            if fetch_details:
                detail = self._fetch_detail(url)
                raw_path = detail.get("raw_file_path") or raw_path
                raw_text = detail.get("text") or raw_text
                title = detail.get("title") or title
                alert_date = detail.get("date") or alert_date
                pdf_url = detail.get("pdf_url")
                pdf_raw_path = detail.get("pdf_raw_file_path")
                pdf_text = detail.get("pdf_text")

            combined_text = clean_text(" ".join(text for text in [title, row_text, raw_text, pdf_text] if text))
            resources.append(
                ScrapedResource(
                    source_name=self.source_name,
                    source_url=self.start_url,
                    resource_type="safety_alert",
                    title=title,
                    url=url,
                    accessed_at=index.accessed_at,
                    raw_path=raw_path,
                    content_text=combined_text or None,
                    metadata={
                        "date": alert_date.isoformat() if alert_date else None,
                        "summary": row_text or None,
                        "organization": "AEMPS",
                        "alert_type": "Safety",
                        "pdf_url": pdf_url,
                        "pdf_raw_file_path": pdf_raw_path,
                        "possible_active_ingredients": detect_possible_active_ingredients(combined_text),
                    },
                    parser_version=self.parser_version,
                )
            )
            if len(resources) >= limit:
                break
        return resources

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            metadata = resource.metadata or {}
            if resource.resource_type == "source_error":
                rows.append(resource.as_dict())
                continue
            rows.append(
                {
                    "record_type": "safety_alert",
                    "title": resource.title,
                    "date": metadata.get("date"),
                    "url": resource.url,
                    "organization": metadata.get("organization"),
                    "alert_type": metadata.get("alert_type"),
                    "summary": metadata.get("summary"),
                    "raw_text": resource.content_text,
                    "pdf_url": metadata.get("pdf_url"),
                    "pdf_raw_file_path": metadata.get("pdf_raw_file_path"),
                    "possible_active_ingredients": metadata.get("possible_active_ingredients", []),
                    **resource.traceability(),
                }
            )
        return rows

    def _fetch_detail(self, url: str) -> dict[str, Any]:
        detail = self.fetch_url(url)
        if detail.error:
            return {"text": None, "raw_file_path": detail.raw_file_path, "error": detail.error}

        content_type = (detail.content_type or "").casefold()
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            text = _extract_pdf_text_safe(Path(detail.raw_file_path)) if detail.raw_file_path else None
            return {"text": text, "raw_file_path": detail.raw_file_path, "pdf_url": url, "pdf_raw_file_path": detail.raw_file_path, "pdf_text": text}

        soup = BeautifulSoup(detail.text or "", "html.parser")
        main = soup.select_one("main") or soup.body or soup
        title = clean_text((soup.select_one("h1") or soup.select_one("title") or main).get_text(" "))
        text = clean_text(main.get_text(" "))
        dates = extract_dates(text)
        pdf_url = None
        pdf_raw_path = None
        pdf_text = None
        for link in soup.select("a[href]"):
            href = link.get("href") or ""
            link_text = clean_text(link.get_text(" "))
            if ".pdf" in href.lower() or "pdf" in link_text.casefold():
                pdf_url = self.absolutize(href, url)
                pdf_fetch = self.fetch_url(pdf_url, ".pdf")
                pdf_raw_path = pdf_fetch.raw_file_path
                if pdf_raw_path:
                    pdf_text = _extract_pdf_text_safe(Path(pdf_raw_path))
                break
        return {
            "title": title or None,
            "text": text,
            "date": dates[0] if dates else None,
            "raw_file_path": detail.raw_file_path,
            "pdf_url": pdf_url,
            "pdf_raw_file_path": pdf_raw_path,
            "pdf_text": pdf_text,
        }

    def _looks_like_alert_link(self, url: str, title: str) -> bool:
        text = f"{url} {title}".casefold()
        if "aemps.gob.es" not in url:
            return False
        # Exclude clearly non-alert pages (general info, legislation, etc.)
        exclude = {"legislacion", "ilegal", "medicamento ilegal", "estupefaciente", "no sustituible",
                   "evaluacion de tecnologia", "investigacion con medicamento", "cima",
                   "problemas de suministro", "situaciones especiales", "arbitraje",
                   "oficina de apoyo", "observatorio", "publicaciones de medicamento"}
        if any(w in text for w in exclude):
            return False
        # Accept anything security/pharmacovigilance related
        terms = ["seguridad", "nota", "muh", "medicamento", "farmacovigilancia", "alerta", "riesgo", "retirada"]
        return len(title) > 12 and any(term in text for term in terms)


def detect_possible_active_ingredients(text: str | None, max_items: int = 20) -> list[str]:
    if not text:
        return []
    candidates: set[str] = set()
    for match in ACTIVE_INGREDIENT_CONTEXT_RE.finditer(text):
        fragment = match.group(1)
        for piece in re.split(r",|;| y | e |/|\(|\)", fragment):
            candidate = _clean_candidate(piece)
            if candidate:
                candidates.add(candidate)
    for match in PHARMA_SUFFIX_RE.finditer(text):
        candidate = _clean_candidate(match.group(0))
        if candidate:
            candidates.add(candidate)
    return sorted(candidates)[:max_items]


def _clean_candidate(value: str) -> str | None:
    text = clean_text(value).strip(" .:-")
    normalized = normalize_drug_name(text)
    if not normalized or normalized in ACTIVE_INGREDIENT_STOPWORDS:
        return None
    if len(normalized) < 4 or len(normalized.split()) > 4:
        return None
    return text


def _extract_pdf_text_safe(path: Path | None) -> str | None:
    if not path:
        return None
    try:
        return extract_pdf_text(path)
    except Exception:
        return None


AEMPSSafetyScraper = AempsSafetyAlertsScraper

