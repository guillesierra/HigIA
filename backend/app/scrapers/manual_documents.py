from datetime import datetime
from typing import Any

from app.normalizers.documents import extract_pdf_text, infer_document_metadata
from app.scrapers.base import BaseScraper, PROJECT_ROOT, ScrapedResource


MANUAL_DIR = PROJECT_ROOT / "data" / "raw" / "manual"


class ManualDocumentIngester(BaseScraper):
    source_name = "Manual local public documents"
    base_url = "local://data/raw/manual"
    start_url = "local://data/raw/manual"
    raw_subdir = "manual"
    parser_version = "manual-documents-0.3"

    def __init__(
        self,
        timeout: float = 15,
        delay_seconds: float = 0,
        respect_robots: bool = False,
        verify_ssl: bool | str = True,
    ) -> None:
        super().__init__(
            timeout=timeout,
            delay_seconds=delay_seconds,
            respect_robots=respect_robots,
            verify_ssl=verify_ssl,
        )

    def parse(self, limit: int = 100, **_: Any) -> list[ScrapedResource]:
        MANUAL_DIR.mkdir(parents=True, exist_ok=True)
        resources: list[ScrapedResource] = []
        for path in sorted(MANUAL_DIR.glob("*.pdf"))[:limit]:
            try:
                text = extract_pdf_text(path)
                metadata = infer_document_metadata(path, text)
            except Exception as exc:
                text = None
                metadata = {"error": str(exc), "pending_work": "Manual review required."}
            resources.append(
                ScrapedResource(
                    source_name=self.source_name,
                    source_url=str(path),
                    resource_type="study_document",
                    title=str(metadata.get("title") or path.stem),
                    url=str(path),
                    accessed_at=datetime.utcnow(),
                    raw_path=str(path),
                    content_text=text,
                    metadata=metadata,
                    parser_version=self.parser_version,
                )
            )
        return resources

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows = []
        for resource in resources:
            metadata = resource.metadata or {}
            rows.append(
                {
                    "record_type": "study_document",
                    "title": resource.title,
                    "authors": metadata.get("authors"),
                    "year": metadata.get("year"),
                    "url": resource.url,
                    "document_type": metadata.get("document_type") or "manual_pdf",
                    "geography": metadata.get("geography"),
                    "period_start": None,
                    "period_end": None,
                    "summary": metadata.get("summary") or (resource.content_text or "")[:1000] or None,
                    "conclusions": None,
                    "pending_work": metadata.get("pending_work"),
                    "therapeutic_group": metadata.get("therapeutic_group"),
                    **resource.traceability(),
                }
            )
        return rows
