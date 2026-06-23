from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    ATCCode,
    AlertDrug,
    ConsumptionRecord,
    Drug,
    DrugATC,
    SafetyAlert,
    Source,
    StudyDocument,
)
from app.normalizers.safety_alerts import (
    KNOWN_ATC_CODES,
    detect_atc_codes,
    detect_known_ingredients,
    detect_possible_drug_names,
    normalize_alert_record,
)
from app.normalizers.text import normalize_name, parse_date
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


def get_or_create_drug(db: Session, name: str, active_ingredient: str | None = None) -> Drug:
    normalized = normalize_name(name)
    if not normalized:
        normalized = normalize_name(name)
    existing = db.scalar(select(Drug).where(Drug.normalized_name == normalized))
    if existing:
        if active_ingredient and not existing.active_ingredient:
            existing.active_ingredient = active_ingredient
            db.flush()
        return existing
    drug = Drug(
        name=name,
        active_ingredient=active_ingredient,
        normalized_name=normalized,
    )
    db.add(drug)
    db.flush()
    return drug


def get_or_create_atc(db: Session, code: str, name: str = "") -> ATCCode | None:
    if not code or len(code) < 3:
        return None
    existing = db.scalar(select(ATCCode).where(ATCCode.code == code))
    if existing:
        return existing
    atc = ATCCode(
        code=code,
        name=name or KNOWN_ATC_CODES.get(code, code),
        level=1 + sum(1 for ch in code if ch.isalpha()),
        parent_code=code[:-1] if len(code) > 1 and code[-1].isalpha() else (code[:-2] if len(code) > 2 else None),
    )
    db.add(atc)
    try:
        db.flush()
    except Exception:
        db.rollback()
        return db.scalar(select(ATCCode).where(ATCCode.code == code))
    return atc


def link_drug_to_atc(db: Session, drug: Drug, atc_code: str) -> None:
    atc = get_or_create_atc(db, atc_code)
    if not atc:
        return
    existing = db.scalar(
        select(DrugATC).where(DrugATC.drug_id == drug.id, DrugATC.atc_code_id == atc.id)
    )
    if not existing:
        db.add(DrugATC(drug_id=drug.id, atc_code_id=atc.id))
        db.flush()


def link_alert_to_drug(db: Session, alert_id: int, drug: Drug) -> None:
    existing = db.scalar(
        select(AlertDrug).where(AlertDrug.alert_id == alert_id, AlertDrug.drug_id == drug.id)
    )
    if not existing:
        db.add(AlertDrug(alert_id=alert_id, drug_id=drug.id, atc_code_id=None))
        db.flush()


def link_alert_to_atc(db: Session, alert_id: int, atc_code: str) -> None:
    atc = get_or_create_atc(db, atc_code)
    if not atc:
        return
    existing = db.scalar(
        select(AlertDrug).where(AlertDrug.alert_id == alert_id, AlertDrug.atc_code_id == atc.id)
    )
    if not existing:
        db.add(AlertDrug(alert_id=alert_id, drug_id=None, atc_code_id=atc.id))
        db.flush()


def _auto_link_alert(db: Session, alert_id: int, raw_text: str | None) -> None:
    if not raw_text:
        return
    text = str(raw_text)
    atc_codes = detect_atc_codes(text)
    for code in atc_codes:
        link_alert_to_atc(db, alert_id, code)
    ingredients = detect_known_ingredients(text)
    for ingredient in ingredients:
        drug = get_or_create_drug(db, ingredient, ingredient)
        link_alert_to_drug(db, alert_id, drug)
    drug_names = detect_possible_drug_names(text)
    for dname in drug_names[:10]:
        drug = get_or_create_drug(db, dname, None)
        link_alert_to_drug(db, alert_id, drug)
    for code in atc_codes:
        name = KNOWN_ATC_CODES.get(code)
        if name:
            drug = get_or_create_drug(db, name, name)
            link_alert_to_drug(db, alert_id, drug)
            link_drug_to_atc(db, drug, code)


def _auto_link_consumption(db: Session, record: dict[str, Any]) -> None:
    drug_name = str(record.get("drug_name") or "")
    active_ingredient = str(record.get("active_ingredient") or "")
    atc_code = str(record.get("atc_code") or "")
    if drug_name or active_ingredient:
        dname = drug_name or active_ingredient
        drug = get_or_create_drug(db, dname, active_ingredient or None)
        if atc_code:
            link_drug_to_atc(db, drug, atc_code)


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
    alert = SafetyAlert(
        source_id=source.id,
        source_name=resource.source_name,
        source_url=resource.source_url,
        accessed_at=resource.accessed_at,
        raw_file_path=resource.raw_path,
        parser_version=resource.parser_version,
        **normalized,
    )
    db.add(alert)
    db.flush()
    _auto_link_alert(db, alert.id, resource.content_text or str(metadata.get("row_text", "")))


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


def _fuzzy_duplicate_score(title_a: str, title_b: str) -> float:
    na = normalize_name(title_a)
    nb = normalize_name(title_b)
    if not na or not nb:
        return 0.0
    set_a = set(na.split())
    set_b = set(nb.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _check_alert_duplicate(db: Session, title: str, url: str) -> bool:
    if url:
        existing = db.scalar(select(SafetyAlert).where(SafetyAlert.url == url))
        if existing:
            return True
    if not title:
        return False
    recent_alerts = db.scalars(
        select(SafetyAlert)
        .order_by(SafetyAlert.date.desc())
        .limit(200)
    ).all()
    for alert in recent_alerts:
        if _fuzzy_duplicate_score(title, alert.title) > 0.85:
            return True
    return False


def _check_study_duplicate(db: Session, title: str, url: str) -> bool:
    if url:
        existing = db.scalar(select(StudyDocument).where(StudyDocument.url == url))
        if existing:
            return True
    if not title:
        return False
    recent = db.scalars(
        select(StudyDocument)
        .order_by(StudyDocument.year.desc())
        .limit(200)
    ).all()
    for doc in recent:
        if _fuzzy_duplicate_score(title, doc.title) > 0.85:
            return True
    return False


def persist_normalized_records(db: Session, records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"sources": 0, "alerts": 0, "consumption": 0, "studies": 0, "errors": 0, "drugs_linked": 0, "atc_linked": 0}
    for record in records:
        record_type = str(record.get("record_type") or "")
        if record_type in {"error", "source_error"}:
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
                _auto_link_consumption(db, record)
                counts["drugs_linked"] += 1
        elif record_type == "atc_code":
            code = str(record.get("code", ""))
            name = str(record.get("name", ""))
            if code and get_or_create_atc(db, code, name):
                counts["atc_linked"] += 1
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
    title = str(record.get("title") or "")
    if not url or _check_alert_duplicate(db, title, url):
        return False
    alert = SafetyAlert(
        source_id=source.id,
        title=title,
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
    db.add(alert)
    db.flush()
    _auto_link_alert(db, alert.id, _none(record.get("raw_text")) or _none(record.get("summary")) or "")
    return True


def _persist_normalized_consumption(db: Session, source: Source, record: dict[str, Any]) -> bool:
    year = _to_int(record.get("year"))
    if year is None:
        return False
    source_url = _none(record.get("source_url"))
    parser_version = _none(record.get("parser_version"))
    month = _to_int(record.get("month"))
    geography = str(record.get("geography") or "Spain")
    sector = _none(record.get("sector"))
    category = _none(record.get("category"))
    atc_code = _none(record.get("atc_code"))
    drug_name = _none(record.get("drug_name"))
    existing = db.scalar(
        select(ConsumptionRecord).where(
            ConsumptionRecord.source_url == source_url,
            ConsumptionRecord.parser_version == parser_version,
            ConsumptionRecord.year == year,
            ConsumptionRecord.month == month,
            ConsumptionRecord.geography == geography,
            ConsumptionRecord.sector == sector,
            ConsumptionRecord.category == category,
            ConsumptionRecord.atc_code == atc_code,
            ConsumptionRecord.drug_name == drug_name,
        )
    )
    if existing:
        return False
    db.add(
        ConsumptionRecord(
            source_id=source.id,
            source_name=_none(record.get("source_name")),
            source_url=source_url,
            accessed_at=_parse_datetime(record.get("accessed_at")),
            raw_file_path=_none(record.get("raw_file_path")),
            parser_version=parser_version,
            year=year,
            month=month,
            geography=geography,
            geography_type=str(record.get("geography_type") or "country"),
            population_group=_none(record.get("population_group")),
            sector=sector,
            category=category,
            atc_code=atc_code,
            drug_name=drug_name,
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
    title = str(record.get("title") or "Untitled public document")
    if _check_study_duplicate(db, title, url or ""):
        return False
    db.add(
        StudyDocument(
            source_id=source.id,
            title=title,
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
