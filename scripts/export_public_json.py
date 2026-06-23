import argparse
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.repositories.export import export_public_json  # noqa: E402


PUBLIC_DIR = ROOT / "data" / "processed" / "public"
FRONTEND_PUBLIC_DIR = ROOT / "frontend" / "public" / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export SQLite data to static public JSON.")
    parser.add_argument("--output-dir", type=Path, default=PUBLIC_DIR)
    parser.add_argument("--frontend-public", action="store_true", help="Copy JSON exports to frontend/public/data.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    create_db()
    with SessionLocal() as db:
        written = export_public_json(db, args.output_dir)
    print("Wrote:")
    for path in written:
        print(f" - {path}")

    if args.frontend_public:
        FRONTEND_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        for path in written:
            shutil.copy2(path, FRONTEND_PUBLIC_DIR / path.name)
        print(f"Copied JSON files to {FRONTEND_PUBLIC_DIR}")


if __name__ == "__main__":
    main()

