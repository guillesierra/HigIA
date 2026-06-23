from collections import defaultdict
from datetime import date
from statistics import median, stdev
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.analytics.correlations import compute_correlations, correlate_alerts_with_consumption
from app.analytics.timeseries import compute_trend_analysis, compute_year_over_year, detect_trend_changes
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
from app.validators.report import ValidationReportGenerator


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


@router.get("/analytics/trends")
def consumption_trends(
    db: DbSession,
    atc_code: str | None = None,
    geography: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    min_years: int = Query(default=2, ge=2, le=20),
) -> list[dict]:
    stmt = (
        select(
            ConsumptionRecord.atc_code,
            ConsumptionRecord.geography,
            ConsumptionRecord.year,
            func.avg(getattr(ConsumptionRecord, metric)).label("avg_val"),
        )
        .where(ConsumptionRecord.atc_code.is_not(None))
        .group_by(ConsumptionRecord.atc_code, ConsumptionRecord.geography, ConsumptionRecord.year)
        .order_by(ConsumptionRecord.year)
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    if geography:
        stmt = stmt.where(ConsumptionRecord.geography.ilike(f"%{geography}%"))

    rows = db.execute(stmt).all()
    series_map: dict[str, dict[int, float]] = {}
    for row in rows:
        key = f"{row.geography}|{row.atc_code}"
        if key not in series_map:
            series_map[key] = {}
        series_map[key][row.year] = float(row.avg_val) if row.avg_val else 0.0

    trends = compute_trend_analysis(series_map, metric)
    significant = sorted(
        [t for t in trends if t.trend_direction != "stable" and t.avg_yoy_change != 0],
        key=lambda t: abs(t.avg_yoy_change),
        reverse=True,
    )
    return [{
        "entity_key": t.entity_key,
        "metric": t.metric,
        "years": t.years,
        "values": t.values,
        "slope": t.slope,
        "mean_value": t.mean_value,
        "total_change": t.total_change,
        "avg_yoy_change": t.avg_yoy_change,
        "trend_direction": t.trend_direction,
        "start_value": t.start_value,
        "end_value": t.end_value,
    } for t in significant[:30]]


@router.get("/analytics/correlations")
def consumption_correlations(
    db: DbSession,
    atc_code: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    min_years: int = Query(default=3, ge=3, le=20),
    limit: int = Query(default=20, le=100),
) -> list[dict]:
    stmt = (
        select(
            ConsumptionRecord.atc_code,
            ConsumptionRecord.geography,
            ConsumptionRecord.year,
            func.avg(getattr(ConsumptionRecord, metric)).label("avg_val"),
        )
        .where(ConsumptionRecord.atc_code.is_not(None))
        .group_by(ConsumptionRecord.atc_code, ConsumptionRecord.geography, ConsumptionRecord.year)
        .order_by(ConsumptionRecord.year)
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))

    rows = db.execute(stmt).all()
    series_map: dict[str, dict[int, float]] = {}
    for row in rows:
        key = f"{row.geography}|{row.atc_code}"
        if key not in series_map:
            series_map[key] = {}
        series_map[key][row.year] = float(row.avg_val) if row.avg_val else 0.0

    correlations = compute_correlations(series_map, min_years)
    return [{
        "entity_a": c.entity_a,
        "entity_b": c.entity_b,
        "correlation": c.correlation,
        "common_years": c.common_years,
    } for c in correlations[:limit]]


@router.get("/analytics/alerts-impact")
def alerts_consumption_impact(
    db: DbSession,
    atc_code: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    window_years: int = Query(default=2, ge=1, le=5),
) -> list[dict]:
    alert_years_rows = db.execute(
        select(SafetyAlert.date).where(SafetyAlert.date.is_not(None))
    ).all()
    alert_years: dict[int, int] = defaultdict(int)
    for row in alert_years_rows:
        y = row.date.year
        alert_years[y] += 1

    stmt = (
        select(
            ConsumptionRecord.atc_code,
            ConsumptionRecord.geography,
            ConsumptionRecord.year,
            func.avg(getattr(ConsumptionRecord, metric)).label("avg_val"),
        )
        .where(ConsumptionRecord.atc_code.is_not(None))
        .group_by(ConsumptionRecord.atc_code, ConsumptionRecord.geography, ConsumptionRecord.year)
        .order_by(ConsumptionRecord.year)
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))

    rows = db.execute(stmt).all()
    series_map: dict[str, dict[int, float]] = {}
    for row in rows:
        key = f"{row.geography}|{row.atc_code}"
        if key not in series_map:
            series_map[key] = {}
        series_map[key][row.year] = float(row.avg_val) if row.avg_val else 0.0

    impacts = correlate_alerts_with_consumption(alert_years, series_map, window_years)
    return impacts[:30]


@router.get("/analytics/year-over-year")
def year_over_year_changes(
    db: DbSession,
    atc_code: str | None = None,
    geography: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    limit: int = Query(default=30, le=100),
) -> list[dict]:
    stmt = (
        select(
            ConsumptionRecord.atc_code,
            ConsumptionRecord.geography,
            ConsumptionRecord.year,
            func.avg(getattr(ConsumptionRecord, metric)).label("avg_val"),
        )
        .where(ConsumptionRecord.atc_code.is_not(None))
        .group_by(ConsumptionRecord.atc_code, ConsumptionRecord.geography, ConsumptionRecord.year)
        .order_by(ConsumptionRecord.year)
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    if geography:
        stmt = stmt.where(ConsumptionRecord.geography.ilike(f"%{geography}%"))

    rows = db.execute(stmt).all()
    series_map: dict[str, dict[int, float]] = {}
    for row in rows:
        key = f"{row.geography}|{row.atc_code}"
        if key not in series_map:
            series_map[key] = {}
        series_map[key][row.year] = float(row.avg_val) if row.avg_val else 0.0

    yoy = compute_year_over_year(series_map)
    return sorted(yoy, key=lambda x: abs(x["change_pct"]), reverse=True)[:limit]


@router.get("/analytics/anomalies")
def trend_anomalies(
    db: DbSession,
    atc_code: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    threshold: float = Query(default=25.0, ge=5.0, le=100.0),
    limit: int = Query(default=20, le=50),
) -> list[dict]:
    stmt = (
        select(
            ConsumptionRecord.atc_code,
            ConsumptionRecord.geography,
            ConsumptionRecord.year,
            func.avg(getattr(ConsumptionRecord, metric)).label("avg_val"),
        )
        .where(ConsumptionRecord.atc_code.is_not(None))
        .group_by(ConsumptionRecord.atc_code, ConsumptionRecord.geography, ConsumptionRecord.year)
        .order_by(ConsumptionRecord.year)
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))

    rows = db.execute(stmt).all()
    series_map: dict[str, dict[int, float]] = {}
    for row in rows:
        key = f"{row.geography}|{row.atc_code}"
        if key not in series_map:
            series_map[key] = {}
        series_map[key][row.year] = float(row.avg_val) if row.avg_val else 0.0

    anomalies = detect_trend_changes(series_map, threshold)
    return anomalies[:limit]


@router.get("/analytics/geography-comparison")
def geography_comparison(
    db: DbSession,
    atc_code: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
    year: int | None = None,
) -> list[dict]:
    metric_col = getattr(ConsumptionRecord, metric)
    stmt = (
        select(
            ConsumptionRecord.geography,
            ConsumptionRecord.atc_code,
            func.avg(metric_col).label("avg_val"),
            func.count().label("record_count"),
        )
        .where(ConsumptionRecord.atc_code.is_not(None))
        .group_by(ConsumptionRecord.geography, ConsumptionRecord.atc_code)
        .order_by(ConsumptionRecord.geography, func.avg(metric_col).desc())
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    if year:
        stmt = stmt.where(ConsumptionRecord.year == year)

    rows = db.execute(stmt).all()
    results: dict[str, list] = defaultdict(list)
    for row in rows:
        results[row.geography].append({
            "atc_code": row.atc_code,
            "avg_value": float(row.avg_val) if row.avg_val else 0,
            "record_count": row.record_count,
        })
    return [
        {"geography": geo, "codes": codes[:10]}
        for geo, codes in sorted(results.items())
    ]


@router.get("/analytics/summary-stats")
def summary_statistics(
    db: DbSession,
    atc_code: str | None = None,
    metric: str = Query(default="dhd", pattern="^(dhd|ddd|packages|amount_pvpiva)$"),
) -> dict:
    metric_col = getattr(ConsumptionRecord, metric)
    stmt = select(
        func.count().label("total"),
        func.avg(metric_col).label("avg"),
        func.max(metric_col).label("max"),
        func.min(metric_col).label("min"),
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))

    row = db.execute(stmt).first()
    if row is None or not row.total:
        return {"total": 0, "avg": None, "max": None, "min": None}

    values_stmt = select(metric_col).where(metric_col.is_not(None))
    if atc_code:
        values_stmt = values_stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    all_vals = [float(v) for v in db.scalars(values_stmt).all()]

    year_range_stmt = select(func.min(ConsumptionRecord.year), func.max(ConsumptionRecord.year))
    if atc_code:
        year_range_stmt = year_range_stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    year_row = db.execute(year_range_stmt).first()

    geo_stmt = select(func.count(func.distinct(ConsumptionRecord.geography)))
    if atc_code:
        geo_stmt = geo_stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    geo_count = db.scalar(geo_stmt)

    return {
        "total_records": row.total,
        "avg_value": float(row.avg) if row.avg else None,
        "max_value": float(row.max) if row.max else None,
        "min_value": float(row.min) if row.min else None,
        "median": round(median(all_vals), 4) if len(all_vals) > 0 else None,
        "stdev": round(stdev(all_vals), 4) if len(all_vals) > 1 else 0,
        "year_range": {"min": year_row[0], "max": year_row[1]} if year_row else None,
        "distinct_geographies": geo_count,
    }


@router.get("/validation/reports")
def list_validation_reports() -> list[dict]:
    return ValidationReportGenerator.load_all_validation_reports()


@router.get("/validation/latest")
def latest_validation(source: str | None = None) -> list[dict]:
    if source:
        report = ValidationReportGenerator.load_latest_validation(source)
        return [report] if report else []
    return ValidationReportGenerator.load_all_validation_reports()
