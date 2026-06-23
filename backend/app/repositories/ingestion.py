from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import ConsumptionRecord, SafetyAlert, Source, StudyDocument
from app.normalizers.safety_alerts import normalize_alert_record
from app.normalizers.text import parse_date
from app.scrapers.base import ScrapedResource


def get_or_create_source(db: Session, resource: ScrapedResource) -> Source:
    source = db.scalar(select(Source).where(Source.url == resource.source_url))
    if source:
        source.accessed_at = resource.accessed_at
        return source
    source = Source(
        name=resource.source_name,
        url=resource.source_url,
        source_type="official_web" if resource.source_url.startswith("http") else "manual_local",
        license="Check source terms before redistribution",
        accessed_at=resource.accessed_at,
        notes="Created by scraper. Review extraction notes before publishing raw data.",
    )
    db.add(source)
    db.flush()
    return source


def persist_resources(db: Session, resources: list[ScrapedResource]) -> dict[str, int]:
    counts = {"sources": 0, "alerts": 0, "studies": 0}
    seen_sources: set[str] = set()
    for resource in resources:
        source = get_or_create_source(db, resource)
        if source.url not in seen_sources:
            counts["sources"] += 1
            seen_sources.add(source.url)

        if resource.resource_type == "safety_alert":
            _persist_alert(db, source, resource)
            counts["alerts"] += 1
        elif resource.resource_type in {"document", "manual_document", "dataset_link", "source_error"}:
            _persist_study_or_document(db, source, resource)
            counts["studies"] += 1
    db.commit()
    return counts


def _persist_alert(db: Session, source: Source, resource: ScrapedResource) -> None:
    if db.scalar(select(SafetyAlert).where(SafetyAlert.url == resource.url)):
        return
    metadata = resource.metadata or {}
    normalized = normalize_alert_record(
        {
            "title": resource.title,
            "date": metadata.get("date"),
            "url": resource.url,
            "organization": metadata.get("organization", "AEMPS"),
            "alert_type": metadata.get("alert_type", "Safety"),
            "summary": metadata.get("row_text"),
            "raw_text": resource.content_text,
        }
    )
    db.add(
        SafetyAlert(
            source_id=source.id,
            source_name=resource.source_name,
            source_url=resource.source_url,
            accessed_at=resource.accessed_at,
            raw_file_path=resource.raw_path,
            parser_version=resource.parser_version,
            **normalized,
        )
    )


def _persist_study_or_document(db: Session, source: Source, resource: ScrapedResource) -> None:
    if db.scalar(select(StudyDocument).where(StudyDocument.url == resource.url)):
        return
    metadata = resource.metadata or {}
    year = metadata.get("year")
    db.add(
        StudyDocument(
            source_id=source.id,
            title=resource.title,
            authors=str(metadata.get("authors") or "") or None,
            year=int(year) if isinstance(year, int) else None,
            url=resource.url,
            document_type=resource.resource_type,
            geography="Asturias" if "astur" in resource.source_name.casefold() else None,
            summary=resource.content_text[:1000] if resource.content_text else str(metadata)[:1000],
            conclusions=None,
            pending_work=_pending_work(resource, metadata),
            source_name=resource.source_name,
            source_url=resource.source_url,
            accessed_at=resource.accessed_at,
            raw_file_path=resource.raw_path,
            parser_version=resource.parser_version,
            therapeutic_group=str(metadata.get("therapeutic_group") or "") or None,
        )
    )


def _pending_work(resource: ScrapedResource, metadata: dict[str, object]) -> str:
    if "error" in metadata:
        return f"Scrape error at {datetime.utcnow().isoformat()}: {metadata['error']}"
    if metadata.get("requires_parser"):
        return "A source-specific parser is required before structured normalization."
    if metadata.get("requires_manual_review"):
        return "Manual review required before structured extraction."
    return "Review license and extraction quality before publishing."


def persist_normalized_records(db: Session, records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"sources": 0, "alerts": 0, "consumption": 0, "studies": 0, "errors": 0}
    for record in records:
        record_type = str(record.get("record_type") or "")
        if record_type == "error" or record_type == "source_error":
            counts["errors"] += 1
            continue
        source = get_or_create_source_from_record(db, record)
        counts["sources"] += 1
        if record_type == "safety_alert":
            if _persist_normalized_alert(db, source, record):
                counts["alerts"] += 1
        elif record_type == "consumption":
            if _persist_normalized_consumption(db, source, record):
                counts["consumption"] += 1
        elif record_type in {"study_document", "document", "source_page", "dataset_link", "html_tables"}:
            if _persist_normalized_study(db, source, record):
                counts["studies"] += 1
    db.commit()
    return counts


def get_or_create_source_from_record(db: Session, record: dict[str, Any]) -> Source:
    source_url = str(record.get("source_url") or record.get("url") or "local://unknown")
    source = db.scalar(select(Source).where(Source.url == source_url))
    accessed_at = _parse_datetime(record.get("accessed_at")) or datetime.utcnow()
    if source:
        source.accessed_at = accessed_at
        return source
    source = Source(
        name=str(record.get("source_name") or "Unknown public source"),
        url=source_url,
        source_type="official_web" if source_url.startswith("http") else "manual_local",
        license="Check source terms before redistribution",
        accessed_at=accessed_at,
        notes=f"Created from normalized scraper output. Parser: {record.get('parser_version')}",
    )
    db.add(source)
    db.flush()
    return source


def _persist_normalized_alert(db: Session, source: Source, record: dict[str, Any]) -> bool:
    url = str(record.get("url") or "")
    if not url or db.scalar(select(SafetyAlert).where(SafetyAlert.url == url)):
        return False
    db.add(
        SafetyAlert(
            source_id=source.id,
            title=str(record.get("title") or ""),
            date=_parse_date(record.get("date")),
            url=url,
            organization=_none(record.get("organization")),
            alert_type=_none(record.get("alert_type")),
            summary=_none(record.get("summary")),
            raw_text=_none(record.get("raw_text")),
            source_name=_none(record.get("source_name")),
            source_url=_none(record.get("source_url")),
            accessed_at=_parse_datetime(record.get("accessed_at")),
            raw_file_path=_none(record.get("raw_file_path")),
            parser_version=_none(record.get("parser_version")),
        )
    )
    return True


def _persist_normalized_consumption(db: Session, source: Source, record: dict[str, Any]) -> bool:
    year = _to_int(record.get("year"))
    if year is None:
        return False
    db.add(
        ConsumptionRecord(
            source_id=source.id,
            source_name=_none(record.get("source_name")),
            source_url=_none(record.get("source_url")),
            accessed_at=_parse_datetime(record.get("accessed_at")),
            raw_file_path=_none(record.get("raw_file_path")),
            parser_version=_none(record.get("parser_version")),
            year=year,
            month=_to_int(record.get("month")),
            geography=str(record.get("geography") or "Spain"),
            geography_type=str(record.get("geography_type") or "country"),
            population_group=_none(record.get("population_group")),
            sector=_none(record.get("sector")),
            category=_none(record.get("category")),
            atc_code=_none(record.get("atc_code")),
            drug_name=_none(record.get("drug_name")),
            active_ingredient=_none(record.get("active_ingredient")),
            packages=_to_decimal(record.get("packages")),
            ddd=_to_decimal(record.get("ddd")),
            dhd=_to_decimal(record.get("dhd")),
            amount_pvpiva=_to_decimal(record.get("amount_pvpiva")),
            unit=_none(record.get("unit")),
            notes=_none(record.get("notes") or record.get("therapeutic_group")),
        )
    )
    return True


def _persist_normalized_study(db: Session, source: Source, record: dict[str, Any]) -> bool:
    url = _none(record.get("url"))
    if url and db.scalar(select(StudyDocument).where(StudyDocument.url == url)):
        return False
    db.add(
        StudyDocument(
            source_id=source.id,
            title=str(record.get("title") or "Untitled public document"),
            authors=_none(record.get("authors")),
            year=_to_int(record.get("year")),
            url=url,
            document_type=_none(record.get("document_type") or record.get("record_type")),
            geography=_none(record.get("geography")),
            period_start=_parse_date(record.get("period_start")),
            period_end=_parse_date(record.get("period_end")),
            summary=_none(record.get("summary")),
            conclusions=_none(record.get("conclusions")),
            pending_work=_none(record.get("pending_work") or "Review extraction quality before structured use."),
            source_name=_none(record.get("source_name")),
            source_url=_none(record.get("source_url")),
            accessed_at=_parse_datetime(record.get("accessed_at")),
            raw_file_path=_none(record.get("raw_file_path")),
            parser_version=_none(record.get("parser_version")),
            therapeutic_group=_none(record.get("therapeutic_group")),
        )
    )
    return True


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    return parse_date(str(value)) if value else None


def _to_int(value: object) -> int | None:
    if _is_empty(value):
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _to_decimal(value: object) -> Decimal | None:
    if _is_empty(value):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _none(value: object) -> str | None:
    if _is_empty(value):
        return None
    return str(value)


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(value == "")
    except Exception:
        return False
