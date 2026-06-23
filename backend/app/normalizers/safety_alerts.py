import re
from typing import Iterable

from app.normalizers.text import clean_text, normalize_name, parse_date


ATC_RE = re.compile(r"\b[A-Z][0-9]{2}[A-Z]{0,2}[0-9]{0,2}\b")


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


def detect_possible_drug_names(text: str, known_names: Iterable[str]) -> list[str]:
    """Find known drug names in free text using normalized comparison."""
    normalized_text = normalize_name(text)
    found = []
    for name in known_names:
        normalized = normalize_name(name)
        if normalized and normalized in normalized_text:
            found.append(name)
    return sorted(set(found))

