from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.correlations import compute_correlations
from app.analytics.timeseries import compute_trend_analysis, detect_trend_changes
from app.models.domain import ATCCode, AlertDrug, ConsumptionRecord, Drug, DrugATC, SafetyAlert, Source, StudyDocument, StudyDrug

CORRELATION_SERIES_LIMIT = 250
MIN_ANALYTICS_YEARS = 8


EXPORT_MODELS = {
    "sources": Source,
    "drugs": Drug,
    "atc": ATCCode,
    "alerts": SafetyAlert,
    "consumption": ConsumptionRecord,
    "studies": StudyDocument,
}


def export_public_json(db: Session, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in EXPORT_MODELS.items():
        rows = db.scalars(select(model)).all()
        path = output_dir / f"{name}.json"
        path.write_text(
            json.dumps([_model_to_dict(row) for row in rows], default=_json_default, indent=2),
            encoding="utf-8",
        )
        written.append(path)
    relationships_path = output_dir / "relationships.json"
    relationships_path.write_text(
        json.dumps(_relationships(db), default=_json_default, indent=2),
        encoding="utf-8",
    )
    written.append(relationships_path)

    trends_path = output_dir / "trends.json"
    trends = _compute_trends_export(db)
    trends_path.write_text(json.dumps(trends, default=_json_default, indent=2), encoding="utf-8")
    written.append(trends_path)

    correlations_path = output_dir / "correlations.json"
    corrs = _compute_correlations_export(db)
    correlations_path.write_text(json.dumps(corrs, default=_json_default, indent=2), encoding="utf-8")
    written.append(correlations_path)

    anomalies_path = output_dir / "anomalies.json"
    anomalies = _compute_anomalies_export(db)
    anomalies_path.write_text(json.dumps(anomalies, default=_json_default, indent=2), encoding="utf-8")
    written.append(anomalies_path)

    summary_path = output_dir / "summary.json"
    summary = _compute_summary_export(db)
    summary_path.write_text(json.dumps(summary, default=_json_default, indent=2), encoding="utf-8")
    written.append(summary_path)

    return written


def _compute_trends_export(db: Session) -> list[dict[str, Any]]:
    series_map = _annual_ccaa_atc_series_map(db)
    trends = compute_trend_analysis(series_map, "dhd")
    return [
        {
            "entity_key": t.entity_key,
            "slope": t.slope,
            "mean_value": t.mean_value,
            "total_change": t.total_change,
            "avg_yoy_change": t.avg_yoy_change,
            "trend_direction": t.trend_direction,
            "years": t.years,
            "values": t.values,
        }
        for t in trends if t.trend_direction != "stable" and len(t.years) >= MIN_ANALYTICS_YEARS
    ][:50]


def _compute_correlations_export(db: Session) -> list[dict[str, Any]]:
    series_map = _limit_series_for_correlations(_annual_ccaa_atc_series_map(db))
    correlations = compute_correlations(series_map, min_common_years=3)
    return [
        {"entity_a": c.entity_a, "entity_b": c.entity_b, "correlation": c.correlation, "common_years": c.common_years}
        for c in correlations[:30]
    ]


def _compute_anomalies_export(db: Session) -> list[dict[str, Any]]:
    series_map = _annual_ccaa_atc_series_map(db)
    anomalies = detect_trend_changes(series_map, change_threshold=20.0)
    return anomalies[:30]


def _annual_ccaa_atc_series_map(db: Session) -> dict[str, dict[int, float]]:
    rows = db.execute(
        select(
            ConsumptionRecord.atc_code,
            ConsumptionRecord.geography,
            ConsumptionRecord.year,
            func.avg(ConsumptionRecord.dhd).label("avg_val"),
        )
        .where(
            ConsumptionRecord.atc_code.is_not(None),
            ConsumptionRecord.dhd.is_not(None),
            ConsumptionRecord.month.is_(None),
            ConsumptionRecord.sector == "Recetas SNS ATC",
            ConsumptionRecord.geography_type == "autonomous_community",
        )
        .group_by(ConsumptionRecord.atc_code, ConsumptionRecord.geography, ConsumptionRecord.year)
        .order_by(ConsumptionRecord.year)
    ).all()
    series_map: dict[str, dict[int, float]] = {}
    for row in rows:
        key = f"{row.geography}|{row.atc_code}"
        if key not in series_map:
            series_map[key] = {}
        if row.avg_val:
            series_map[key][row.year] = float(row.avg_val)
    return series_map


def _limit_series_for_correlations(series_map: dict[str, dict[int, float]]) -> dict[str, dict[int, float]]:
    ranked = sorted(
        ((key, values) for key, values in series_map.items() if len(values) >= MIN_ANALYTICS_YEARS),
        key=lambda item: (
            -len(item[1]),
            -sum(item[1].values()) / max(len(item[1]), 1),
            item[0],
        ),
    )
    return dict(ranked[:CORRELATION_SERIES_LIMIT])


def _compute_summary_export(db: Session) -> dict[str, Any]:
    total_alerts = db.scalar(select(func.count(SafetyAlert.id)))
    total_sources = db.scalar(select(func.count(Source.id)))
    total_consumption = db.scalar(select(func.count(ConsumptionRecord.id)))
    total_studies = db.scalar(select(func.count(StudyDocument.id)))
    total_drugs = db.scalar(select(func.count(Drug.id)))
    total_atc = db.scalar(select(func.count(ATCCode.id)))

    year_range = db.execute(
        select(func.min(ConsumptionRecord.year), func.max(ConsumptionRecord.year))
    ).first()

    geos = db.execute(
        select(ConsumptionRecord.geography, func.count().label("cnt"))
        .group_by(ConsumptionRecord.geography)
        .order_by(func.count().desc())
    ).all()

    alert_years = db.execute(
        select(SafetyAlert.date, func.count().label("cnt"))
        .where(SafetyAlert.date.is_not(None))
        .group_by(SafetyAlert.date)
        .order_by(SafetyAlert.date)
    ).all()

    return {
        "counts": {
            "sources": total_sources,
            "alerts": total_alerts,
            "consumption_records": total_consumption,
            "studies": total_studies,
            "drugs": total_drugs,
            "atc_codes": total_atc,
        },
        "year_range": {"min": year_range[0], "max": year_range[1]} if year_range else None,
        "top_geographies": [
            {"name": g.geography, "records": g.cnt} for g in geos[:10]
        ],
        "alerts_timeline": [
            {"year": row.date.year, "count": row.cnt}
            for row in alert_years if row.date
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def _model_to_dict(row: object) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _json_default(value: object) -> str | float | None:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return None


def _relationships(db: Session) -> dict[str, list[dict[str, Any]]]:
    return {
        "drug_atc": [_model_to_dict(row) for row in db.scalars(select(DrugATC)).all()],
        "alert_drugs": [_model_to_dict(row) for row in db.scalars(select(AlertDrug)).all()],
        "study_drugs": [_model_to_dict(row) for row in db.scalars(select(StudyDrug)).all()],
        "atc_consumption": [
            {
                "atc_code": row.atc_code,
                "consumption_record_id": row.id,
                "drug_name": row.drug_name,
                "year": row.year,
                "geography": row.geography,
            }
            for row in db.scalars(select(ConsumptionRecord).where(ConsumptionRecord.atc_code.is_not(None))).all()
        ],
    }
