from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    ATCCode,
    AlertDrug,
    ConsumptionRecord,
    Drug,
    DrugATC,
    SafetyAlert,
    Source,
    StudyDocument,
    StudyDrug,
)
from app.normalizers.text import normalize_name


def seed_demo_data(db: Session) -> None:
    """Insert small public-domain-like demo data for local development."""
    existing = db.scalar(select(Source).limit(1))
    if existing:
        return

    aemps = Source(
        name="AEMPS medicine safety notes",
        url="https://www.aemps.gob.es/comunicacion/notas-de-seguridad/notas-informativas-de-seguridad-de-medicamentos-de-uso-humano/",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Seed source. Real scraper stores raw HTML/PDF and extraction notes.",
    )
    sanidad = Source(
        name="Ministry of Health medicine consumption by ATC",
        url="https://www.sanidad.gob.es/gabinete/notasPrensa.do?id=5655",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Seed source for aggregated SNS consumption metrics.",
    )
    pran = Source(
        name="PRAN antibiotic consumption maps",
        url="https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumos-antibioticos-humana",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Seed source for human antibiotic consumption pages.",
    )
    asturias = Source(
        name="Asturias public pharmacotherapeutic documents",
        url="https://www.astursalud.es/",
        source_type="official_web",
        license="Check source terms before redistribution",
        accessed_at=datetime.utcnow(),
        notes="Seed source for public Asturias documents. No internal SESPA data included.",
    )
    db.add_all([aemps, sanidad, pran, asturias])
    db.flush()

    amoxicillin = Drug(
        name="Amoxicillin",
        active_ingredient="amoxicillin",
        normalized_name=normalize_name("Amoxicillin"),
    )
    diazepam = Drug(
        name="Diazepam",
        active_ingredient="diazepam",
        normalized_name=normalize_name("Diazepam"),
    )
    omeprazole = Drug(
        name="Omeprazole",
        active_ingredient="omeprazole",
        normalized_name=normalize_name("Omeprazole"),
    )
    db.add_all([amoxicillin, diazepam, omeprazole])

    j01 = ATCCode(code="J01", level=2, name="Antibacterials for systemic use", parent_code="J")
    j01ca = ATCCode(code="J01CA", level=4, name="Penicillins with extended spectrum", parent_code="J01")
    n05ba = ATCCode(code="N05BA", level=4, name="Benzodiazepine derivatives", parent_code="N05B")
    a02bc = ATCCode(code="A02BC", level=4, name="Proton pump inhibitors", parent_code="A02B")
    db.add_all([j01, j01ca, n05ba, a02bc])
    db.flush()

    db.add_all(
        [
            DrugATC(drug=amoxicillin, atc_code=j01ca),
            DrugATC(drug=diazepam, atc_code=n05ba),
            DrugATC(drug=omeprazole, atc_code=a02bc),
        ]
    )

    alert = SafetyAlert(
        source=aemps,
        title="Example safety note related to benzodiazepine risk minimization",
        date=date(2021, 6, 15),
        url="https://www.aemps.gob.es/comunicacion/notas-de-seguridad/",
        organization="AEMPS",
        alert_type="Safety",
        summary="Demo alert used to validate relations and before/after views.",
        raw_text="Demo text mentioning diazepam and benzodiazepines.",
    )
    db.add(alert)
    db.flush()
    db.add(AlertDrug(alert=alert, drug=diazepam, atc_code=n05ba))

    rows = [
        (2019, "Spain", "country", "J01CA", "Amoxicillin", "amoxicillin", Decimal("13.8"), Decimal("2100000")),
        (2020, "Spain", "country", "J01CA", "Amoxicillin", "amoxicillin", Decimal("12.4"), Decimal("1970000")),
        (2021, "Spain", "country", "N05BA", "Diazepam", "diazepam", Decimal("18.1"), Decimal("890000")),
        (2022, "Spain", "country", "N05BA", "Diazepam", "diazepam", Decimal("17.2"), Decimal("850000")),
        (2023, "Asturias", "autonomous_community", "J01CA", "Amoxicillin", "amoxicillin", Decimal("11.9"), Decimal("42000")),
        (2024, "Asturias", "autonomous_community", "J01CA", "Amoxicillin", "amoxicillin", Decimal("11.1"), Decimal("40100")),
        (2023, "Spain", "country", "A02BC", "Omeprazole", "omeprazole", Decimal("45.4"), Decimal("4200000")),
        (2024, "Spain", "country", "A02BC", "Omeprazole", "omeprazole", Decimal("44.7"), Decimal("4100000")),
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
                notes="Demo aggregated record. Replace with normalized public data.",
            )
        )

    study = StudyDocument(
        source=asturias,
        title="Demo Asturias public document inventory for medicine use",
        authors="HigIA seed",
        year=2024,
        url="https://www.astursalud.es/",
        document_type="public_document_inventory",
        geography="Asturias",
        summary="Placeholder record showing where public Asturias documents will appear.",
        conclusions="No internal SESPA data is included in the public MVP.",
        pending_work="Review public PDFs and only normalize data that can be extracted reliably.",
    )
    db.add(study)
    db.flush()
    db.add(StudyDrug(study=study, drug=amoxicillin, atc_code=j01ca))

    db.commit()

