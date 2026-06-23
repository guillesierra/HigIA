"""Import normalized scraper JSON records into the HigIA SQLite database."""
import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import delete


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.domain import ConsumptionRecord  # noqa: E402
from app.repositories.ingestion import persist_normalized_records  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized scraper JSON into SQLite.")
    parser.add_argument("paths", nargs="+", type=Path, help="JSON files containing normalized records.")
    parser.add_argument(
        "--replace-consumption-parser",
        action="append",
        default=[],
        help="Delete existing consumption rows for this parser_version before importing.",
    )
    parser.add_argument(
        "--purge-untraced-consumption",
        action="store_true",
        help="Delete consumption rows without source_name, raw_file_path, or parser_version.",
    )
    return parser.parse_args()


def load_records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]
    if isinstance(data, dict):
        for key in ("records", "items", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [record for record in value if isinstance(record, dict)]
    raise ValueError(f"{path} does not contain a list of records")


def main() -> None:
    args = parse_args()
    create_db()
    all_records: list[dict] = []
    for path in args.paths:
        records = load_records(path)
        all_records.extend(records)
        print(f"Loaded {len(records)} records from {path}")

    with SessionLocal() as db:
        if args.purge_untraced_consumption:
            result = db.execute(
                delete(ConsumptionRecord).where(
                    (ConsumptionRecord.source_name.is_(None))
                    | (ConsumptionRecord.raw_file_path.is_(None))
                    | (ConsumptionRecord.parser_version.is_(None))
                )
            )
            print(f"Purged untraced consumption rows: {result.rowcount}")
        for parser_version in args.replace_consumption_parser:
            result = db.execute(
                delete(ConsumptionRecord).where(ConsumptionRecord.parser_version == parser_version)
            )
            print(f"Purged consumption rows for {parser_version}: {result.rowcount}")
        db.commit()

        counts = persist_normalized_records(db, all_records)
    print(f"Persisted: {counts}")


if __name__ == "__main__":
    main()
