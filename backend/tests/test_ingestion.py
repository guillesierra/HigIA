from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.domain import ConsumptionRecord
from app.repositories.ingestion import persist_normalized_records


def test_persist_consumption_updates_existing_parser_version_without_duplicate() -> None:
    source_url = "https://example.test/pran-dedupe"
    base_record = {
        "record_type": "consumption",
        "source_name": "PRAN test source",
        "source_url": source_url,
        "accessed_at": "2026-06-25T10:00:00",
        "raw_file_path": "raw/old.json",
        "parser_version": "parser-0.1",
        "year": 2021,
        "month": None,
        "geography": "Asturias",
        "geography_type": "autonomous_community",
        "sector": "Comunitario",
        "category": "Global comunitario",
        "atc_code": "J01",
        "drug_name": None,
        "active_ingredient": None,
        "dhd": "20.0",
        "unit": "DHD",
        "notes": "Old parser output.",
    }
    updated_record = {
        **base_record,
        "accessed_at": "2026-06-25T11:00:00",
        "raw_file_path": "raw/new.json",
        "parser_version": "parser-0.2",
        "dhd": "21.5",
        "notes": "New parser output.",
    }

    with SessionLocal() as db:
        first_counts = persist_normalized_records(db, [base_record])
        second_counts = persist_normalized_records(db, [updated_record])
        rows = db.scalars(
            select(ConsumptionRecord).where(
                ConsumptionRecord.source_url == source_url,
                ConsumptionRecord.year == 2021,
                ConsumptionRecord.geography == "Asturias",
                ConsumptionRecord.atc_code == "J01",
            )
        ).all()

    assert first_counts["consumption"] == 1
    assert second_counts["consumption"] == 0
    assert len(rows) == 1
    assert rows[0].parser_version == "parser-0.2"
    assert rows[0].raw_file_path == "raw/new.json"
    assert rows[0].dhd == Decimal("21.5000")
