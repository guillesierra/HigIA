import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.repositories.ingestion import persist_normalized_records  # noqa: E402
from app.scrapers.aemps import AempsSafetyAlertsScraper  # noqa: E402
from app.scrapers.asturias import AsturiasPublicDocsScraper  # noqa: E402
from app.scrapers.manual_documents import ManualDocumentIngester  # noqa: E402
from app.scrapers.pran import PranAntibioticsScraper  # noqa: E402
from app.scrapers.sanidad import SanidadConsumptionScraper  # noqa: E402
from app.scrapers.universities import SpanishUniversityPublicationsScraper  # noqa: E402


SCRAPERS = {
    "aemps": AempsSafetyAlertsScraper,
    "sanidad": SanidadConsumptionScraper,
    "pran": PranAntibioticsScraper,
    "asturias": AsturiasPublicDocsScraper,
    "universities": SpanishUniversityPublicationsScraper,
    "manual": ManualDocumentIngester,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HigIA public-source scrapers.")
    parser.add_argument("--source", choices=[*SCRAPERS.keys(), "all"], default="all")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--persist", action="store_true", help="Persist discovered records to SQLite.")
    parser.add_argument("--no-details", action="store_true", help="Skip AEMPS detail pages.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between HTTP requests.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    create_db()
    selected = SCRAPERS.keys() if args.source == "all" else [args.source]
    all_records = []
    for name in selected:
        scraper = SCRAPERS[name](delay_seconds=args.delay) if name != "manual" else SCRAPERS[name]()
        if name == "aemps":
            records = scraper.run(limit=args.limit, fetch_details=not args.no_details)
        else:
            records = scraper.run(limit=args.limit)
        print(f"{name}: normalized {len(records)} records")
        all_records.extend(records)

    if args.persist:
        with SessionLocal() as db:
            counts = persist_normalized_records(db, all_records)
        print(f"Persisted: {counts}")


if __name__ == "__main__":
    main()
