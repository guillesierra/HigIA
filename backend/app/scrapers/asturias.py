from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.normalizers.documents import extract_pdf_text, infer_document_metadata
from app.normalizers.text import clean_text, extract_dates, infer_document_type, infer_geography, infer_therapeutic_group
from app.scrapers.base import BaseScraper, ScrapedResource


ASTURIAS_SEEDS = [
    "https://www.astursalud.es/",
    "https://www.astursalud.es/noticias",
    "https://oetspa.astursalud.es/",
    "https://huca.sespa.es/huca/web/contenidos/servicios/farmacia/GFT_HUCA.pdf",
]
ALLOWED_DOMAINS = {
    "www.astursalud.es",
    "astursalud.es",
    "oetspa.astursalud.es",
    "www.oetspa.astursalud.es",
    "sespa.es",
    "www.sespa.es",
    "huca.sespa.es",
}
ASTURIAS_KEYWORDS = {
    "medicamento",
    "medicamentos",
    "farmacia",
    "farmaceut",
    "antibiot",
    "proa",
    "benzodiacep",
    "psicof",
    "uso racional",
    "farmacovigilancia",
    "guia farmacoterapeutica",
}


class AsturiasPublicDocsScraper(BaseScraper):
    source_name = "Asturias public medicine-related documents"
    base_url = "https://www.astursalud.es"
    start_url = ASTURIAS_SEEDS[0]
    raw_subdir = "asturias"
    parser_version = "asturias-public-docs-0.3"

    def parse(self, limit: int = 50, max_pages: int = 25, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        queue: deque[tuple[str, int]] = deque((seed, 0) for seed in ASTURIAS_SEEDS)
        visited_pages: set[str] = set()
        seen_docs: set[str] = set()

        while queue and len(visited_pages) < max_pages and len(resources) < limit:
            url, depth = queue.popleft()
            if url in visited_pages or not _allowed_domain(url):
                continue
            visited_pages.add(url)

            if url.lower().endswith(".pdf"):
                resource = self._download_pdf(url, url, "Asturias public PDF")
                if resource:
                    resources.append(resource)
                continue

            page = self.fetch_url(url, ".html")
            if page.error:
                resources.append(self.error_resource(url, "page_fetch_failed", page.error))
                continue

            soup = BeautifulSoup(page.text or "", "html.parser")
            page_text = clean_text(soup.get_text(" "))
            for link in soup.select("a[href]"):
                href = link.get("href")
                if not href:
                    continue
                target = self.absolutize(href, url)
                title = clean_text(link.get_text(" ")) or target
                context = f"{title} {target} {page_text[:1000]}"
                if target.lower().endswith(".pdf"):
                    if target in seen_docs or not _looks_relevant(context):
                        continue
                    seen_docs.add(target)
                    resource = self._download_pdf(target, url, title)
                    if resource:
                        resources.append(resource)
                        if len(resources) >= limit:
                            break
                elif depth < 1 and _allowed_domain(target) and _looks_relevant(context):
                    queue.append((target, depth + 1))
        return resources[:limit]

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            if resource.resource_type == "source_error":
                rows.append(resource.as_dict())
                continue
            metadata = resource.metadata or {}
            text = resource.content_text
            if not text and resource.raw_path and Path(resource.raw_path).suffix.lower() == ".pdf":
                try:
                    text = extract_pdf_text(Path(resource.raw_path))
                except Exception as exc:
                    self.log_error("pdf_text_extraction_failed", resource.url, exc)
            inferred = infer_document_metadata(Path(resource.raw_path or resource.url), text or "")
            context = f"{resource.title} {text or ''}"
            dates = extract_dates(context)
            rows.append(
                {
                    "record_type": "study_document",
                    "title": resource.title or inferred.get("title"),
                    "authors": None,
                    "year": inferred.get("year"),
                    "url": resource.url,
                    "document_type": infer_document_type(context, default=str(inferred.get("document_type") or "public_document")),
                    "geography": infer_geography(context, default="Asturias") or "Asturias",
                    "period_start": dates[0].isoformat() if dates else None,
                    "period_end": dates[-1].isoformat() if len(dates) > 1 else None,
                    "summary": (text or resource.content_text or "")[:1000] or None,
                    "conclusions": None,
                    "pending_work": "Manual review required before structured data extraction.",
                    "therapeutic_group": infer_therapeutic_group(context) or inferred.get("therapeutic_group"),
                    "keywords": metadata.get("keywords", []),
                    **resource.traceability(),
                }
            )
        return rows

    def _download_pdf(self, pdf_url: str, source_url: str, title: str) -> ScrapedResource | None:
        fetched = self.fetch_url(pdf_url, ".pdf")
        if fetched.error:
            return self.error_resource(pdf_url, "pdf_fetch_failed", fetched.error)
        text = None
        if fetched.raw_file_path:
            try:
                text = extract_pdf_text(Path(fetched.raw_file_path))
            except Exception as exc:
                self.log_error("pdf_text_extraction_failed", pdf_url, exc)
        context = f"{title} {pdf_url} {text or ''}"
        return ScrapedResource(
            source_name=self.source_name,
            source_url=source_url,
            resource_type="document",
            title=clean_text(title)[:300] or Path(urlparse(pdf_url).path).name,
            url=pdf_url,
            accessed_at=fetched.accessed_at,
            raw_path=fetched.raw_file_path,
            content_text=text,
            metadata={
                "keywords": sorted(keyword for keyword in ASTURIAS_KEYWORDS if keyword in context.casefold()),
                "document_type": infer_document_type(context),
                "geography": infer_geography(context, default="Asturias"),
                "therapeutic_group": infer_therapeutic_group(context),
            },
            parser_version=self.parser_version,
        )


def _allowed_domain(url: str) -> bool:
    host = urlparse(url).netloc.casefold()
    return not host or host in ALLOWED_DOMAINS


def _looks_relevant(value: str) -> bool:
    text = value.casefold()
    return any(keyword in text for keyword in ASTURIAS_KEYWORDS)


AsturiasDocumentScraper = AsturiasPublicDocsScraper

