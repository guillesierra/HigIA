from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.init_db import reset_db
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def seeded_database() -> Generator[None, None, None]:
    reset_db()
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)

