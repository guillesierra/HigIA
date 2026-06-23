import re
from typing import Iterable

from app.normalizers.text import clean_text, normalize_name, parse_date


ATC_RE = re.compile(r"\b[A-Z][0-9]{2}[A-Z]{0,2}[0-9]{0,2}\b", re.IGNORECASE)

KNOWN_ATC_CODES: dict[str, str] = {
    "J01CA04": "amoxicillin",
    "J01CR02": "amoxicillin and beta-lactamase inhibitor",
    "J01FA10": "azithromycin",
    "J01MA02": "ciprofloxacin",
    "J01CA01": "ampicillin",
    "J01DD04": "ceftriaxone",
    "J01DD01": "cefotaxime",
    "J01FA09": "clarithromycin",
    "J01GB06": "amikacin",
    "J01MA12": "levofloxacin",
    "J01CF05": "flucloxacillin",
    "J01CE02": "phenoxymethylpenicillin",
    "J01CR05": "piperacillin and beta-lactamase inhibitor",
    "J01DH02": "meropenem",
    "J01DH51": "imipenem and cilastatin",
    "J01XC01": "fusidic acid",
    "J01XE01": "nitrofurantoin",
    "J01XX01": "fosfomycin",
    "J01EA01": "trimethoprim",
    "J01EE01": "sulfamethoxazole and trimethoprim",
    "J01MA14": "moxifloxacin",
    "J01FF01": "clindamycin",
    "J01FG01": "pristinamycin",
    "J01MB04": "nalidixic acid",
    "J01XA01": "vancomycin",
    "J01XD01": "metronidazole",
    "J01AA02": "doxycycline",
    "N02BE01": "paracetamol",
    "M01AE01": "ibuprofen",
    "C10AA05": "atorvastatin",
    "A02BC01": "omeprazole",
    "A02BC02": "pantoprazole",
    "A02BC04": "rabeprazole",
    "A02BC05": "esomeprazole",
    "N02BA01": "acetylsalicylic acid",
    "N05BA01": "diazepam",
    "N05BA06": "lorazepam",
    "N05BA12": "alprazolam",
    "N06AB04": "citalopram",
    "N06AB06": "sertraline",
    "N06AB05": "paroxetine",
    "N06AB10": "escitalopram",
    "N06AB03": "fluoxetine",
    "N06DA02": "donepezil",
    "A10BA02": "metformin",
    "C09AA05": "ramipril",
    "C09CA01": "losartan",
    "C09CA06": "candesartan",
    "R03AC02": "salbutamol",
    "R03AK06": "salmeterol and fluticasone",
    "C08CA01": "amlodipine",
    "C07AB03": "atenolol",
    "C07AB02": "metoprolol",
}

KNOWN_ACTIVE_INGREDIENTS: list[str] = sorted(set(KNOWN_ATC_CODES.values()))

KNOWN_DRUG_NAMES: list[str] = [
    "Augmentine", "Clamoxyl", "Zithromax", "Baycip", "Cipro",
    "Cleocin", "Flagyl", "Dalacin", "Rocephin", "Vibracina",
    "Dalsy", "Espidifen", "Termalgin", "Gelocatil", "Efferalgan",
    "Nolotil", "Enantyum", "Trankimazin", "Valium", "Orfidal",
    "Prozac", "Celexa", "Seroxat", "Prisdal", "Zoloft",
    "Omeprazol", "Pantoprazol", "Esomeprazol", "Losec", "Nexium",
    "Lipitor", "Zarator", "Cardyl", "Norvas", "Amlodipino",
    "Sintrom", "Adiro", "Tromalyt", "Plavix", "Iscover",
    "Ventolin", "Pulmicort", "Seretide", "Symbicort",
    "Metformina", "Dianben", "Glucophage",
    "Eutirox", "Levothroid", "Dexnon",
    "Ibuprofeno", "Paracetamol", "Tramadol", "Morfina", "Fentanilo",
    "Lorazepam", "Diazepam", "Alprazolam", "Bromazepam", "Clonazepam",
    "Prednisona", "Metilprednisolona", "Dexametasona", "Hidrocortisona",
    "Insulina", "Glargina", "Aspart", "Lispro", "Degludec",
]


def normalize_alert_record(record: dict[str, object]) -> dict[str, object]:
    """Normalize a scraped alert dictionary into the API field names."""
    title = clean_text(str(record.get("title") or ""))
    raw_date = str(record.get("date") or "")
    return {
        "title": title,
        "date": parse_date(raw_date),
        "url": str(record.get("url") or ""),
        "organization": str(record.get("organization") or "AEMPS"),
        "alert_type": str(record.get("alert_type") or "Safety"),
        "summary": clean_text(str(record.get("summary") or "")) or None,
        "raw_text": clean_text(str(record.get("raw_text") or "")) or None,
    }


def detect_atc_codes(text: str) -> list[str]:
    return sorted(set(ATC_RE.findall(text or "")))


def detect_atc_codes_with_names(text: str) -> list[dict[str, str]]:
    codes = detect_atc_codes(text)
    results = []
    for code in codes:
        results.append({
            "code": code,
            "name": KNOWN_ATC_CODES.get(code, "unknown"),
        })
    results.sort(key=lambda x: x["code"])
    return results


def detect_possible_drug_names(text: str, known_names: Iterable[str] | None = None) -> list[str]:
    names = known_names or KNOWN_DRUG_NAMES
    normalized_text = normalize_name(text)
    found = []
    for name in names:
        normalized = normalize_name(name)
        if normalized and len(normalized) > 3 and normalized in normalized_text:
            found.append(name)
    return sorted(set(found))


def detect_known_ingredients(text: str) -> list[str]:
    normalized_text = normalize_name(text)
    found = []
    for ingredient in KNOWN_ACTIVE_INGREDIENTS:
        if ingredient in normalized_text or normalize_name(ingredient) in normalized_text:
            found.append(ingredient)
    return sorted(set(found))


def detect_alert_therapeutic_category(alert_text: str) -> list[str]:
    categories: list[str] = []
    text_lower = (alert_text or "").casefold()
    category_keywords = {
        "antibiotics": ["antibiotic", "antibacterial", "penicillin", "cephalosporin", "macrolide", "quinolone", "fluoroquinolone", "amoxicillin", "azithromycin", "ciprofloxacin"],
        "nsaids": ["nsaid", "antiinflamatorio", "ibuprofen", "naproxen", "diclofenac", "aspirin"],
        "opioids": ["opioid", "opioide", "morphine", "fentanyl", "tramadol"],
        "benzodiazepines": ["benzodiazepine", "benzodiacepina", "diazepam", "lorazepam", "alprazolam"],
        "antidepressants": ["antidepressant", "antidepresivo", "ssri", "fluoxetine", "sertraline", "citalopram", "escitalopram"],
        "statins": ["statin", "atorvastatin", "simvastatin", "rosuvastatin", "cholesterol"],
        "ppis": ["proton pump", "omeprazole", "pantoprazole", "esomeprazole", "lansoprazole", "inhibidores de la bomba"],
        "anticoagulants": ["anticoagulant", "anticoagulante", "warfarin", "acenocoumarol", "dabigatran", "rivaroxaban", "apixaban", "heparin"],
        "antidiabetics": ["antidiabetic", "metformin", "insulin", "glibenclamide", "glimepiride"],
        "antihypertensives": ["antihypertensive", "ace inhibitor", "arb", "losartan", "enalapril", "ramipril", "amlodipine", "beta blocker"],
        "antipsychotics": ["antipsychotic", "antipsicotico", "risperidone", "olanzapine", "quetiapine", "clozapine"],
        "antineoplastics": ["antineoplastic", "antineoplasico", "cancer", "chemotherapy", "oncology"],
    }
    for category, keywords in category_keywords.items():
        if any(kw in text_lower for kw in keywords):
            categories.append(category)
    return sorted(categories)

