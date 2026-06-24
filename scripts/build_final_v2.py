"""Rebuild full database from all sources and export to frontend."""
import sys, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import reset_db
from app.db.session import SessionLocal
from app.repositories.ingestion import persist_normalized_records, get_or_create_atc, get_or_create_drug, link_drug_to_atc
from app.normalizers.text import normalize_name
from app.scrapers.who_atc import get_embedded_atc_codes, EMBEDDED_ATC_NAMES
from app.normalizers.safety_alerts import KNOWN_ATC_CODES, KNOWN_ACTIVE_INGREDIENTS, KNOWN_DRUG_NAMES
from app.models.domain import ATCCode, Drug, DrugATC, SafetyAlert
from sqlalchemy import select

PROCESSED = ROOT / "data" / "processed"
PUBLIC = PROCESSED / "public"
FRONTEND = ROOT / "frontend" / "public" / "data"
reset_db()

print("=== HigIA DB Builder ===")

# 1. Real ATC + hospital data
print("\n1. Real consumption data...")
hp = PROCESSED / "sanidad_real" / "latest_normalized.json"
if hp.exists():
    real = json.loads(hp.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        c = persist_normalized_records(db, real)
    print(f"   {len(real)} records -> {c}")

# 2. ATC codes + drugs
print("\n2. ATC codes + drugs...")
with SessionLocal() as db:
    for code, name in KNOWN_ATC_CODES.items():
        get_or_create_atc(db, code, name)
    for a in get_embedded_atc_codes():
        get_or_create_atc(db, a["code"], a["name"])
    for ing in KNOWN_ACTIVE_INGREDIENTS:
        get_or_create_drug(db, ing, ing)
    for dn in KNOWN_DRUG_NAMES:
        get_or_create_drug(db, dn, None)
    
    import pandas as pd
    xlsx_dir = ROOT / "data" / "raw" / "atc_xlsx"
    xlsx_files = list(xlsx_dir.glob("*.xlsx"))
    if not xlsx_files:
        # Fall back to old path
        import glob as g
        xlsx_files = [Path(p) for p in g.glob(str(ROOT / "data" / "raw" / "**" / "*.xlsx"), recursive=True)][:10]
    
    for link_c, (code, name) in enumerate(KNOWN_ATC_CODES.items()):
        atc_obj = db.scalar(select(ATCCode).where(ATCCode.code == code))
        if not atc_obj: continue
        for ing in KNOWN_ACTIVE_INGREDIENTS:
            if normalize_name(ing) in normalize_name(name):
                drug = db.scalar(select(Drug).where(Drug.active_ingredient == ing))
                if not drug:
                    drug = db.scalar(select(Drug).where(Drug.normalized_name == normalize_name(ing)))
                if drug:
                    ex = db.scalar(select(DrugATC).where(DrugATC.drug_id == drug.id, DrugATC.atc_code_id == atc_obj.id))
                    if not ex:
                        link_drug_to_atc(db, drug, code)
                break
    db.commit()
    print(f"   Loaded ATC codes, drugs and links")

# 3. Alerts + studies
print("\n3. Alerts and studies...")
for src in ["aemps", "universities", "asturias", "sanidad", "pran"]:
    fp = PROCESSED / src / "latest_normalized.json"
    if fp.exists():
        recs = json.loads(fp.read_text(encoding="utf-8"))
        with SessionLocal() as db:
            cnt = persist_normalized_records(db, recs)
        print(f"   {src}: {len(recs)} -> {cnt}")

# 4. Link alerts
print("\n4. Linking alerts...")
with SessionLocal() as db:
    from app.normalizers.safety_alerts import detect_atc_codes, detect_known_ingredients
    from app.repositories.ingestion import link_alert_to_drug, link_alert_to_atc
    alerts = db.scalars(select(SafetyAlert)).all()
    ld = la = 0
    for alert in alerts:
        text = f"{alert.title} {alert.summary or ''} {alert.raw_text or ''}"
        for code in detect_atc_codes(text)[:5]:
            atc = db.scalar(select(ATCCode).where(ATCCode.code == code))
            if atc:
                try: link_alert_to_atc(db, alert.id, code); la += 1
                except: pass
        for ing in detect_known_ingredients(text)[:5]:
            drug = db.scalar(select(Drug).where(Drug.active_ingredient == ing))
            if not drug:
                drug = db.scalar(select(Drug).where(Drug.normalized_name == normalize_name(ing)))
            if drug:
                try: link_alert_to_drug(db, alert.id, drug); ld += 1
                except: pass
    db.commit()
    print(f"   {len(alerts)} alerts, {la} ATC links, {ld} drug links")

# 5. Export
print("\n5. Exporting to static JSON...")
from app.repositories.export import export_public_json
with SessionLocal() as db:
    written = export_public_json(db, PUBLIC)
    for path in sorted(written, key=lambda p: p.stat().st_size, reverse=True):
        sz = path.stat().st_size
        try: items = len(json.loads(path.read_text(encoding="utf-8")))
        except: items = "?"
        print(f"   {path.name}: {sz:,}B ({items})")

FRONTEND.mkdir(parents=True, exist_ok=True)
for f in PUBLIC.iterdir():
    if f.suffix == ".json":
        (FRONTEND / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
print("   Copied to frontend/")

# Final stats
from sqlalchemy import func
from app.models.domain import ConsumptionRecord, Source, StudyDocument

print("\n=== Final Stats ===")
with SessionLocal() as db:
    for m, lbl in [(Source,"Sources"), (SafetyAlert,"Alertas"), (ConsumptionRecord,"Consumo"), (StudyDocument,"Estudios"), (Drug,"Farmacos"), (ATCCode,"ATC")]:
        c = db.scalar(select(func.count()).select_from(m))
        print(f"   {lbl}: {c}")
    yr = db.execute(select(func.min(ConsumptionRecord.year), func.max(ConsumptionRecord.year))).first()
    print(f"   Periodo: {yr[0]} - {yr[1]}")
    geo = db.scalar(select(func.count(func.distinct(ConsumptionRecord.geography))))
    print(f"   Territorios: {geo}")
    sectors = {}
    for row in db.execute(select(ConsumptionRecord.sector, func.count()).group_by(ConsumptionRecord.sector)).all():
        sectors[row[0]] = row[1]
    print(f"   Sectores: {sectors}")

print("=== DONE ===")
