from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.normalizers.text import clean_text
from app.scrapers.base import BaseScraper, ScrapedResource


DOWNLOAD_EXTENSIONS = {".csv", ".xls", ".xlsx", ".pdf", ".zip", ".json"}


class LinkDiscoveryScraper(BaseScraper):
    source_name = "Public link discovery"
    start_url = ""
    raw_subdir = "discovery"

    def scrape(self, limit: int = 50) -> list[ScrapedResource]:
        response = self.fetch(self.start_url)
        raw_path = self.save_raw_bytes(self.start_url, response.content, ".html")
        soup = BeautifulSoup(response.text, "html.parser")
        resources: list[ScrapedResource] = []
        for link in soup.select("a[href]"):
            href = link.get("href")
            if not href:
                continue
            url = self.absolutize(href)
            extension = _extension(url)
            title = clean_text(link.get_text(" ")) or url
            if extension not in DOWNLOAD_EXTENSIONS and not _looks_relevant(title, url):
                continue
            resources.append(
                ScrapedResource(
                    source_name=self.source_name,
                    source_url=self.start_url,
                    resource_type="document" if extension == ".pdf" else "dataset_link",
                    title=title,
                    url=url,
                    accessed_at=datetime.utcnow(),
                    raw_path=str(raw_path),
                    metadata={"extension": extension, "requires_parser": extension not in {".csv", ".xls", ".xlsx"}},
                )
            )
            if len(resources) >= limit:
                break
        return resources


def _extension(url: str) -> str:
    return "." + urlparse(url).path.rsplit(".", 1)[-1].lower() if "." in urlparse(url).path else ""


def _looks_relevant(title: str, url: str) -> bool:
    text = f"{title} {url}".casefold()
    terms = ["atc", "medic", "farmac", "antibi", "proa", "consumo", "benzodia", "psicof"]
    return any(term in text for term in terms)

