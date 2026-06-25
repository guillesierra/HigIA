# ruff: noqa: E402
from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal
import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / ".test_higia.sqlite"
# DATABASE_URL must be set before importing app.db modules.
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

import pytest
from fastapi.testclient import TestClient

from app.db.init_db import reset_db
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.domain import ATCCode, AlertDrug, ConsumptionRecord, Drug, DrugATC, SafetyAlert, Source
from app.normalizers.text import normalize_name


@pytest.fixture(scope="session", autouse=True)
def seeded_database() -> Generator[None, None, None]:
    reset_db()
    with SessionLocal() as db:
        seed_test_data(db)
    yield
    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def seed_test_data(db) -> None:
    """Insert test-only fixtures. Runtime data must come from public scrapers."""
    aemps = Source(
        name="AEMPS medicine safety notes",
        url="https://www.aemps.gob.es/comunicacion/notas-de-seguridad/notas-informativas-de-seguridad-de-medicamentos-de-uso-humano/",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Test fixture source.",
    )
    sanidad = Source(
        name="Ministry of Health medicine consumption by ATC",
        url="https://www.sanidad.gob.es/gabinete/notasPrensa.do?id=5655",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Test fixture source.",
    )
    pran = Source(
        name="PRAN antibiotic consumption maps",
        url="https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumos-antibioticos-humana",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Test fixture source.",
    )
    asturias = Source(
        name="Asturias public pharmacotherapeutic documents",
        url="https://www.astursalud.es/",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Test fixture source.",
    )
    db.add_all([aemps, sanidad, pran, asturias])
    db.flush()

    amoxicillin = Drug(name="Amoxicillin", active_ingredient="amoxicillin", normalized_name=normalize_name("Amoxicillin"))
    diazepam = Drug(name="Diazepam", active_ingredient="diazepam", normalized_name=normalize_name("Diazepam"))
    db.add_all([amoxicillin, diazepam])

    j01ca = ATCCode(code="J01CA", level=4, name="Penicillins with extended spectrum", parent_code="J01")
    n05ba = ATCCode(code="N05BA", level=4, name="Benzodiazepine derivatives", parent_code="N05B")
    db.add_all([j01ca, n05ba])
    db.flush()

    db.add_all([DrugATC(drug=amoxicillin, atc_code=j01ca), DrugATC(drug=diazepam, atc_code=n05ba)])

    alert = SafetyAlert(
        source=aemps,
        title="Test safety note related to benzodiazepine risk minimization",
        date=date(2021, 6, 15),
        url="https://www.aemps.gob.es/comunicacion/notas-de-seguridad/test",
        organization="AEMPS",
        alert_type="Safety",
        summary="Test alert used to validate relations and before/after views.",
        raw_text="Test text mentioning diazepam and benzodiazepines.",
    )
    db.add(alert)
    db.flush()
    db.add(AlertDrug(alert=alert, drug=diazepam, atc_code=n05ba))

    rows = [
        (2021, "Spain", "country", "N05BA", "Diazepam", "diazepam", Decimal("18.1"), Decimal("890000")),
        (2022, "Spain", "country", "N05BA", "Diazepam", "diazepam", Decimal("17.2"), Decimal("850000")),
        (2023, "Asturias", "autonomous_community", "J01CA", "Amoxicillin", "amoxicillin", Decimal("11.9"), Decimal("42000")),
        (2024, "Asturias", "autonomous_community", "J01CA", "Amoxicillin", "amoxicillin", Decimal("11.1"), Decimal("40100")),
    ]
    for year, geography, geography_type, atc, drug, ingredient, dhd, packages in rows:
        db.add(
            ConsumptionRecord(
                source=sanidad if geography == "Spain" else pran,
                year=year,
                geography=geography,
                geography_type=geography_type,
                atc_code=atc,
                drug_name=drug,
                active_ingredient=ingredient,
                packages=packages,
                dhd=dhd,
                unit="DHD",
                notes="Test fixture record.",
            )
        )

    db.commit()
