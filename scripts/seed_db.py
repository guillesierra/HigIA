from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db  # noqa: E402


def main() -> None:
    create_db()
    print("Database schema ready. No demo data inserted.")


if __name__ == "__main__":
    main()
