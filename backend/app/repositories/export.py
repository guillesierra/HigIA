from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import ATCCode, AlertDrug, ConsumptionRecord, Drug, DrugATC, SafetyAlert, Source, StudyDocument, StudyDrug


EXPORT_MODELS = {
    "sources": Source,
    "drugs": Drug,
    "atc": ATCCode,
    "alerts": SafetyAlert,
    "consumption": ConsumptionRecord,
    "studies": StudyDocument,
}


def export_public_json(db: Session, output_dir: Path) -> list[Path]:
    """Export publishable tables to JSON for static frontend mode."""
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
    return written


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
