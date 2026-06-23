from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import ATCCode, ConsumptionRecord, Drug, SafetyAlert, Source, StudyDocument
from app.schemas.domain import (
    ATCCodeRead,
    ComparisonResponse,
    ConsumptionRecordRead,
    DrugRead,
    RelationshipResponse,
    SafetyAlertRead,
    SourceRead,
    StudyDocumentRead,
)
from app.services.comparison import compare_consumption_before_after_alert
from app.services.relationships import relationship_for_alert, relationship_for_atc, relationship_for_drug


router = APIRouter(prefix="/api")
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sources", response_model=list[SourceRead])
def list_sources(db: DbSession) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.name)).all())


@router.get("/drugs", response_model=list[DrugRead])
def list_drugs(db: DbSession, q: str | None = None, limit: int = Query(default=100, le=500)) -> list[Drug]:
    stmt = select(Drug).order_by(Drug.name).limit(limit)
    if q:
        stmt = stmt.where(
            or_(
                Drug.name.ilike(f"%{q}%"),
                Drug.active_ingredient.ilike(f"%{q}%"),
                Drug.normalized_name.ilike(f"%{q.lower()}%"),
            )
        )
    return list(db.scalars(stmt).all())


@router.get("/atc", response_model=list[ATCCodeRead])
def list_atc_codes(db: DbSession, q: str | None = None, level: int | None = None, limit: int = Query(default=200, le=1000)) -> list[ATCCode]:
    stmt = select(ATCCode).order_by(ATCCode.code).limit(limit)
    if q:
        stmt = stmt.where(or_(ATCCode.code.ilike(f"{q}%"), ATCCode.name.ilike(f"%{q}%")))
    if level:
        stmt = stmt.where(ATCCode.level == level)
    return list(db.scalars(stmt).all())


@router.get("/alerts", response_model=list[SafetyAlertRead])
def list_alerts(
    db: DbSession,
    q: str | None = None,
    year: int | None = None,
    organization: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[SafetyAlert]:
    stmt = select(SafetyAlert).order_by(SafetyAlert.date.desc(), SafetyAlert.id.desc()).limit(limit)
    if q:
        stmt = stmt.where(
            or_(
                SafetyAlert.title.ilike(f"%{q}%"),
                SafetyAlert.summary.ilike(f"%{q}%"),
                SafetyAlert.raw_text.ilike(f"%{q}%"),
            )
        )
    if year:
        stmt = stmt.where(SafetyAlert.date.between(date(year, 1, 1), date(year, 12, 31)))
    if organization:
        stmt = stmt.where(SafetyAlert.organization.ilike(f"%{organization}%"))
    return list(db.scalars(stmt).all())


@router.get("/alerts/search", response_model=list[SafetyAlertRead])
def search_alerts(
    db: DbSession,
    medicine: str | None = None,
    active_ingredient: str | None = None,
    atc: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[SafetyAlert]:
    terms = [term for term in [medicine, active_ingredient, atc, q] if term]
    stmt = select(SafetyAlert).order_by(SafetyAlert.date.desc()).limit(limit)
    if terms:
        clauses = []
        for term in terms:
            clauses.extend(
                [
                    SafetyAlert.title.ilike(f"%{term}%"),
                    SafetyAlert.summary.ilike(f"%{term}%"),
                    SafetyAlert.raw_text.ilike(f"%{term}%"),
                ]
            )
        stmt = stmt.where(or_(*clauses))
    return list(db.scalars(stmt).all())


@router.get("/consumption", response_model=list[ConsumptionRecordRead])
def list_consumption(
    db: DbSession,
    year: int | None = None,
    geography: str | None = None,
    geography_type: str | None = None,
    atc: str | None = None,
    medicine: str | None = None,
    active_ingredient: str | None = None,
    therapeutic_group: str | None = None,
    sector: str | None = None,
    category: str | None = None,
    limit: int = Query(default=500, le=2000),
) -> list[ConsumptionRecord]:
    stmt = select(ConsumptionRecord).order_by(ConsumptionRecord.year, ConsumptionRecord.geography).limit(limit)
    if year:
        stmt = stmt.where(ConsumptionRecord.year == year)
    if geography:
        stmt = stmt.where(ConsumptionRecord.geography.ilike(f"%{geography}%"))
    if geography_type:
        stmt = stmt.where(ConsumptionRecord.geography_type.ilike(f"%{geography_type}%"))
    if atc:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc}%"))
    if medicine:
        stmt = stmt.where(ConsumptionRecord.drug_name.ilike(f"%{medicine}%"))
    if active_ingredient:
        stmt = stmt.where(ConsumptionRecord.active_ingredient.ilike(f"%{active_ingredient}%"))
    if therapeutic_group:
        stmt = stmt.where(
            or_(
                ConsumptionRecord.atc_code.ilike(f"{therapeutic_group}%"),
                ConsumptionRecord.notes.ilike(f"%{therapeutic_group}%"),
            )
        )
    if sector:
        stmt = stmt.where(ConsumptionRecord.sector.ilike(f"%{sector}%"))
    if category:
        stmt = stmt.where(ConsumptionRecord.category.ilike(f"%{category}%"))
    return list(db.scalars(stmt).all())


@router.get("/consumption/compare-before-after", response_model=ComparisonResponse)
def compare_before_after(
    db: DbSession,
    alert_id: int,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    atc_code: str | None = None,
    drug_name: str | None = None,
    window_years: int = Query(default=2, ge=1, le=10),
) -> ComparisonResponse:
    try:
        return compare_consumption_before_after_alert(db, alert_id, metric, atc_code, drug_name, window_years)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/studies", response_model=list[StudyDocumentRead])
def list_studies(
    db: DbSession,
    q: str | None = None,
    geography: str | None = None,
    year: int | None = None,
    limit: int = Query(default=100, le=500),
) -> list[StudyDocument]:
    stmt = select(StudyDocument).order_by(StudyDocument.year.desc(), StudyDocument.title).limit(limit)
    if q:
        stmt = stmt.where(
            or_(
                StudyDocument.title.ilike(f"%{q}%"),
                StudyDocument.summary.ilike(f"%{q}%"),
                StudyDocument.conclusions.ilike(f"%{q}%"),
            )
        )
    if geography:
        stmt = stmt.where(StudyDocument.geography.ilike(f"%{geography}%"))
    if year:
        stmt = stmt.where(StudyDocument.year == year)
    return list(db.scalars(stmt).all())


@router.get("/relationships/drug/{query}", response_model=RelationshipResponse)
def drug_relationships(db: DbSession, query: str) -> RelationshipResponse:
    return relationship_for_drug(db, query)


@router.get("/relationships/atc/{code}", response_model=RelationshipResponse)
def atc_relationships(db: DbSession, code: str) -> RelationshipResponse:
    return relationship_for_atc(db, code)


@router.get("/relationships/alert/{alert_id}", response_model=RelationshipResponse)
def alert_relationships(db: DbSession, alert_id: int) -> RelationshipResponse:
    try:
        return relationship_for_alert(db, alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
