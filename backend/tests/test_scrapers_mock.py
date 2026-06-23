from datetime import datetime
from pathlib import Path

import requests

from app.scrapers.aemps import AempsSafetyAlertsScraper
from app.scrapers.asturias import AsturiasPublicDocsScraper
from app.scrapers.base import BaseScraper, FetchResult, ScrapedResource
from app.scrapers.pran import PranAntibioticsScraper
from app.scrapers.sanidad import SanidadConsumptionScraper
from app.scrapers.universities import SpanishUniversityPublicationsScraper


class TmpAempsScraper(AempsSafetyAlertsScraper):
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        super().__init__(delay_seconds=0, respect_robots=False)

    @property
    def raw_dir(self) -> Path:
        path = self.tmp_path / "raw"
        path.mkdir(exist_ok=True)
        return path

    @property
    def processed_dir(self) -> Path:
        path = self.tmp_path / "processed"
        path.mkdir(exist_ok=True)
        return path

    @property
    def metadata_dir(self) -> Path:
        path = self.tmp_path / "metadata"
        path.mkdir(exist_ok=True)
        return path

    def fetch_url(self, url: str, extension: str | None = None, save: bool = True) -> FetchResult:
        if url.endswith("detail"):
            text = """
            <html><body><main><h1>Nota sobre amoxicillin</h1>
            <p>15 de junio de 2021. Medicamentos que contienen amoxicillin.</p>
            <a href="note.pdf">PDF</a></main></body></html>
            """
        elif url.endswith("note.pdf"):
            raw = self.raw_dir / "note.pdf"
            raw.write_bytes(b"%PDF-1.4 mock")
            return FetchResult(url, datetime.utcnow(), 200, "application/pdf", str(raw), content=b"%PDF-1.4 mock")
        else:
            text = '<html><body><a href="https://www.aemps.gob.es/detail">Nota de seguridad medicamento</a></body></html>'
        raw = self.raw_dir / "page.html"
        raw.write_text(text, encoding="utf-8")
        return FetchResult(url, datetime.utcnow(), 200, "text/html", str(raw), text=text, content=text.encode())


def test_aemps_mock_html_does_not_need_network(tmp_path: Path) -> None:
    scraper = TmpAempsScraper(tmp_path)
    rows = scraper.run(limit=1)
    assert rows[0]["record_type"] == "safety_alert"
    assert rows[0]["date"] == "2021-06-15"
    assert "amoxicillin" in rows[0]["possible_active_ingredients"]
    assert rows[0]["raw_file_path"]


def test_sanidad_normalize_missing_columns_from_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "consumption.csv"
    csv_path.write_text("Ano,CCAA,DHD\n2024,Asturias,11.9\n", encoding="utf-8")
    scraper = SanidadConsumptionScraper(delay_seconds=0, respect_robots=False)
    resource = ScrapedResource(
        source_name=scraper.source_name,
        source_url="https://example.test/source",
        resource_type="dataset_file",
        title="mock csv",
        url="https://example.test/consumption.csv",
        accessed_at=datetime.utcnow(),
        raw_path=str(csv_path),
        parser_version=scraper.parser_version,
    )
    rows = scraper.normalize([resource])
    assert rows[0]["record_type"] == "consumption"
    assert rows[0]["year"] == 2024
    assert rows[0]["atc_code"] is None


def test_pran_powerbi_querydata_normalizes_dhd_rows() -> None:
    scraper = PranAntibioticsScraper(delay_seconds=0, respect_robots=False)
    querydata = """
    {
      "results": [{
        "result": {
          "data": {
            "dsr": {
              "DS": [{
                "PH": [{
                  "DM0": [{
                    "S": [{"N": "G0"}, {"N": "M0"}, {"N": "M1"}, {"N": "M2"}, {"N": "M3"}, {"N": "M4"}],
                    "C": [2024, "16.50", "6.30", "22.80", "0.88", "15.62"]
                  }]
                }]
              }]
            }
          }
        }
      }]
    }
    """
    resource = ScrapedResource(
        source_name=scraper.source_name,
        source_url="https://www.resistenciaantibioticos.es/pran",
        resource_type="powerbi_querydata",
        title="PRAN J01 community antibiotic consumption DHD",
        url="https://wabi-north-europe-api.analysis.windows.net/public/reports/querydata?synchronous=true",
        accessed_at=datetime.utcnow(),
        raw_path="raw/pran-query.json",
        content_text=querydata,
        parser_version=scraper.parser_version,
    )

    rows = scraper.normalize([resource])

    assert len(rows) == 5
    global_row = next(row for row in rows if row["category"] == "Global comunitario")
    assert global_row["record_type"] == "consumption"
    assert global_row["year"] == 2024
    assert global_row["atc_code"] == "J01"
    assert global_row["dhd"] == "22.80"
    assert global_row["unit"] == "DHD"


class TmpBaseScraper(BaseScraper):
    source_name = "Temporary test source"
    base_url = "https://broken.example"
    raw_subdir = "tmp-base"

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        super().__init__(delay_seconds=0)

    @property
    def raw_dir(self) -> Path:
        path = self.tmp_path / "base_raw"
        path.mkdir(exist_ok=True)
        return path

    @property
    def processed_dir(self) -> Path:
        path = self.tmp_path / "base_processed"
        path.mkdir(exist_ok=True)
        return path

    @property
    def metadata_dir(self) -> Path:
        path = self.tmp_path / "base_metadata"
        path.mkdir(exist_ok=True)
        return path

    def parse(self, limit: int = 50, **_: object) -> list[ScrapedResource]:
        return []


def test_base_scraper_skips_origin_after_ssl_failure(monkeypatch, tmp_path: Path) -> None:
    scraper = TmpBaseScraper(tmp_path)
    calls = []

    def fail_get(url: str, **_: object) -> object:
        calls.append(url)
        raise requests.exceptions.SSLError("certificate verify failed")

    monkeypatch.setattr(scraper.session, "get", fail_get)
    first = scraper.fetch_url("https://broken.example/page")
    second = scraper.fetch_url("https://broken.example/other")

    assert "certificate verify failed" in (first.error or "")
    assert "ssl_verification_failed" in (second.error or "")
    assert calls == ["https://broken.example/robots.txt"]


def test_asturias_pdf_mock_metadata(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "proa.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")
    monkeypatch.setattr("app.scrapers.asturias.extract_pdf_text", lambda _path: "Informe PROA antibioticos Asturias 2024")
    scraper = AsturiasPublicDocsScraper(delay_seconds=0, respect_robots=False)
    resource = ScrapedResource(
        source_name=scraper.source_name,
        source_url="https://www.astursalud.es/",
        resource_type="document",
        title="Informe PROA",
        url="https://www.astursalud.es/proa.pdf",
        accessed_at=datetime.utcnow(),
        raw_path=str(pdf_path),
        parser_version=scraper.parser_version,
    )
    rows = scraper.normalize([resource])
    assert rows[0]["record_type"] == "study_document"
    assert rows[0]["year"] == 2024
    assert rows[0]["geography"] == "Asturias"
    assert rows[0]["therapeutic_group"] == "antibiotics"


class TmpUniversityScraper(SpanishUniversityPublicationsScraper):
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        super().__init__(delay_seconds=0, respect_robots=False)

    @property
    def raw_dir(self) -> Path:
        path = self.tmp_path / "university_raw"
        path.mkdir(exist_ok=True)
        return path

    @property
    def processed_dir(self) -> Path:
        path = self.tmp_path / "university_processed"
        path.mkdir(exist_ok=True)
        return path

    @property
    def metadata_dir(self) -> Path:
        path = self.tmp_path / "university_metadata"
        path.mkdir(exist_ok=True)
        return path

    def fetch_url(self, url: str, extension: str | None = None, save: bool = True) -> FetchResult:
        text = """
        <html><head>
          <title>Evolucion del consumo de antibioticos</title>
          <meta name="citation_author" content="Laura Calle-Miguel" />
          <meta name="citation_author" content="Ana Isabel Iglesias Carbajo" />
        </head><body>
          <h1>Evolucion del consumo de antibioticos a nivel extrahospitalario en Asturias</h1>
          <p>Journal: Anales de Pediatria</p>
          <p>Year of publication: 2021</p>
          <p>DOI: 10.1016/J.ANPEDI.2020.11.010</p>
          <h2>Abstract</h2>
          <p>Antibiotic consumption in pediatric outpatients in Principado de Asturias, J01, DDD and DID.</p>
        </body></html>
        """
        raw = self.raw_dir / "publication.html"
        raw.write_text(text, encoding="utf-8")
        return FetchResult(url, datetime.utcnow(), 200, "text/html", str(raw), text=text, content=text.encode())


def test_university_scraper_extracts_publication_metadata(tmp_path: Path) -> None:
    scraper = TmpUniversityScraper(tmp_path)
    rows = scraper.run(limit=1)
    assert rows[0]["record_type"] == "study_document"
    assert rows[0]["year"] == 2021
    assert rows[0]["doi"].lower() == "10.1016/j.anpedi.2020.11.010"
    assert rows[0]["therapeutic_group"] == "antibiotics"
    assert "Laura Calle-Miguel" in rows[0]["authors"]
