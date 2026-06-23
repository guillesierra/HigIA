from decimal import Decimal

import pandas as pd

from app.normalizers.consumption import normalize_consumption_dataframe
from app.normalizers.safety_alerts import detect_atc_codes, detect_possible_drug_names, normalize_alert_record
from app.normalizers.text import (
    extract_dates,
    extract_year,
    infer_document_type,
    infer_geography,
    infer_therapeutic_group,
    normalize_atc_code,
    normalize_drug_name,
    normalize_name,
    parse_date,
)


def test_normalize_name_and_date() -> None:
    assert normalize_name("Acido acetilsalicilico 500 mg") == "acido acetilsalicilico 500 mg"
    assert parse_date("15 de junio de 2021").isoformat() == "2021-06-15"
    assert normalize_drug_name("Ácido Acetilsalicílico") == "acido acetilsalicilico"
    assert normalize_atc_code(" j01-ca ") == "J01CA"
    assert extract_year("Informe PROA Asturias 2024") == 2024
    assert extract_dates("Publicado el 15 de junio de 2021")[0].isoformat() == "2021-06-15"
    assert infer_geography("Principado de Asturias") == "Asturias"
    assert infer_document_type("Guia farmacoterapeutica hospitalaria") == "pharmacotherapeutic guide"
    assert infer_therapeutic_group("Programa PROA antibioticos") == "antibiotics"


def test_alert_normalization_and_detection() -> None:
    record = normalize_alert_record(
        {
            "title": " Nota de seguridad ",
            "date": "2021-06-15",
            "url": "https://example.test/alert",
            "raw_text": "Diazepam N05BA",
        }
    )
    assert record["title"] == "Nota de seguridad"
    assert record["date"].isoformat() == "2021-06-15"
    assert detect_atc_codes("Related to J01CA and N05BA") == ["J01CA", "N05BA"]
    assert detect_possible_drug_names("Diazepam risk note", ["Diazepam", "Amoxicillin"]) == ["Diazepam"]


def test_consumption_dataframe_normalization() -> None:
    df = pd.DataFrame(
        [
            {
                "Ano": 2024,
                "CCAA": "Asturias",
                "Codigo ATC": "J01CA",
                "Medicamento": "Amoxicillin",
                "DHD": "11.9",
                "Envases": "40100",
            }
        ]
    )
    rows = normalize_consumption_dataframe(df, source_id=7)
    assert rows[0]["year"] == 2024
    assert rows[0]["geography"] == "Asturias"
    assert rows[0]["atc_code"] == "J01CA"
    assert rows[0]["dhd"] == Decimal("11.9")
    assert rows[0]["packages"] == Decimal("40100")


def test_consumption_normalization_tolerates_missing_columns() -> None:
    df = pd.DataFrame([{"Ano": 2024, "CCAA": "Asturias", "DHD": "11,9"}])
    rows = normalize_consumption_dataframe(df, source_name="mock", source_url="https://example.test")
    assert rows[0]["year"] == 2024
    assert rows[0]["geography"] == "Asturias"
    assert rows[0]["dhd"] == Decimal("11.9")
    assert rows[0]["atc_code"] is None
