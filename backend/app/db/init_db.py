from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models import domain  # noqa: F401


def create_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def reset_db() -> None:
    """Drop and recreate all tables for local development."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def ensure_db(session: Session | None = None) -> None:
    """Create tables. The optional session keeps script call sites simple."""
    create_db()

