from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

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
PRAN_POWERBI_PAYLOAD_DIR = Path(__file__).resolve().parent / "payloads"


class PranAntibioticsScraper(BaseScraper):
    source_name = "PRAN human antibiotic consumption"
    base_url = "https://www.resistenciaantibioticos.es"
    start_url = PRAN_SEED_URLS[0]
    raw_subdir = "pran"
    parser_version = "pran-antibiotics-0.3"

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


PRANConsumptionScraper = PranAntibioticsScraper
