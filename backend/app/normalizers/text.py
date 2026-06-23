from datetime import date, datetime
import re
import unicodedata

from dateutil import parser


WHITESPACE_RE = re.compile(r"\s+")
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ATC_CODE_RE = re.compile(r"^[A-Z][0-9]{2}(?:[A-Z]{1,2})?(?:[0-9]{1,2})?$")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-](?:19|20)\d{2}|\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+(?:19|20)\d{2}|(?:19|20)\d{2}-\d{1,2}-\d{1,2})\b",
    re.IGNORECASE,
)

GEOGRAPHY_ALIASES = {
    "espana": "Spain",
    "spain": "Spain",
    "nacional": "Spain",
    "asturias": "Asturias",
    "principado de asturias": "Asturias",
    "andalucia": "Andalucia",
    "aragon": "Aragon",
    "canarias": "Canarias",
    "cantabria": "Cantabria",
    "castilla y leon": "Castilla y Leon",
    "castilla la mancha": "Castilla-La Mancha",
    "cataluna": "Cataluna",
    "comunitat valenciana": "Comunitat Valenciana",
    "valencia": "Comunitat Valenciana",
    "extremadura": "Extremadura",
    "galicia": "Galicia",
    "illes balears": "Illes Balears",
    "islas baleares": "Illes Balears",
    "la rioja": "La Rioja",
    "madrid": "Comunidad de Madrid",
    "murcia": "Region de Murcia",
    "navarra": "Navarra",
    "pais vasco": "Pais Vasco",
    "euskadi": "Pais Vasco",
    "ceuta": "Ceuta",
    "melilla": "Melilla",
}

DOCUMENT_KEYWORDS = {
    "proa": "PROA report",
    "farmacovigilancia": "pharmacovigilance document",
    "uso racional": "rational medicine use document",
    "guia farmacoterapeutica": "pharmacotherapeutic guide",
    "farmacia": "pharmacy document",
    "informe": "report",
    "memoria": "annual report",
}

THERAPEUTIC_KEYWORDS = {
    "antibiotico": "antibiotics",
    "antibioticos": "antibiotics",
    "antimicrobiano": "antimicrobials",
    "proa": "antimicrobials",
    "benzodiacepina": "benzodiazepines",
    "benzodiacepinas": "benzodiazepines",
    "psicofarmaco": "psychopharmaceuticals",
    "psicofarmacos": "psychopharmaceuticals",
    "antidepresivo": "antidepressants",
    "opioide": "opioids",
    "omeprazol": "proton pump inhibitors",
    "inhibidores de la bomba de protones": "proton pump inhibitors",
}


def normalize_name(value: str | None) -> str:
    """Normalize names for search and deduplication."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_drug_name(value: str | None) -> str:
    return normalize_name(value)


def normalize_atc_code(value: str | None) -> str | None:
    if not value:
        return None
    code = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if not code:
        return None
    return code if ATC_CODE_RE.match(code) else None


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def parse_date(value: str | None) -> date | None:
    """Parse dates from Spanish or ISO-like public pages."""
    if not value:
        return None
    text = clean_text(value)
    replacements = {
        "enero": "january",
        "febrero": "february",
        "marzo": "march",
        "abril": "april",
        "mayo": "may",
        "junio": "june",
        "julio": "july",
        "agosto": "august",
        "septiembre": "september",
        "setiembre": "september",
        "octubre": "october",
        "noviembre": "november",
        "diciembre": "december",
    }
    lowered = text.casefold()
    for spanish, english in replacements.items():
        lowered = lowered.replace(spanish, english)
    try:
        return parser.parse(lowered, dayfirst=True, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def extract_year(value: str | None) -> int | None:
    if not value:
        return None
    match = YEAR_RE.search(value)
    return int(match.group(0)) if match else None


def extract_dates(value: str | None) -> list[date]:
    if not value:
        return []
    dates: list[date] = []
    for match in DATE_RE.finditer(value):
        parsed = parse_date(match.group(0))
        if parsed and parsed not in dates:
            dates.append(parsed)
    return dates


def infer_geography(value: str | None, default: str | None = None) -> str | None:
    normalized = normalize_name(value)
    for alias, geography in GEOGRAPHY_ALIASES.items():
        if alias in normalized:
            return geography
    return default


def infer_document_type(value: str | None, default: str = "public_document") -> str:
    normalized = normalize_name(value)
    for keyword, document_type in DOCUMENT_KEYWORDS.items():
        if normalize_name(keyword) in normalized:
            return document_type
    return default


def infer_therapeutic_group(value: str | None) -> str | None:
    normalized = normalize_name(value)
    for keyword, group in THERAPEUTIC_KEYWORDS.items():
        if normalize_name(keyword) in normalized:
            return group
    return None


def utc_now() -> datetime:
    return datetime.utcnow()
