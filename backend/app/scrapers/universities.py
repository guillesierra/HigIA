from __future__ import annotations

from collections import deque
from pathlib import Path
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.normalizers.documents import extract_pdf_text, infer_document_metadata
from app.normalizers.text import clean_text, extract_dates, extract_year, infer_document_type, infer_geography, infer_therapeutic_group
from app.scrapers.base import BaseScraper, ScrapedResource


UNIOVI_GENERIC_SEEDS = [
    "https://digibuo.uniovi.es/dspace/",
    "https://digibuo.uniovi.es/dspace/simple-search?query=antibioticos",
    "https://digibuo.uniovi.es/dspace/simple-search?query=medicamentos",
    "https://digibuo.uniovi.es/dspace/simple-search?query=farmacia",
    "https://digibuo.uniovi.es/dspace/simple-search?query=consumo%20antibioticos",
    "https://digibuo.uniovi.es/dspace/simple-search?query=DDD",
    "https://digibuo.uniovi.es/dspace/simple-search?query=DHD",
    "https://portalinvestigacion.uniovi.es/",
    "https://portalinvestigacion.uniovi.es/resultados/publicaciones",
    "https://portalinvestigacion.uniovi.es/resultados/tesis/anualidades",
]

UNIOVI_HIGH_SIGNAL_SEEDS = [
    "https://digibuo.uniovi.es/dspace/handle/10651/45002",
    "https://portalinvestigacion.uniovi.es/documentos/667c517a6de8e7265d987072?lang=en",
    "https://digibuo.uniovi.es/dspace/handle/10651/16740",
    "https://digibuo.uniovi.es/dspace/bitstream/10651/34879/1/TD_CristinaMariaSuarezCastanon.pdf",
    "https://digibuo.uniovi.es/dspace/bitstream/handle/10651/50389/TD_DiegoParraRuiz.pdf",
    "https://digibuo.uniovi.es/dspace/bitstream/handle/10651/13462/TD_pedrojavierguerrero.pdf?isAllowed=y&sequence=2",
    "https://digibuo.uniovi.es/dspace/bitstream/handle/10651/72580/2024_025_TD_PilarLumbrerasIglesias.pdf?isAllowed=y&sequence=1",
]

OTHER_SPANISH_UNIVERSITY_SEEDS = [
    "https://eprints.ucm.es/51527/",
    "https://repositorio.uam.es/",
    "https://idus.us.es/",
    "https://riunet.upv.es/",
    "https://digitum.um.es/",
    "https://e-spacio.uned.es/",
    "https://zaguan.unizar.es/",
    "https://diposit.ub.edu/",
]

UNIVERSITY_SEEDS = [
    *UNIOVI_GENERIC_SEEDS,
    *UNIOVI_HIGH_SIGNAL_SEEDS,
    *OTHER_SPANISH_UNIVERSITY_SEEDS,
]

ALLOWED_UNIVERSITY_DOMAINS = {
    "digibuo.uniovi.es",
    "portalinvestigacion.uniovi.es",
    "eprints.ucm.es",
    "repositorio.uam.es",
    "idus.us.es",
    "riunet.upv.es",
    "digitum.um.es",
    "e-spacio.uned.es",
    "zaguan.unizar.es",
    "diposit.ub.edu",
}

UNIVERSITY_KEYWORDS = {
    "medicamento",
    "medicamentos",
    "farmacia",
    "farmaceut",
    "antibiot",
    "antimicrob",
    "proa",
    "benzodiacep",
    "psicof",
    "farmacovigilancia",
    "uso racional",
    "atc",
    "ddd",
    "dhd",
    "consumo",
    "prescripcion",
}

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


class SpanishUniversityPublicationsScraper(BaseScraper):
    source_name = "Spanish university public medicine-related publications"
    base_url = "https://digibuo.uniovi.es"
    start_url = UNIVERSITY_SEEDS[0]
    raw_subdir = "universities"
    parser_version = "spanish-university-publications-0.1"

    def parse(self, limit: int = 50, max_pages: int = 35, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        queue: deque[tuple[str, int]] = deque((seed, 0) for seed in UNIVERSITY_SEEDS)
        visited: set[str] = set()

        while queue and len(visited) < max_pages and len(resources) < limit:
            url, depth = queue.popleft()
            if url in visited or not _allowed_domain(url):
                continue
            visited.add(url)

            if _is_pdf(url):
                resources.append(self._download_pdf(url, url, Path(urlparse(url).path).name))
                continue

            page = self.fetch_url(url, ".html")
            if page.error:
                resources.append(self.error_resource(url, "university_page_fetch_failed", page.error))
                continue

            soup = BeautifulSoup(page.text or "", "html.parser")
            page_text = clean_text(soup.get_text(" "))
            title = _title_from_page(soup, url)
            if _looks_relevant(f"{title} {page_text} {url}"):
                resources.append(
                    ScrapedResource(
                        source_name=self.source_name,
                        source_url=url,
                        resource_type="university_publication",
                        title=title,
                        url=url,
                        accessed_at=page.accessed_at,
                        raw_path=page.raw_file_path,
                        content_text=page_text,
                        metadata=_metadata_from_publication_page(soup, page_text, url),
                        parser_version=self.parser_version,
                    )
                )

            for link in soup.select("a[href]"):
                href = link.get("href")
                if not href:
                    continue
                target = self.absolutize(href, url)
                link_text = clean_text(link.get_text(" "))
                context = f"{link_text} {target} {page_text[:1200]}"
                if not _allowed_domain(target):
                    continue
                if _is_pdf(target) and _looks_relevant(context):
                    resources.append(self._download_pdf(target, url, link_text or Path(urlparse(target).path).name))
                    if len(resources) >= limit:
                        break
                elif depth < 1 and _looks_relevant(context):
                    queue.append((target, depth + 1))
        return resources[:limit]

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            if resource.resource_type == "source_error":
                rows.append(resource.as_dict())
                continue

            metadata = resource.metadata or {}
            text = resource.content_text or ""
            inferred = infer_document_metadata(Path(resource.raw_path or resource.url), text)
            context = f"{resource.title} {text}"
            dates = extract_dates(context)
            rows.append(
                {
                    "record_type": "study_document",
                    "title": resource.title or inferred.get("title"),
                    "authors": metadata.get("authors"),
                    "year": metadata.get("year") or extract_year(context),
                    "url": resource.url,
                    "document_type": metadata.get("document_type") or infer_document_type(context, default="academic_publication"),
                    "geography": metadata.get("geography") or infer_geography(context, default="Spain"),
                    "period_start": dates[0].isoformat() if dates else None,
                    "period_end": dates[-1].isoformat() if len(dates) > 1 else None,
                    "summary": metadata.get("abstract") or text[:1000] or None,
                    "conclusions": None,
                    "pending_work": "Review publication license and full-text extraction before structured data extraction.",
                    "therapeutic_group": metadata.get("therapeutic_group") or infer_therapeutic_group(context),
                    "doi": metadata.get("doi"),
                    "journal": metadata.get("journal"),
                    "external_full_text_url": metadata.get("external_full_text_url"),
                    "keywords": metadata.get("keywords", []),
                    **resource.traceability(),
                }
            )
        return rows

    def _download_pdf(self, pdf_url: str, source_url: str, title: str) -> ScrapedResource:
        fetched = self.fetch_url(pdf_url, ".pdf")
        if fetched.error:
            return self.error_resource(pdf_url, "university_pdf_fetch_failed", fetched.error)
        text = None
        if fetched.raw_file_path:
            try:
                text = extract_pdf_text(Path(fetched.raw_file_path))
            except Exception as exc:
                self.log_error("university_pdf_text_extraction_failed", pdf_url, exc)
        context = f"{title} {pdf_url} {text or ''}"
        return ScrapedResource(
            source_name=self.source_name,
            source_url=source_url,
            resource_type="university_publication",
            title=clean_text(title)[:300] or Path(urlparse(pdf_url).path).name,
            url=pdf_url,
            accessed_at=fetched.accessed_at,
            raw_path=fetched.raw_file_path,
            content_text=text,
            metadata={
                "document_type": infer_document_type(context, default="academic_pdf"),
                "geography": infer_geography(context, default="Spain"),
                "therapeutic_group": infer_therapeutic_group(context),
                "doi": _extract_doi(context),
                "keywords": sorted(keyword for keyword in UNIVERSITY_KEYWORDS if keyword in context.casefold()),
            },
            parser_version=self.parser_version,
        )


def _metadata_from_publication_page(soup: BeautifulSoup, text: str, url: str) -> dict[str, Any]:
    title = _title_from_page(soup, url)
    authors = _authors_from_page(soup)
    abstract = _abstract_from_page(soup, text)
    journal = _field_after_label(text, "Journal:")
    doi = _extract_doi(text)
    full_text = _full_text_link(soup, url)
    context = f"{title} {abstract} {text[:2000]}"
    return {
        "authors": authors,
        "abstract": abstract,
        "journal": journal,
        "year": _field_year(text),
        "document_type": infer_document_type(context, default="academic_publication"),
        "geography": infer_geography(context, default="Spain"),
        "therapeutic_group": infer_therapeutic_group(context),
        "doi": doi,
        "external_full_text_url": full_text,
        "keywords": sorted(keyword for keyword in UNIVERSITY_KEYWORDS if keyword in context.casefold()),
    }


def _title_from_page(soup: BeautifulSoup, fallback_url: str) -> str:
    node = soup.select_one("h1") or soup.select_one("title")
    return clean_text(node.get_text(" ")) if node else fallback_url


def _authors_from_page(soup: BeautifulSoup) -> str | None:
    authors = []
    for selector in ["meta[name='citation_author']", "meta[name='DC.creator']", "meta[name='dc.creator']"]:
        for node in soup.select(selector):
            value = node.get("content")
            if value:
                authors.append(clean_text(value))
    if authors:
        return "; ".join(dict.fromkeys(authors))
    return None


def _abstract_from_page(soup: BeautifulSoup, text: str) -> str | None:
    for selector in ["meta[name='citation_abstract']", "meta[name='description']", "meta[name='DC.description']"]:
        node = soup.select_one(selector)
        value = node.get("content") if node else None
        if value:
            return clean_text(value)
    marker = "Abstract"
    if marker in text:
        return clean_text(text.split(marker, 1)[1])[:1200]
    return None


def _field_after_label(text: str, label: str) -> str | None:
    if label not in text:
        return None
    tail = text.split(label, 1)[1].strip()
    return clean_text(tail.splitlines()[0])[:300] if tail else None


def _field_year(text: str) -> int | None:
    match = re.search(r"Year of publication:\s*((?:19|20)\d{2})", text)
    return int(match.group(1)) if match else extract_year(text)


def _full_text_link(soup: BeautifulSoup, base_url: str) -> str | None:
    for link in soup.select("a[href]"):
        label = clean_text(link.get_text(" ")).casefold()
        href = link.get("href")
        if href and ("full text" in label or "texto completo" in label or href.lower().endswith(".pdf")):
            return urljoin(base_url, href)
    return None


def _extract_doi(text: str) -> str | None:
    match = DOI_RE.search(text or "")
    return match.group(0) if match else None


def _allowed_domain(url: str) -> bool:
    host = urlparse(url).netloc.casefold()
    return not host or host in ALLOWED_UNIVERSITY_DOMAINS


def _looks_relevant(value: str) -> bool:
    text = value.casefold()
    return any(keyword in text for keyword in UNIVERSITY_KEYWORDS)


def _is_pdf(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


UniversityPublicationsScraper = SpanishUniversityPublicationsScraper
