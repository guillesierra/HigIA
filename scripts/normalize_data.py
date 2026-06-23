from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.domain import ConsumptionRecord, Source  # noqa: E402
from app.normalizers.consumption import normalize_consumption_dataframe  # noqa: E402


PROCESSED_DIR = ROOT / "data" / "processed"


def main() -> None:
    create_db()
    files = [*PROCESSED_DIR.rglob("*.csv"), *PROCESSED_DIR.rglob("*.xlsx")]
    if not files:
        print("No CSV/XLSX files found under data/processed. Nothing to normalize.")
        return

    with SessionLocal() as db:
        source = _normalization_source(db)
        inserted = 0
        for path in files:
            df = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
            records = normalize_consumption_dataframe(df, source.id)
            for record in records:
                db.add(ConsumptionRecord(**record))
            inserted += len(records)
        db.commit()
    print(f"Inserted {inserted} normalized consumption records.")


def _normalization_source(db):
    source = (
        db.query(Source)
        .filter(Source.url == "local://data/processed")
        .one_or_none()
    )
    if source:
        return source
    source = Source(
        name="Local processed public files",
        url="local://data/processed",
        source_type="manual_local",
        license="Review source file licenses before publication",
        notes="Created by normalize_data.py from files placed in data/processed.",
    )
    db.add(source)
    db.flush()
    return source


if __name__ == "__main__":
    main()

