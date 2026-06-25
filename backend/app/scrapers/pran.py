from __future__ import annotations

from base64 import urlsafe_b64decode
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.normalizers.consumption import normalize_consumption_dataframe
from app.normalizers.text import clean_text, infer_geography, infer_therapeutic_group
from app.scrapers.base import BaseScraper, ScrapedResource
from app.scrapers.tabular import DATASET_EXTENSIONS, discover_links, html_tables_to_dataframes, read_tabular_file, relevant_dataset_links, rows_to_jsonable


PRAN_SEED_URLS = [
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumos-antibioticos-humana",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumos-antibioticos-extrahospitalarios-por-comunidades",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumos-antibioticos-en-atencion-primaria",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumos-antibioticos-en-hospitales",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumos-antibioticos-hospitalarios-por-comunidades",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumo-categorias-aware",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumo-categorias-aware-spain",
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/ecdc",
]
PRAN_KEYWORDS = {
    "consumo",
    "consumos",
    "antibioticos",
    "antibiotico",
    "antimicrobianos",
    "humana",
    "extrahospitalarios",
    "hospitalarios",
    "comunidades",
    "dhd",
    "datos",
}

PRAN_POWERBI_QUERYDATA_URL = "https://wabi-north-europe-api.analysis.windows.net/public/reports/querydata?synchronous=true"
PRAN_J01_COMMUNITY_PAGE = (
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/"
    "consumo-antibioticos-humana/consumos-antibioticos-en-atencion-primaria"
)
PRAN_J01_COMMUNITY_BY_CCAA_PAGE = (
    "https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/"
    "consumo-antibioticos-humana/consumos-antibioticos-extrahospitalarios-por-comunidades"
)
PRAN_J01_CCAA_RESOURCE_KEY = "8c75ace5-7b1e-4307-bbc3-164b04dbf95d"
PRAN_J01_CCAA_DATASET_ID = "9846e8fd-19de-4c7a-9d72-60ac7e5a3188"
PRAN_J01_CCAA_REPORT_ID = "499ac648-9c88-4131-902f-0abbdb722864"
PRAN_J01_CCAA_VISUAL_ID = "3def56001005e4ee6538"
PRAN_J01_CCAA_MODEL_ID = 4017226
PRAN_POWERBI_PAYLOAD_DIR = Path(__file__).resolve().parent / "payloads"


class PranAntibioticsScraper(BaseScraper):
    source_name = "PRAN human antibiotic consumption"
    base_url = "https://www.resistenciaantibioticos.es"
    start_url = PRAN_SEED_URLS[0]
    raw_subdir = "pran"
    parser_version = "pran-antibiotics-0.4"

    def parse(self, limit: int = 50, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        seen: set[str] = set()
        for seed_url in PRAN_SEED_URLS:
            page = self.fetch_url(seed_url, ".html")
            if page.error:
                resources.append(self.error_resource(seed_url, "seed_fetch_failed", page.error))
                continue

            resources.append(
                ScrapedResource(
                    source_name=self.source_name,
                    source_url=seed_url,
                    resource_type="html_tables",
                    title="PRAN HTML tables",
                    url=seed_url,
                    accessed_at=page.accessed_at,
                    raw_path=page.raw_file_path,
                    content_text=clean_text((page.text or "")[:2000]),
                    metadata={
                        "geography": infer_geography(seed_url),
                        "therapeutic_group": infer_therapeutic_group(seed_url) or "antibiotics",
                    },
                    parser_version=self.parser_version,
                )
            )

            for report_url in self._powerbi_iframe_urls(page.text or "", seed_url):
                resources.append(
                    ScrapedResource(
                        source_name=self.source_name,
                        source_url=seed_url,
                        resource_type="powerbi_report",
                        title="PRAN public Power BI report",
                        url=report_url,
                        accessed_at=page.accessed_at,
                        raw_path=page.raw_file_path,
                        content_text=None,
                        metadata={
                            "requires_parser": seed_url != PRAN_J01_COMMUNITY_PAGE,
                            "therapeutic_group": "antibiotics",
                        },
                        parser_version=self.parser_version,
                    )
                )
                if seed_url == PRAN_J01_COMMUNITY_PAGE:
                    query_resource = self._fetch_j01_community_powerbi_query(seed_url, report_url)
                    if query_resource:
                        resources.append(query_resource)
                elif seed_url == PRAN_J01_COMMUNITY_BY_CCAA_PAGE:
                    query_resource = self._fetch_j01_community_by_ccaa_powerbi_query(seed_url, report_url)
                    if query_resource:
                        resources.append(query_resource)

            links = relevant_dataset_links(discover_links(page.text or "", seed_url, self.absolutize), PRAN_KEYWORDS)
            for link in links:
                if link["url"] in seen:
                    continue
                seen.add(link["url"])
                if link["extension"] not in DATASET_EXTENSIONS:
                    resources.append(self._metadata_resource(seed_url, page, link))
                    continue
                dataset = self.fetch_url(link["url"], link["extension"])
                resources.append(
                    ScrapedResource(
                        source_name=self.source_name,
                        source_url=seed_url,
                        resource_type="dataset_file" if not dataset.error else "source_error",
                        title=link["title"],
                        url=link["url"],
                        accessed_at=dataset.accessed_at,
                        raw_path=dataset.raw_file_path,
                        metadata={
                            "extension": link["extension"],
                            "download_error": dataset.error,
                            "therapeutic_group": "antibiotics",
                            "origin_page_raw_file_path": page.raw_file_path,
                        },
                        parser_version=self.parser_version,
                    )
                )
                if len(resources) >= limit:
                    return resources[:limit]
        return resources[:limit]

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            if resource.resource_type == "dataset_file" and resource.raw_path:
                rows.extend(self._normalize_dataset(resource))
            elif resource.resource_type == "html_tables" and resource.raw_path:
                rows.extend(self._normalize_html_tables(resource))
            elif resource.resource_type == "powerbi_querydata" and resource.content_text:
                rows.extend(self._normalize_j01_community_powerbi(resource))
            elif resource.resource_type == "powerbi_ccaa_querydata" and resource.content_text:
                rows.extend(self._normalize_j01_community_by_ccaa_powerbi(resource))
            else:
                rows.append(self._metadata_record(resource))
        return rows

    def _normalize_dataset(self, resource: ScrapedResource) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            for sheet_name, frame in read_tabular_file(Path(resource.raw_path)):
                normalized = normalize_consumption_dataframe(
                    frame,
                    source_name=resource.source_name,
                    source_url=resource.url,
                    accessed_at=resource.accessed_at.isoformat(),
                    raw_file_path=resource.raw_path,
                    parser_version=resource.parser_version,
                    default_geography="Spain",
                    context_text=f"{resource.title} {sheet_name} antibiotics",
                )
                for record in rows_to_jsonable(normalized):
                    record.update({"record_type": "consumption", "sheet_name": sheet_name, "therapeutic_group": "antibiotics"})
                    rows.append(record)
        except Exception as exc:
            self.log_error("pran_dataset_normalization_failed", resource.url, exc)
            rows.append(self.error_payload(resource.url, "pran_dataset_normalization_failed", exc))
        return rows

    def _normalize_html_tables(self, resource: ScrapedResource) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            html = Path(resource.raw_path).read_text(encoding="utf-8", errors="ignore")
            for index, frame in enumerate(html_tables_to_dataframes(html), start=1):
                normalized = normalize_consumption_dataframe(
                    frame,
                    source_name=resource.source_name,
                    source_url=resource.url,
                    accessed_at=resource.accessed_at.isoformat(),
                    raw_file_path=resource.raw_path,
                    parser_version=resource.parser_version,
                    default_geography=infer_geography(resource.url) or "Spain",
                    context_text=f"{resource.title} table {index} antibiotics",
                )
                for record in rows_to_jsonable(normalized):
                    record.update({"record_type": "consumption", "table_index": index, "therapeutic_group": "antibiotics"})
                    rows.append(record)
        except Exception as exc:
            self.log_error("pran_html_table_normalization_failed", resource.url, exc)
            rows.append(self.error_payload(resource.url, "pran_html_table_normalization_failed", exc))
        if not rows:
            rows.append(self._metadata_record(resource))
        return rows

    def _metadata_resource(self, seed_url: str, page, link: dict[str, str]) -> ScrapedResource:
        return ScrapedResource(
            source_name=self.source_name,
            source_url=seed_url,
            resource_type="dataset_link",
            title=link["title"],
            url=link["url"],
            accessed_at=page.accessed_at,
            raw_path=page.raw_file_path,
            metadata={"extension": link["extension"], "requires_source_specific_parser": True},
            parser_version=self.parser_version,
        )

    def _metadata_record(self, resource: ScrapedResource) -> dict[str, Any]:
        return {
            "record_type": resource.resource_type,
            "title": resource.title,
            "url": resource.url,
            "metadata": resource.metadata or {},
            **resource.traceability(),
        }

    def _powerbi_iframe_urls(self, html: str, seed_url: str) -> list[str]:
        from bs4 import BeautifulSoup

        urls: list[str] = []
        soup = BeautifulSoup(html, "html.parser")
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src") or ""
            if "app.powerbi.com/view" in src:
                urls.append(self.absolutize(src, seed_url))
        return urls

    def _fetch_j01_community_powerbi_query(self, source_url: str, report_url: str) -> ScrapedResource | None:
        payload_path = PRAN_POWERBI_PAYLOAD_DIR / "pran_j01_community_query.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        resource_key = _powerbi_resource_key(report_url)
        if not self.can_fetch(PRAN_POWERBI_QUERYDATA_URL):
            return self.error_resource(
                PRAN_POWERBI_QUERYDATA_URL,
                "robots_disallow",
                f"robots.txt disallows fetch: {PRAN_POWERBI_QUERYDATA_URL}",
            )
        self._delay()
        try:
            response = self.session.post(
                PRAN_POWERBI_QUERYDATA_URL,
                data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                timeout=self.timeout,
                verify=self.verify_ssl,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": "https://app.powerbi.com",
                    "Referer": report_url,
                    **({"X-PowerBI-ResourceKey": resource_key} if resource_key else {}),
                },
            )
            raw_path = str(self.save_raw(PRAN_POWERBI_QUERYDATA_URL, response.content, ".json"))
            self.log_fetch(
                PRAN_POWERBI_QUERYDATA_URL,
                response.status_code,
                raw_path,
                response.headers.get("content-type"),
            )
            if response.status_code >= 400:
                return self.error_resource(
                    PRAN_POWERBI_QUERYDATA_URL,
                    "powerbi_query_failed",
                    f"HTTP {response.status_code}",
                )
            return ScrapedResource(
                source_name=self.source_name,
                source_url=source_url,
                resource_type="powerbi_querydata",
                title="PRAN J01 community antibiotic consumption DHD",
                url=PRAN_POWERBI_QUERYDATA_URL,
                accessed_at=datetime.utcnow(),
                raw_path=raw_path,
                content_text=response.text,
                metadata={
                    "report_url": report_url,
                    "atc_code": "J01",
                    "atc_label": "J01 - ANTIBACTERIANOS PARA USO SISTEMICO",
                    "sector": "Comunitario",
                    "unit": "DHD",
                    "query_payload_path": str(payload_path),
                },
                parser_version=self.parser_version,
            )
        except Exception as exc:
            self.log_error("powerbi_query_failed", PRAN_POWERBI_QUERYDATA_URL, exc)
            return self.error_resource(PRAN_POWERBI_QUERYDATA_URL, "powerbi_query_failed", exc)

    def _fetch_j01_community_by_ccaa_powerbi_query(self, source_url: str, report_url: str) -> ScrapedResource | None:
        payload = _j01_community_by_ccaa_powerbi_payload()
        if not self.can_fetch(PRAN_POWERBI_QUERYDATA_URL):
            return self.error_resource(
                PRAN_POWERBI_QUERYDATA_URL,
                "robots_disallow",
                f"robots.txt disallows fetch: {PRAN_POWERBI_QUERYDATA_URL}",
            )
        self._delay()
        try:
            response = self.session.post(
                PRAN_POWERBI_QUERYDATA_URL,
                data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                timeout=self.timeout,
                verify=self.verify_ssl,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": "https://app.powerbi.com",
                    "Referer": report_url,
                    "X-PowerBI-ResourceKey": PRAN_J01_CCAA_RESOURCE_KEY,
                },
            )
            raw_path = str(self.save_raw(PRAN_POWERBI_QUERYDATA_URL, response.content, ".json"))
            self.log_fetch(
                PRAN_POWERBI_QUERYDATA_URL,
                response.status_code,
                raw_path,
                response.headers.get("content-type"),
            )
            if response.status_code >= 400:
                return self.error_resource(
                    PRAN_POWERBI_QUERYDATA_URL,
                    "powerbi_ccaa_query_failed",
                    f"HTTP {response.status_code}",
                )
            return ScrapedResource(
                source_name=self.source_name,
                source_url=source_url,
                resource_type="powerbi_ccaa_querydata",
                title="PRAN J01 community antibiotic consumption DHD by autonomous community",
                url=PRAN_POWERBI_QUERYDATA_URL,
                accessed_at=datetime.utcnow(),
                raw_path=raw_path,
                content_text=response.text,
                metadata={
                    "report_url": report_url,
                    "resource_key": PRAN_J01_CCAA_RESOURCE_KEY,
                    "dataset_id": PRAN_J01_CCAA_DATASET_ID,
                    "atc_code": "J01",
                    "atc_label": "J01 - ANTIBACTERIANOS PARA USO SISTEMICO",
                    "sector": "Comunitario",
                    "unit": "DHD",
                    "years": [2014, 2021],
                },
                parser_version=self.parser_version,
            )
        except Exception as exc:
            self.log_error("powerbi_ccaa_query_failed", PRAN_POWERBI_QUERYDATA_URL, exc)
            return self.error_resource(PRAN_POWERBI_QUERYDATA_URL, "powerbi_ccaa_query_failed", exc)

    def _normalize_j01_community_powerbi(self, resource: ScrapedResource) -> list[dict[str, Any]]:
        try:
            payload = json.loads(resource.content_text or "{}")
            rows = (
                payload["results"][0]["result"]["data"]["dsr"]["DS"][0]["PH"][0]["DM0"]
            )
        except Exception as exc:
            self.log_error("powerbi_normalization_failed", resource.url, exc)
            return [self.error_payload(resource.url, "powerbi_normalization_failed", exc)]

        metrics = [
            ("Receta Oficial+Mutuas", 1),
            ("Receta Privada", 2),
            ("Global comunitario", 3),
            ("Mutuas", 4),
            ("Receta Oficial", 5),
        ]
        records: list[dict[str, Any]] = []
        for row in rows:
            values = row.get("C") or []
            if len(values) < 6:
                continue
            year = values[0]
            for category, index in metrics:
                records.append(
                    {
                        "record_type": "consumption",
                        "year": year,
                        "month": None,
                        "geography": "Spain",
                        "geography_type": "country",
                        "sector": "Comunitario",
                        "category": category,
                        "atc_code": "J01",
                        "drug_name": None,
                        "active_ingredient": None,
                        "packages": None,
                        "ddd": None,
                        "dhd": values[index],
                        "amount_pvpiva": None,
                        "unit": "DHD",
                        "notes": (
                            "PRAN public Power BI report: Consumo de Antibioticos de uso "
                            "sistemico (J01) en sector comunitario, DHD."
                        ),
                        "therapeutic_group": "antibiotics",
                        **resource.traceability(),
                    }
                )
        return records

    def _normalize_j01_community_by_ccaa_powerbi(self, resource: ScrapedResource) -> list[dict[str, Any]]:
        try:
            payload = json.loads(resource.content_text or "{}")
            dataset = payload["results"][0]["result"]["data"]["dsr"]["DS"][0]
            rows = dataset["PH"][0]["DM0"]
        except Exception as exc:
            self.log_error("powerbi_ccaa_normalization_failed", resource.url, exc)
            return [self.error_payload(resource.url, "powerbi_ccaa_normalization_failed", exc)]

        metrics = [
            ("Global comunitario", 2),
            ("Receta Oficial+Mutuas", 3),
            ("Receta Privada", 4),
            ("Mutuas", 5),
            ("Receta Oficial", 6),
        ]
        records: list[dict[str, Any]] = []
        previous: list[Any] = []
        value_dicts = dataset.get("ValueDicts") or {}

        for row in rows:
            expanded = _expand_powerbi_row(row, previous, 7)
            previous = expanded
            if len(expanded) < 7:
                continue

            year = _to_int(expanded[1])
            if year is None or not 2014 <= year <= 2021:
                continue

            geography = _normalize_ccaa_name(_decode_powerbi_dict_value(expanded[0], value_dicts, "D0"))
            for category, index in metrics:
                dhd = _none_if_empty(expanded[index])
                if dhd is None:
                    continue
                records.append(
                    {
                        "record_type": "consumption",
                        "year": year,
                        "month": None,
                        "geography": geography,
                        "geography_type": "autonomous_community",
                        "sector": "Comunitario",
                        "category": category,
                        "atc_code": "J01",
                        "drug_name": None,
                        "active_ingredient": None,
                        "packages": None,
                        "ddd": None,
                        "dhd": dhd,
                        "amount_pvpiva": None,
                        "unit": "DHD",
                        "notes": (
                            "PRAN public Power BI report: Consumo de antibioticos de uso sistemico (J01) "
                            "en sector comunitario por comunidad autonoma, DHD."
                        ),
                        "therapeutic_group": "antibiotics",
                        **resource.traceability(),
                    }
                )
        return records


def _j01_community_by_ccaa_powerbi_payload() -> dict[str, Any]:
    year = "A\u00d1O"
    year_month = "A\u00d1OMES"
    atc_j01 = "J01 - ANTIBACTERIANOS PARA USO SIST\u00c9MICO"
    return {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {
                    "Commands": [
                        {
                            "SemanticQueryDataShapeCommand": {
                                "Query": {
                                    "Version": 2,
                                    "From": [
                                        {"Name": "cc", "Entity": "CCAA", "Type": 0},
                                        {"Name": "f", "Entity": "FECHAS", "Type": 0},
                                        {"Name": "d", "Entity": "CONSUMOS_DETALLE_CODNAC2", "Type": 0},
                                        {"Name": "i", "Entity": "CONSUMOS_IMS_AEMPS", "Type": 0},
                                        {"Name": "j", "Entity": "CONSUMOS_JERARQUIA2", "Type": 0},
                                    ],
                                    "Select": [
                                        {
                                            "Column": {"Expression": {"SourceRef": {"Source": "cc"}}, "Property": "DES_CCAA"},
                                            "Name": "CCAA.DES_CCAA",
                                        },
                                        {
                                            "Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": year},
                                            "Name": f"FECHAS.{year}",
                                        },
                                        {
                                            "Measure": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "DHD_AEMPS_AP"},
                                            "Name": "CONSUMOS_DETALLE_CODNAC2.DHD_AEMPS_AP",
                                        },
                                        {
                                            "Measure": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "DHD_AEMPS"},
                                            "Name": "CONSUMOS_DETALLE_CODNAC2.DHD_AEMPS",
                                        },
                                        {
                                            "Measure": {
                                                "Expression": {"SourceRef": {"Source": "i"}},
                                                "Property": "DHD AP Rec Priv (Tot-Reem)",
                                            },
                                            "Name": "CONSUMOS_IMS_AEMPS.DHD AP Rec Priv (Tot-Reem)",
                                        },
                                        {
                                            "Measure": {
                                                "Expression": {"SourceRef": {"Source": "d"}},
                                                "Property": "DHD_AEMPS para Mutuas",
                                            },
                                            "Name": "CONSUMOS_DETALLE_CODNAC2.DHD_AEMPS para Mutuas",
                                        },
                                        {
                                            "Measure": {
                                                "Expression": {"SourceRef": {"Source": "d"}},
                                                "Property": "DHD_AEMPS para Receta Oficial",
                                            },
                                            "Name": "CONSUMOS_DETALLE_CODNAC2.DHD_AEMPS para Receta Oficial",
                                        },
                                    ],
                                    "Where": [
                                        {
                                            "Condition": {
                                                "In": {
                                                    "Expressions": [
                                                        {
                                                            "Column": {
                                                                "Expression": {"SourceRef": {"Source": "j"}},
                                                                "Property": "N2_ATC",
                                                            }
                                                        }
                                                    ],
                                                    "Values": [
                                                        [{"Literal": {"Value": f"'{atc_j01}'"}}],
                                                        [{"Literal": {"Value": "'J01 - ANTIBACTERIANOS PARA USO SISTEMICO'"}}],
                                                    ],
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "And": {
                                                    "Left": {
                                                        "Comparison": {
                                                            "ComparisonKind": 3,
                                                            "Left": {
                                                                "Column": {
                                                                    "Expression": {"SourceRef": {"Source": "f"}},
                                                                    "Property": year,
                                                                }
                                                            },
                                                            "Right": {"Literal": {"Value": "2022L"}},
                                                        }
                                                    },
                                                    "Right": {
                                                        "Comparison": {
                                                            "ComparisonKind": 2,
                                                            "Left": {
                                                                "Column": {
                                                                    "Expression": {"SourceRef": {"Source": "f"}},
                                                                    "Property": year,
                                                                }
                                                            },
                                                            "Right": {"Literal": {"Value": "2014L"}},
                                                        }
                                                    },
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "Comparison": {
                                                    "ComparisonKind": 4,
                                                    "Left": {
                                                        "Column": {
                                                            "Expression": {"SourceRef": {"Source": "f"}},
                                                            "Property": year_month,
                                                        }
                                                    },
                                                    "Right": {"Literal": {"Value": "202412L"}},
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "Not": {
                                                    "Expression": {
                                                        "In": {
                                                            "Expressions": [
                                                                {
                                                                    "Column": {
                                                                        "Expression": {"SourceRef": {"Source": "j"}},
                                                                        "Property": "VTM_TERM",
                                                                    }
                                                                }
                                                            ],
                                                            "Values": [[{"Literal": {"Value": "null"}}]],
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                    ],
                                    "OrderBy": [
                                        {
                                            "Direction": 1,
                                            "Expression": {
                                                "Column": {"Expression": {"SourceRef": {"Source": "cc"}}, "Property": "DES_CCAA"}
                                            },
                                        },
                                        {
                                            "Direction": 1,
                                            "Expression": {
                                                "Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": year}
                                            },
                                        },
                                    ],
                                },
                                "Binding": {
                                    "Primary": {"Groupings": [{"Projections": [0, 1, 2, 3, 4, 5, 6]}]},
                                    "DataReduction": {"DataVolume": 4, "Primary": {"Window": {"Count": 5000}}},
                                    "Version": 1,
                                },
                                "ExecutionMetricsKind": 1,
                            }
                        }
                    ]
                },
                "CacheKey": "",
                "QueryId": "",
                "ApplicationContext": {
                    "DatasetId": PRAN_J01_CCAA_DATASET_ID,
                    "Sources": [{"ReportId": PRAN_J01_CCAA_REPORT_ID, "VisualId": PRAN_J01_CCAA_VISUAL_ID}],
                },
            }
        ],
        "cancelQueries": [],
        "modelId": PRAN_J01_CCAA_MODEL_ID,
    }


def _powerbi_resource_key(report_url: str) -> str | None:
    token = parse_qs(urlparse(report_url).query).get("r", [None])[0]
    if not token:
        return None
    try:
        padding = "=" * (-len(token) % 4)
        payload = json.loads(urlsafe_b64decode(f"{token}{padding}").decode("utf-8"))
    except Exception:
        return None
    key = payload.get("k")
    return str(key) if key else None


def _decode_powerbi_dict_value(value: object, value_dicts: dict[str, Any], dict_name: str) -> str:
    values = value_dicts.get(dict_name) or []
    if isinstance(value, int) and 0 <= value < len(values):
        return str(values[value])
    return str(value)


def _expand_powerbi_row(row: dict[str, Any], previous: list[Any], column_count: int) -> list[Any]:
    values = list(row.get("C") or [])
    repeat_mask = int(row.get("R") or 0)
    null_mask = int(row.get("\u00d8") or 0)
    expanded: list[Any] = []
    value_index = 0

    for column_index in range(column_count):
        bit = 1 << column_index
        if repeat_mask & bit:
            expanded.append(previous[column_index] if column_index < len(previous) else None)
        elif null_mask & bit:
            expanded.append(None)
        elif value_index < len(values):
            expanded.append(values[value_index])
            value_index += 1
        else:
            expanded.append(None)

    return expanded


def _normalize_ccaa_name(value: str) -> str:
    labels = {
        "ANDALUCIA": "Andalucia",
        "ARAGON": "Aragon",
        "ASTURIAS": "Asturias",
        "BALEARES": "Illes Balears",
        "CANARIAS": "Canarias",
        "CANTABRIA": "Cantabria",
        "CASTILLA Y LEON": "Castilla y Leon",
        "CASTILLA-LA MANCHA": "Castilla-La Mancha",
        "CATALU\u00d1A": "Cataluna",
        "CEUTA": "Ceuta",
        "COMUNIDAD DE MADRID": "Comunidad de Madrid",
        "COMUNIDAD VALENCIANA": "Comunitat Valenciana",
        "EXTREMADURA": "Extremadura",
        "GALICIA": "Galicia",
        "LA RIOJA": "La Rioja",
        "MELILLA": "Melilla",
        "NAVARRA": "Navarra",
        "PAIS VASCO": "Pais Vasco",
        "REGION DE MURCIA": "Region de Murcia",
    }
    return labels.get(value.strip().upper(), value.strip().title())


def _to_int(value: object) -> int | None:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _none_if_empty(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


PRANConsumptionScraper = PranAntibioticsScraper
