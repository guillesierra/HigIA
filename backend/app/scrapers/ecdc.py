from __future__ import annotations

from typing import Any

from app.normalizers.text import clean_text
from app.scrapers.base import BaseScraper, ScrapedResource
from app.scrapers.tabular import DATASET_EXTENSIONS, discover_links, html_tables_to_dataframes, relevant_dataset_links, rows_to_jsonable
from app.normalizers.consumption import normalize_consumption_dataframe


ECDC_SEED_URLS = [
    "https://www.ecdc.europa.eu/en/antimicrobial-consumption/database/rates-country",
    "https://www.ecdc.europa.eu/en/antimicrobial-consumption/database",
    "https://www.ecdc.europa.eu/en/publications-data/antimicrobial-consumption-eueea-annual-epidemiological-report",
]

ESAC_NET_SEED = "https://www.esac.ua.ac.be/main.aspx?c=*SABE&n=60096"
ESNAMED_URL = "https://www.aemps.gob.es/medicamentosUsoHumano/observatorio/informes-publicados/informes-uso-antibioticos-espana/"

ECDC_KEYWORDS = {
    "antimicrobial", "consumption", "ddd", "did", "antibiotic",
    "antibiotics", "rate", "country", "database", "surveillance",
    "community", "hospital", "atc", "j01",
}


class EuropeAntimicrobialScraper(BaseScraper):
    source_name = "ECDC / ESAC-Net antimicrobial consumption"
    base_url = "https://www.ecdc.europa.eu"
    start_url = ECDC_SEED_URLS[0]
    raw_subdir = "ecdc"
    parser_version = "ecdc-antimicrobial-0.4"

    def parse(self, limit: int = 50, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        seen: set[str] = set()

        for seed_url in ECDC_SEED_URLS:
            page = self.fetch_url(seed_url, ".html")
            if page.error:
                resources.append(self.error_resource(seed_url, "ecdc_seed_fetch_failed", page.error))
                continue
            resources.append(
                ScrapedResource(
                    source_name=self.source_name,
                    source_url=seed_url,
                    resource_type="source_page",
                    title="ECDC / ESAC-Net antimicrobial consumption",
                    url=seed_url,
                    accessed_at=page.accessed_at,
                    raw_path=page.raw_file_path,
                    content_text=clean_text((page.text or "")[:2000]),
                    metadata={"status": "page_indexed"},
                    parser_version=self.parser_version,
                )
            )
            if page.text:
                links = relevant_dataset_links(
                    discover_links(page.text, seed_url, self.absolutize),
                    ECDC_KEYWORDS,
                )
                for link in links:
                    if link["url"] in seen:
                        continue
                    seen.add(link["url"])
                    if link["extension"] in DATASET_EXTENSIONS:
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
                                    "origin_page_raw_file_path": page.raw_file_path,
                                    "therapeutic_group": "antibiotics",
                                },
                                parser_version=self.parser_version,
                            )
                        )
                for table_idx, frame in enumerate(html_tables_to_dataframes(page.text), start=1):
                    if frame.shape[0] < 2:
                        continue
                    resources.append(
                        ScrapedResource(
                            source_name=self.source_name,
                            source_url=seed_url,
                            resource_type="html_tables",
                            title=f"ECDC HTML table {table_idx}",
                            url=seed_url,
                            accessed_at=page.accessed_at,
                            raw_path=page.raw_file_path,
                            metadata={
                                "table_index": table_idx,
                                "therapeutic_group": "antibiotics",
                                "columns": list(frame.columns),
                            },
                            parser_version=self.parser_version,
                        )
                    )
            if len(resources) >= limit:
                break
        return resources[:limit]

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            if resource.resource_type == "dataset_file" and resource.raw_path:
                rows.extend(self._normalize_dataset(resource))
            elif resource.resource_type == "html_tables" and resource.raw_path:
                rows.extend(self._normalize_html_tables(resource))
            else:
                rows.append({
                    "record_type": resource.resource_type,
                    "title": resource.title,
                    "url": resource.url,
                    "metadata": resource.metadata or {},
                    **resource.traceability(),
                })
        return rows

    def _normalize_dataset(self, resource: ScrapedResource) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            from app.scrapers.tabular import read_tabular_file
            from pathlib import Path

            for sheet_name, frame in read_tabular_file(Path(resource.raw_path)):
                normalized = normalize_consumption_dataframe(
                    frame,
                    source_name=resource.source_name,
                    source_url=resource.url,
                    accessed_at=resource.accessed_at.isoformat(),
                    raw_file_path=resource.raw_path,
                    parser_version=resource.parser_version,
                    default_geography="Europe",
                    context_text=f"ECDC {resource.title} {sheet_name}",
                )
                for record in rows_to_jsonable(normalized):
                    record.update({
                        "record_type": "consumption",
                        "sheet_name": sheet_name,
                        "therapeutic_group": "antibiotics",
                    })
                    rows.append(record)
        except Exception as exc:
            self.log_error("ecdc_dataset_normalization_failed", resource.url, exc)
            rows.append(self.error_payload(resource.url, "ecdc_dataset_normalization_failed", exc))
        return rows

    def _normalize_html_tables(self, resource: ScrapedResource) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            from pathlib import Path
            html = Path(resource.raw_path).read_text(encoding="utf-8", errors="ignore")
            for index, frame in enumerate(html_tables_to_dataframes(html), start=1):
                normalized = normalize_consumption_dataframe(
                    frame,
                    source_name=resource.source_name,
                    source_url=resource.url,
                    accessed_at=resource.accessed_at.isoformat(),
                    raw_file_path=resource.raw_path,
                    parser_version=resource.parser_version,
                    default_geography="Europe",
                    context_text=f"ECDC table {index} antibiotics",
                )
                for record in rows_to_jsonable(normalized):
                    record.update({
                        "record_type": "consumption",
                        "table_index": index,
                        "therapeutic_group": "antibiotics",
                    })
                    rows.append(record)
        except Exception as exc:
            self.log_error("ecdc_html_table_normalization_failed", resource.url, exc)
            rows.append(self.error_payload(resource.url, "ecdc_html_table_normalization_failed", exc))
        return rows


class AempsAntibioticsScraper(BaseScraper):
    source_name = "AEMPS antibiotic use reports Spain"
    base_url = "https://www.aemps.gob.es"
    start_url = ESNAMED_URL
    raw_subdir = "esnamed"
    parser_version = "esnamed-antibiotics-0.4"

    def parse(self, limit: int = 50, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        seen: set[str] = set()

        page = self.fetch_url(self.start_url, ".html")
        if page.error:
            return [self.error_resource(self.start_url, "esnamed_fetch_failed", page.error)]

        resources.append(
            ScrapedResource(
                source_name=self.source_name,
                source_url=self.start_url,
                resource_type="source_page",
                title="Informes uso de antibioticos Espana",
                url=self.start_url,
                accessed_at=page.accessed_at,
                raw_path=page.raw_file_path,
                content_text=clean_text((page.text or "")[:2000]),
                metadata={"status": "page_indexed"},
                parser_version=self.parser_version,
            )
        )

        if page.text:
            links = relevant_dataset_links(
                discover_links(page.text, self.start_url, self.absolutize),
                {"antibiotico", "antibiotic", "consumo", "informe", "uso", "espana", "datos", "dhd", "ddd"},
            )
            for link in links:
                if link["url"] in seen:
                    continue
                seen.add(link["url"])
                if link["extension"] in DATASET_EXTENSIONS:
                    dataset = self.fetch_url(link["url"], link["extension"])
                    resources.append(
                        ScrapedResource(
                            source_name=self.source_name,
                            source_url=self.start_url,
                            resource_type="dataset_file" if not dataset.error else "source_error",
                            title=link["title"],
                            url=link["url"],
                            accessed_at=dataset.accessed_at,
                            raw_path=dataset.raw_file_path,
                            metadata={
                                "extension": link["extension"],
                                "download_error": dataset.error,
                                "therapeutic_group": "antibiotics",
                            },
                            parser_version=self.parser_version,
                        )
                    )
                if len(resources) >= limit:
                    break

        return resources[:limit]

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for resource in resources:
            if resource.resource_type == "dataset_file" and resource.raw_path:
                try:
                    from app.scrapers.tabular import read_tabular_file
                    from pathlib import Path

                    for sheet_name, frame in read_tabular_file(Path(resource.raw_path)):
                        normalized = normalize_consumption_dataframe(
                            frame,
                            source_name=resource.source_name,
                            source_url=resource.url,
                            accessed_at=resource.accessed_at.isoformat(),
                            raw_file_path=resource.raw_path,
                            parser_version=resource.parser_version,
                            default_geography="Spain",
                            context_text=f"{resource.title} {sheet_name}",
                        )
                        for record in rows_to_jsonable(normalized):
                            record.update({
                                "record_type": "consumption",
                                "sheet_name": sheet_name,
                                "therapeutic_group": "antibiotics",
                            })
                            rows.append(record)
                except Exception as exc:
                    self.log_error("esnamed_dataset_normalization_failed", resource.url, exc)
                    rows.append(self.error_payload(resource.url, "esnamed_dataset_normalization_failed", exc))
            else:
                rows.append({
                    "record_type": resource.resource_type,
                    "title": resource.title,
                    "url": resource.url,
                    "metadata": resource.metadata or {},
                    **resource.traceability(),
                })
        return rows


EcdcAntimicrobialScraper = EuropeAntimicrobialScraper
