"""Fast export: skip DB, directly build static JSON from normalized data."""
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.init_db import reset_db
from app.db.session import SessionLocal
from app.repositories.ingestion import persist_normalized_records
from app.normalizers.safety_alerts import KNOWN_ATC_CODES, KNOWN_ACTIVE_INGREDIENTS, KNOWN_DRUG_NAMES
from app.repositories.ingestion import get_or_create_atc, get_or_create_drug, link_drug_to_atc
from app.models.domain import ATCCode, Drug, DrugATC, SafetyAlert
from sqlalchemy import select, func

PROCESSED = Path("data/processed")
PUBLIC = PROCESSED / "public"
FRONTEND = Path("frontend/public/data")
reset_db()

# ====== 1. ATC codes + drugs (fast, keep in DB) ======
print("1. ATC codes + drugs...")
with SessionLocal() as db:
    from app.scrapers.who_atc import get_embedded_atc_codes, EMBEDDED_ATC_NAMES
    for code, name in KNOWN_ATC_CODES.items():
        get_or_create_atc(db, code, name)
    for a in get_embedded_atc_codes():
        get_or_create_atc(db, a["code"], a["name"])
    for ing in KNOWN_ACTIVE_INGREDIENTS:
        get_or_create_drug(db, ing, ing)
    for dn in KNOWN_DRUG_NAMES:
        get_or_create_drug(db, dn, None)
    for code, name in KNOWN_ATC_CODES.items():
        atc_o = db.scalar(select(ATCCode).where(ATCCode.code == code))
        if not atc_o: continue
        from app.normalizers.text import normalize_name
        for ing in KNOWN_ACTIVE_INGREDIENTS:
            if normalize_name(ing) in normalize_name(name):
                drug = db.scalar(select(Drug).where(Drug.active_ingredient == ing))
                if drug:
                    ex = db.scalar(select(DrugATC).where(DrugATC.drug_id == drug.id, DrugATC.atc_code_id == atc_o.id))
                    if not ex: link_drug_to_atc(db, drug, code)
                break
    db.commit()

# Ingest alerts + studies
for src in ["aemps", "universities", "asturias", "sanidad", "pran"]:
    fp = PROCESSED / src / "latest_normalized.json"
    if fp.exists():
        r = json.loads(fp.read_text(encoding="utf-8"))
        with SessionLocal() as db: persist_normalized_records(db, r)

# ====== 2. Load real consumption data directly (skip DB) ======
print("2. Loading consumption data...")
cp = PROCESSED / "sanidad_real" / "latest_normalized.json"
consumption_data = json.loads(cp.read_text(encoding="utf-8"))

# Sample down to keep size manageable: take max 50K records
if len(consumption_data) > 50000:
    # Keep all hospital + sample ATC records
    hospital = [r for r in consumption_data if r.get("sector") == "Hospitalario"]
    atc_spain = [r for r in consumption_data if r.get("sector") == "Recetas SNS ATC" and r.get("geography") == "Spain"]
    atc_ccaa = [r for r in consumption_data if r.get("sector") == "Recetas SNS ATC" and r.get("geography") != "Spain"]
    
    # Keep all ATC records for complete trend data
    consumption_data = hospital + atc_spain + atc_ccaa
    print(f"   Kept: {len(hospital)} hosp + {len(atc_spain)} spain + {len(atc_ccaa)} ccaa = {len(consumption_data)}")

# Ingest to SQLite (just for source tracking)
with SessionLocal() as db:
    c = persist_normalized_records(db, consumption_data)
print(f"   Ingested: {c}")

# ====== 3. Export JSON ======
print("3. Exporting...")
from app.repositories.export import export_public_json
with SessionLocal() as db:
    written = export_public_json(db, PUBLIC)
    for path in sorted(written, key=lambda p: p.stat().st_size, reverse=True):
        sz = path.stat().st_size
        print(f"   {path.name}: {sz:,}B")

# Copy
FRONTEND.mkdir(parents=True, exist_ok=True)
for f in PUBLIC.iterdir():
    if f.suffix == ".json":
        (FRONTEND / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

# Stats
with SessionLocal() as db:
    from app.models.domain import ConsumptionRecord, Source, StudyDocument
    for m, l in [(Source,"Sources"), (SafetyAlert,"Alertas"), (ConsumptionRecord,"Consumo"), (StudyDocument,"Estudios"), (Drug,"Farmacos"), (ATCCode,"ATC")]:
        print(f"   {l}: {db.scalar(select(func.count()).select_from(m))}")
    yr = db.execute(select(func.min(ConsumptionRecord.year), func.max(ConsumptionRecord.year))).first()
    print(f"   Periodo: {yr[0]} - {yr[1]}")
    geos = db.execute(select(ConsumptionRecord.geography, func.count()).group_by(ConsumptionRecord.geography)).all()
    print(f"   Territorios: {len(geos)}")
    secs = db.execute(select(ConsumptionRecord.sector, func.count()).group_by(ConsumptionRecord.sector)).all()
    print(f"   Sectores: {dict(secs)}")

print("=== DONE ===")
