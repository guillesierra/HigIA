"""Load embedded ATC codes and known drugs into the database."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.init_db import create_db
from app.db.session import SessionLocal
from app.repositories.ingestion import get_or_create_atc, get_or_create_drug, link_drug_to_atc
from app.scrapers.who_atc import get_embedded_atc_codes, EMBEDDED_ATC_NAMES
from app.normalizers.safety_alerts import KNOWN_ACTIVE_INGREDIENTS, KNOWN_DRUG_NAMES

create_db()

with SessionLocal() as db:
    count_atc = 0
    count_drug = 0
    count_link = 0

    embedded = get_embedded_atc_codes()
    for atc_data in embedded:
        code = atc_data["code"]
        name = atc_data["name"]
        if get_or_create_atc(db, code, name):
            count_atc += 1

    for ingredient in KNOWN_ACTIVE_INGREDIENTS:
        drug = get_or_create_drug(db, ingredient, ingredient)
        count_drug += 1

    for dname in KNOWN_DRUG_NAMES:
        get_or_create_drug(db, dname, None)
        count_drug += 1

    for code, name in EMBEDDED_ATC_NAMES.items():
        atc = get_or_create_atc(db, code, name)
        if atc:
            ingredient = KNOWN_ACTIVE_INGREDIENTS[0] if KNOWN_ACTIVE_INGREDIENTS else ""
            for ing in KNOWN_ACTIVE_INGREDIENTS:
                if ing and ing.lower() in name.lower():
                    drug = get_or_create_drug(db, ing, ing)
                    link_drug_to_atc(db, drug, code)
                    count_link += 1
                    break

    db.commit()

print(f"Loaded: {count_atc} ATC codes, {count_drug} drugs, {count_link} drug-ATC links")
