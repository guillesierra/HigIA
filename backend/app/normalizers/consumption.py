from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from app.normalizers.text import extract_year, infer_geography, normalize_atc_code, normalize_name


COLUMN_ALIASES = {
    "year": {"year", "ano", "anio", "ejercicio"},
    "month": {"month", "mes"},
    "geography": {"geography", "ambito", "territorio", "ccaa", "comunidad autonoma"},
    "geography_type": {"geography_type", "tipo geografia", "tipo_ambito"},
    "population_group": {"population_group", "grupo poblacion", "grupo_poblacion"},
    "sector": {"sector", "ambito asistencial", "ambito_asistencial", "tipo consumo"},
    "category": {"category", "categoria", "clasificacion", "grupo", "aware"},
    "atc_code": {"atc", "codigo atc", "codigo_atc", "atc_code"},
    "drug_name": {"medicamento", "drug", "drug_name", "nombre medicamento"},
    "active_ingredient": {"principio activo", "active ingredient", "active_ingredient"},
    "packages": {"envases", "packages", "numero envases", "num_envases"},
    "ddd": {"ddd", "dosis diaria definida"},
    "dhd": {"dhd", "dosis habitante dia"},
    "amount_pvpiva": {"pvpiva", "importe pvpiva", "amount_pvpiva", "importe"},
    "unit": {"unit", "unidad"},
    "notes": {"notes", "notas", "observaciones"},
}


def normalize_consumption_dataframe(
    df: pd.DataFrame,
    source_id: int | None = None,
    *,
    source_name: str | None = None,
    source_url: str | None = None,
    accessed_at: str | None = None,
    raw_file_path: str | None = None,
    parser_version: str | None = None,
    default_geography: str = "Spain",
    context_text: str | None = None,
) -> list[dict[str, Any]]:
    """Map a public tabular dataset to ConsumptionRecord-compatible dictionaries."""
    renamed = df.rename(columns=_build_column_map(df.columns))
    records: list[dict[str, Any]] = []
    for _, row in renamed.iterrows():
        row_text = " ".join(str(value) for value in row.to_dict().values() if not pd.isna(value))
        year = _to_int(row.get("year")) or extract_year(row_text) or extract_year(context_text)
        if year is None:
            continue
        geography = _none_if_empty(row.get("geography")) or infer_geography(row_text) or infer_geography(context_text) or default_geography
        atc_code = normalize_atc_code(_none_if_empty(row.get("atc_code"))) or _none_if_empty(row.get("category"))
        records.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "source_url": source_url,
                "accessed_at": accessed_at,
                "raw_file_path": raw_file_path,
                "parser_version": parser_version,
                "year": year,
                "month": _to_int(row.get("month")),
                "geography": geography,
                "geography_type": str(row.get("geography_type") or _geography_type(geography)),
                "population_group": _none_if_empty(row.get("population_group")),
                "sector": _none_if_empty(row.get("sector")),
                "category": _none_if_empty(row.get("category")),
                "atc_code": atc_code,
                "drug_name": _none_if_empty(row.get("drug_name")),
                "active_ingredient": _none_if_empty(row.get("active_ingredient")),
                "packages": _to_decimal(row.get("packages")),
                "ddd": _to_decimal(row.get("ddd")),
                "dhd": _to_decimal(row.get("dhd")),
                "amount_pvpiva": _to_decimal(row.get("amount_pvpiva")),
                "unit": _none_if_empty(row.get("unit")),
                "notes": _none_if_empty(row.get("notes")),
            }
        )
    return records


def _build_column_map(columns: pd.Index) -> dict[str, str]:
    mapping = {}
    normalized_aliases = {
        target: {normalize_name(alias) for alias in aliases}
        for target, aliases in COLUMN_ALIASES.items()
    }
    for column in columns:
        normalized = normalize_name(str(column))
        for target, aliases in normalized_aliases.items():
            if normalized in aliases:
                mapping[column] = target
                break
    return mapping


def _to_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except ValueError:
        return None


def _to_decimal(value: object) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _none_if_empty(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _geography_type(geography: str) -> str:
    return "country" if normalize_name(geography) in {"spain", "espana"} else "autonomous_community"
