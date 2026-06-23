import argparse
import json
from pathlib import Path
import shutil
import sys

from sqlalchemy import func, select


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.domain import ATCCode, ConsumptionRecord, Drug, SafetyAlert, Source, StudyDocument  # noqa: E402
from app.repositories.export import export_public_json  # noqa: E402


PUBLIC_DIR = ROOT / "data" / "processed" / "public"
FRONTEND_PUBLIC_DIR = ROOT / "frontend" / "public" / "data"
PUBLIC_COUNT_FILES = {
    "sources": "sources.json",
    "alerts": "alerts.json",
    "consumption_records": "consumption.json",
    "studies": "studies.json",
    "drugs": "drugs.json",
    "atc_codes": "atc.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export SQLite data to static public JSON.")
    parser.add_argument("--output-dir", type=Path, default=PUBLIC_DIR)
    parser.add_argument("--frontend-public", action="store_true", help="Copy JSON exports to frontend/public/data.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow exports that reduce existing public JSON record counts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    create_db()
    with SessionLocal() as db:
        _guard_against_accidental_shrink(db, args.output_dir, args.force)
        written = export_public_json(db, args.output_dir)
    print("Wrote:")
    for path in written:
        print(f" - {path}")

    if args.frontend_public:
        FRONTEND_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        for path in written:
            shutil.copy2(path, FRONTEND_PUBLIC_DIR / path.name)
        print(f"Copied JSON files to {FRONTEND_PUBLIC_DIR}")


def _guard_against_accidental_shrink(db, output_dir: Path, force: bool) -> None:
    if force:
        return
    existing = _existing_public_counts(output_dir)
    if not existing:
        return
    current = {
        "sources": db.scalar(select(func.count(Source.id))) or 0,
        "alerts": db.scalar(select(func.count(SafetyAlert.id))) or 0,
        "consumption_records": db.scalar(select(func.count(ConsumptionRecord.id))) or 0,
        "studies": db.scalar(select(func.count(StudyDocument.id))) or 0,
        "drugs": db.scalar(select(func.count(Drug.id))) or 0,
        "atc_codes": db.scalar(select(func.count(ATCCode.id))) or 0,
    }
    shrinking = {
        key: (existing_count, current.get(key, 0))
        for key, existing_count in existing.items()
        if current.get(key, 0) < existing_count
    }
    if not shrinking:
        return
    details = ", ".join(
        f"{key}: existing {old} > database {new}" for key, (old, new) in sorted(shrinking.items())
    )
    raise SystemExit(
        "Refusing to overwrite public JSON with fewer records. "
        f"{details}. Rebuild/import the full database first, or rerun with --force if this reduction is intentional."
    )


def _existing_public_counts(output_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, filename in PUBLIC_COUNT_FILES.items():
        path = output_dir / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            counts[key] = len(data)
    return counts


if __name__ == "__main__":
    main()
