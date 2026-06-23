from collections import defaultdict
from decimal import Decimal
from statistics import mean
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.domain import ConsumptionRecord, SafetyAlert
from app.schemas.domain import ComparisonResponse


def compare_consumption_before_after_alert(
    db: Session,
    alert_id: int,
    metric: str = "dhd",
    atc_code: str | None = None,
    drug_name: str | None = None,
    window_years: int = 2,
) -> ComparisonResponse:
    alert = db.get(SafetyAlert, alert_id)
    if alert is None:
        raise ValueError("Alert not found")

    alert_year = alert.date.year if alert.date else None
    if alert_year is None:
        return ComparisonResponse(
            alert_id=alert.id,
            alert_title=alert.title,
            alert_year=None,
            metric=metric,
            before_average=None,
            after_average=None,
            before_records=0,
            after_records=0,
            delta=None,
            filters={"atc_code": atc_code, "drug_name": drug_name, "window_years": window_years},
        )

    before_stmt = _filtered_stmt(metric, atc_code, drug_name).where(
        ConsumptionRecord.year >= alert_year - window_years,
        ConsumptionRecord.year < alert_year,
    )
    after_stmt = _filtered_stmt(metric, atc_code, drug_name).where(
        ConsumptionRecord.year > alert_year,
        ConsumptionRecord.year <= alert_year + window_years,
    )

    before_values = [float(value) for value in db.scalars(before_stmt).all() if value is not None]
    after_values = [float(value) for value in db.scalars(after_stmt).all() if value is not None]
    before_average = mean(before_values) if before_values else None
    after_average = mean(after_values) if after_values else None
    delta = after_average - before_average if before_average is not None and after_average is not None else None

    return ComparisonResponse(
        alert_id=alert.id,
        alert_title=alert.title,
        alert_year=alert_year,
        metric=metric,
        before_average=before_average,
        after_average=after_average,
        before_records=len(before_values),
        after_records=len(after_values),
        delta=delta,
        filters={"atc_code": atc_code, "drug_name": drug_name, "window_years": window_years},
    )


def geographies_around_alert(
    db: Session,
    alert_id: int,
    metric: str = "dhd",
    atc_code: str | None = None,
    window_years: int = 3,
) -> list[dict[str, Any]]:
    alert = db.get(SafetyAlert, alert_id)
    if alert is None or alert.date is None:
        return []
    alert_year = alert.date.year
    metric_column = getattr(ConsumptionRecord, metric, None)
    if metric_column is None:
        return []

    stmt = select(
        ConsumptionRecord.geography,
        func.avg(metric_column).label("avg_metric"),
        func.count().label("record_count"),
    ).where(
        ConsumptionRecord.year.between(alert_year - window_years, alert_year + window_years),
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    stmt = stmt.group_by(ConsumptionRecord.geography).order_by(func.avg(metric_column).desc())

    rows = db.execute(stmt).all()
    return [
        {
            "geography": row.geography,
            "avg_metric": float(row.avg_metric) if row.avg_metric else 0,
            "record_count": row.record_count,
        }
        for row in rows
    ]


def time_series_around_alert(
    db: Session,
    alert_id: int,
    metric: str = "dhd",
    atc_code: str | None = None,
    window_years: int = 4,
) -> list[dict[str, Any]]:
    alert = db.get(SafetyAlert, alert_id)
    if alert is None or alert.date is None:
        return []
    alert_year = alert.date.year
    metric_column = getattr(ConsumptionRecord, metric, None)
    if metric_column is None:
        return []

    stmt = (
        select(
            ConsumptionRecord.year,
            ConsumptionRecord.geography,
            func.avg(metric_column).label("avg_metric"),
        )
        .where(
            ConsumptionRecord.year.between(alert_year - window_years, alert_year + window_years),
        )
        .group_by(ConsumptionRecord.year, ConsumptionRecord.geography)
        .order_by(ConsumptionRecord.year)
    )
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))

    rows = db.execute(stmt).all()
    series: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        series[row.year].append({
            "geography": row.geography,
            "avg_metric": float(row.avg_metric) if row.avg_metric else 0,
        })

    return [
        {
            "year": year,
            "is_alert_year": year == alert_year,
            "breakdown": data,
        }
        for year, data in sorted(series.items())
    ]


def _filtered_stmt(metric: str, atc_code: str | None, drug_name: str | None) -> Select[tuple[object]]:
    metric_column = getattr(ConsumptionRecord, metric, None)
    if metric_column is None:
        raise ValueError(f"Unsupported metric: {metric}")

    stmt = select(metric_column)
    if atc_code:
        stmt = stmt.where(ConsumptionRecord.atc_code.ilike(f"{atc_code}%"))
    if drug_name:
        stmt = stmt.where(ConsumptionRecord.drug_name.ilike(f"%{drug_name}%"))
    return stmt

