from __future__ import annotations

from pathlib import Path
from typing import Any

from app.normalizers.consumption import normalize_consumption_dataframe
from app.normalizers.text import clean_text
from app.scrapers.base import BaseScraper, ScrapedResource
from app.scrapers.tabular import DATASET_EXTENSIONS, discover_links, read_tabular_file, relevant_dataset_links, rows_to_jsonable


SANIDAD_SEED_URLS = [
    "https://www.sanidad.gob.es/gabinete/notasPrensa.do?id=5655",
    "https://pestadistico.inteligenciadegestion.sanidad.gob.es/publicoSNS/D/consumo-farmaceutico-en-el-sns/consumo-en-recetas-medicas-sns/consumo-medicamentos-por-atc/nota-metodologica",
]
SANIDAD_KEYWORDS = {
    "consumo",
    "farmaceutico",
    "medicamento",
    "medicamentos",
    "recetas",
    "atc",
    "sns",
    "dhd",
    "envases",
    "pvpiva",
}


class SanidadConsumptionScraper(BaseScraper):
    source_name = "Ministry of Health medicine consumption by ATC"
    base_url = "https://www.sanidad.gob.es"
    start_url = SANIDAD_SEED_URLS[0]
    raw_subdir = "sanidad"
    parser_version = "sanidad-consumption-0.3"

    def parse(self, limit: int = 50, **_: Any) -> list[ScrapedResource]:
        resources: list[ScrapedResource] = []
        seen: set[str] = set()
        for seed_url in SANIDAD_SEED_URLS:
            page = self.fetch_url(seed_url, ".html")
            if page.error:
                resources.append(self.error_resource(seed_url, "seed_fetch_failed", page.error))
                continue
            links = relevant_dataset_links(discover_links(page.text or "", seed_url, self.absolutize), SANIDAD_KEYWORDS)
            if not links:
                resources.append(
                    ScrapedResource(
                        source_name=self.source_name,
                        source_url=seed_url,
                        resource_type="source_page",
                        title="Sanidad consumption source page",
                        url=seed_url,
                        accessed_at=page.accessed_at,
                        raw_path=page.raw_file_path,
                        content_text=clean_text((page.text or "")[:2000]),
                        metadata={"status": "no_direct_dataset_link_found"},
                        parser_version=self.parser_version,
                    )
                )
            for link in links:
                if link["url"] in seen:
                    continue
                seen.add(link["url"])
                if link["extension"] not in DATASET_EXTENSIONS:
                    resources.append(self._link_resource(seed_url, page, link, "dataset_link"))
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
                        content_text=None,
                        metadata={
                            "extension": link["extension"],
                            "download_error": dataset.error,
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
            if resource.resource_type != "dataset_file" or not resource.raw_path:
                rows.append(self._metadata_record(resource))
                continue
            try:
                sheets = read_tabular_file(Path(resource.raw_path))
                for sheet_name, frame in sheets:
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
                        record.update({"record_type": "consumption", "sheet_name": sheet_name})
                        rows.append(record)
            except Exception as exc:
                self.log_error("tabular_normalization_failed", resource.url, exc)
                rows.append(self.error_payload(resource.url, "tabular_normalization_failed", exc))
        return rows

    def _link_resource(self, seed_url: str, page, link: dict[str, str], resource_type: str) -> ScrapedResource:
        return ScrapedResource(
            source_name=self.source_name,
            source_url=seed_url,
            resource_type=resource_type,
            title=link["title"],
            url=link["url"],
            accessed_at=page.accessed_at,
            raw_path=page.raw_file_path,
            metadata={"extension": link["extension"], "requires_source_specific_parser": True},
            parser_version=self.parser_version,
        )

    def _metadata_record(self, resource: ScrapedResource) -> dict[str, Any]:
        metadata = resource.metadata or {}
        return {
            "record_type": resource.resource_type,
            "title": resource.title,
            "url": resource.url,
            "status": metadata.get("status") or metadata.get("download_error") or "not_structured",
            "metadata": metadata,
            **resource.traceability(),
        }

