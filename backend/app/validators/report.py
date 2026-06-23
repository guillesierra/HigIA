from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

from app.normalizers.text import normalize_name


METADATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "metadata"


class ValidationReportGenerator:
    """Generates validation reports after scraping and normalization runs."""

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        self.run_at = datetime.utcnow().isoformat()
        self.warnings: list[dict[str, str]] = []
        self.errors: list[dict[str, str]] = []
        self.summary: dict[str, Any] = {}
        self.completeness: dict[str, dict[str, float]] = {}
        self.duplicates: list[dict[str, Any]] = []

    def validate_consumption_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        results = {
            "total_records": len(records),
            "valid_records": 0,
            "missing_year": 0,
            "missing_geography": 0,
            "missing_atc_code": 0,
            "missing_dhd": 0,
            "out_of_range_dhd": 0,
            "duplicate_keys": 0,
            "year_range": (None, None),
            "geographies": [],
            "atc_codes_found": [],
            "dhd_stats": {},
            "packages_stats": {},
            "field_completeness": {},
        }
        seen_keys: set[str] = set()
        years: list[int] = []
        geographies: list[str] = []
        atc_codes: list[str] = []
        dhd_values: list[float] = []
        package_values: list[float] = []
        field_counters: dict[str, int] = Counter()

        for record in records:
            if record.get("record_type") != "consumption":
                continue
            for key in ["year", "geography", "atc_code", "dhd", "packages", "ddd", "drug_name", "active_ingredient"]:
                if record.get(key) is not None and record.get(key) != "":
                    field_counters[key] += 1

            key_parts = f"{record.get('year')}|{record.get('geography')}|{record.get('atc_code')}|{record.get('drug_name')}|{record.get('sector')}"
            if key_parts in seen_keys:
                results["duplicate_keys"] += 1
            seen_keys.add(key_parts)

            year = record.get("year")
            if year is None:
                results["missing_year"] += 1
            else:
                years.append(int(year))

            geo = record.get("geography")
            if not geo:
                results["missing_geography"] += 1
            else:
                geographies.append(str(geo))

            atc = record.get("atc_code")
            if not atc:
                results["missing_atc_code"] += 1
            else:
                atc_codes.append(str(atc))

            dhd = record.get("dhd")
            if dhd is None:
                results["missing_dhd"] += 1
            elif isinstance(dhd, (int, float, Decimal)):
                val = float(dhd)
                dhd_values.append(val)
                if val < 0 or val > 500:
                    results["out_of_range_dhd"] += 1

            pkgs = record.get("packages")
            if pkgs is not None and isinstance(pkgs, (int, float, Decimal)):
                package_values.append(float(pkgs))

            results["valid_records"] += 1

        if years:
            results["year_range"] = (min(years), max(years))
        results["geographies"] = sorted(set(geographies))
        results["atc_codes_found"] = sorted(set(atc_codes))

        if dhd_values:
            results["dhd_stats"] = {
                "mean": round(mean(dhd_values), 4),
                "median": round(median(dhd_values), 4),
                "min": round(min(dhd_values), 4),
                "max": round(max(dhd_values), 4),
                "stdev": round(stdev(dhd_values), 4) if len(dhd_values) > 1 else 0,
                "count": len(dhd_values),
            }
        if package_values:
            results["packages_stats"] = {
                "mean": round(mean(package_values), 2),
                "median": round(median(package_values), 2),
                "min": round(min(package_values), 2),
                "max": round(max(package_values), 2),
                "count": len(package_values),
            }
        total = results["valid_records"] or 1
        results["field_completeness"] = {
            key: round(count / total * 100, 1)
            for key, count in field_counters.items()
        }
        return results

    def validate_alert_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        results = {
            "total_records": len(records),
            "valid_records": 0,
            "missing_title": 0,
            "missing_date": 0,
            "missing_url": 0,
            "missing_summary": 0,
            "duplicate_urls": 0,
            "active_ingredients_found": 0,
            "dates_range": (None, None),
            "organizations": [],
        }
        seen_urls: set[str] = set()
        dates: list[str] = []
        orgs: list[str] = []

        for record in records:
            if record.get("record_type") != "safety_alert":
                continue

            url = str(record.get("url") or "")
            if url and url in seen_urls:
                results["duplicate_urls"] += 1
            if url:
                seen_urls.add(url)

            if not record.get("title"):
                results["missing_title"] += 1
            if not record.get("date"):
                results["missing_date"] += 1
            else:
                dates.append(str(record["date"]))
            if not record.get("url"):
                results["missing_url"] += 1
            if not record.get("summary"):
                results["missing_summary"] += 1
            if record.get("possible_active_ingredients"):
                results["active_ingredients_found"] += len(record.get("possible_active_ingredients", []))

            org = record.get("organization")
            if org:
                orgs.append(str(org))

            results["valid_records"] += 1

        if dates:
            results["dates_range"] = (min(dates), max(dates))
        results["organizations"] = sorted(set(orgs))
        return results

    def validate_study_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        results = {
            "total_records": len(records),
            "valid_records": 0,
            "missing_title": 0,
            "missing_year": 0,
            "missing_url": 0,
            "duplicate_urls": 0,
            "year_range": (None, None),
            "document_types": [],
            "therapeutic_groups": [],
        }
        seen_urls: set[str] = set()
        years: list[int] = []
        doc_types: list[str] = []
        groups: list[str] = []

        for record in records:
            rt = record.get("record_type") or record.get("resource_type") or ""
            if rt not in {"study_document", "document", "study"}:
                continue

            url = str(record.get("url") or "")
            if url and url in seen_urls:
                results["duplicate_urls"] += 1
            if url:
                seen_urls.add(url)

            if not record.get("title"):
                results["missing_title"] += 1
            yr = record.get("year")
            if yr is None:
                results["missing_year"] += 1
            else:
                years.append(int(yr))
            if not record.get("url"):
                results["missing_url"] += 1

            dt = record.get("document_type")
            if dt:
                doc_types.append(str(dt))
            tg = record.get("therapeutic_group")
            if tg:
                groups.append(str(tg))

            results["valid_records"] += 1

        if years:
            results["year_range"] = (min(years), max(years))
        results["document_types"] = sorted(set(doc_types))
        results["therapeutic_groups"] = sorted(set(groups))
        return results

    def detect_duplicates(self, records: list[dict[str, Any]], record_type: str, threshold: float = 0.85) -> list[dict[str, Any]]:
        """Detect near-duplicates using normalized title hashing."""
        if not records:
            return []
        normalized_pairs: list[tuple[int, str, str]] = []
        for idx, record in enumerate(records):
            rt = record.get("record_type", "")
            if rt != record_type:
                continue
            title = normalize_name(str(record.get("title") or ""))
            if not title or len(title) < 10:
                continue
            hash_val = hashlib.md5(title.encode()).hexdigest()
            normalized_pairs.append((idx, hash_val, title))

        seen_hashes: dict[str, int] = {}
        duplicate_groups: list[dict[str, Any]] = []
        for idx, hash_val, title in normalized_pairs:
            for seen_hash, seen_idx in seen_hashes.items():
                if hash_val[:8] == seen_hash[:8] or _title_similarity(title, normalized_pairs[seen_idx][2]) >= threshold:
                    duplicate_groups.append({
                        "record_type": record_type,
                        "index_a": seen_idx,
                        "index_b": idx,
                        "title_a": records[seen_idx].get("title", "")[:200],
                        "title_b": records[idx].get("title", "")[:200],
                    })
                    break
            seen_hashes[hash_val] = idx
        return duplicate_groups

    def generate_report(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        consumption_records = [r for r in records if r.get("record_type") == "consumption"]
        alert_records = [r for r in records if r.get("record_type") == "safety_alert"]
        study_records = [r for r in records if r.get("record_type") in {"study_document", "document", "study", "source_page", "dataset_link", "html_tables"}]

        self.summary = {
            "source_name": self.source_name,
            "run_at": self.run_at,
            "total_records": len(records),
            "consumption_records": len(consumption_records),
            "alert_records": len(alert_records),
            "study_records": len(study_records),
            "error_records": len([r for r in records if r.get("record_type") in {"error", "source_error"}]),
        }

        consumption_validation = self.validate_consumption_records(records) if consumption_records else None
        alert_validation = self.validate_alert_records(records) if alert_records else None
        study_validation = self.validate_study_records(records) if study_records else None

        alert_dupes = self.detect_duplicates(records, "safety_alert") if alert_records else []
        consumption_dupes = self.detect_duplicates(records, "consumption") if consumption_records else []

        report = {
            "summary": self.summary,
            "consumption_validation": consumption_validation,
            "alert_validation": alert_validation,
            "study_validation": study_validation,
            "duplicate_alerts": alert_dupes,
            "duplicate_consumption": consumption_dupes,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        self._save_report(report)
        return report

    def _save_report(self, report: dict[str, Any]) -> Path:
        report_dir = METADATA_ROOT / self.source_name
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        path = report_dir / f"validation_{timestamp}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        latest = report_dir / "latest_validation.json"
        latest.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path

    @staticmethod
    def load_latest_validation(source_name: str) -> dict[str, Any] | None:
        report_dir = METADATA_ROOT / source_name
        latest = report_dir / "latest_validation.json"
        if not latest.exists():
            return None
        return json.loads(latest.read_text(encoding="utf-8"))

    @staticmethod
    def load_all_validation_reports() -> list[dict[str, Any]]:
        reports = []
        if not METADATA_ROOT.exists():
            return reports
        for subdir in METADATA_ROOT.iterdir():
            if subdir.is_dir():
                latest = subdir / "latest_validation.json"
                if latest.exists():
                    try:
                        report = json.loads(latest.read_text(encoding="utf-8"))
                        report["source_name"] = subdir.name
                        reports.append(report)
                    except (json.JSONDecodeError, KeyError):
                        continue
        return reports


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)
