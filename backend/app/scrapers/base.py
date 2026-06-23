from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
METADATA_ROOT = PROJECT_ROOT / "data" / "metadata"
USER_AGENT = (
    "PharmaImpact-HigIA/0.2 public research scraper "
    "(no personal data; contact: configure repository README)"
)
DEFAULT_HEADERS = {"User-Agent": USER_AGENT}


@dataclass
class FetchResult:
    url: str
    accessed_at: datetime
    status_code: int | None
    content_type: str | None
    raw_file_path: str | None
    text: str | None = None
    content: bytes | None = None
    error: str | None = None


@dataclass
class ScrapedResource:
    source_name: str
    source_url: str
    resource_type: str
    title: str
    url: str
    accessed_at: datetime
    raw_path: str | None = None
    content_text: str | None = None
    metadata: dict[str, Any] | None = None
    parser_version: str = "base-0.2"

    def traceability(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "accessed_at": self.accessed_at.isoformat(),
            "raw_file_path": self.raw_path,
            "parser_version": self.parser_version,
        }

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["accessed_at"] = self.accessed_at.isoformat()
        return payload


class BaseScraper:
    source_name = "Base public source"
    base_url = ""
    start_url = ""
    raw_subdir = "base"
    parser_version = "base-0.2"

    def __init__(
        self,
        timeout: int = 30,
        delay_seconds: float = 1.0,
        respect_robots: bool = True,
    ) -> None:
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.respect_robots = respect_robots
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._robots_cache: dict[str, RobotFileParser | None] = {}
        self._last_request_at = 0.0
        self.logger = logging.getLogger(f"higia.scrapers.{self.raw_subdir}")
        self.logger.setLevel(logging.INFO)
        self._ensure_dirs()

    @property
    def entry_url(self) -> str:
        return self.start_url or self.base_url

    @property
    def raw_dir(self) -> Path:
        path = RAW_ROOT / self.raw_subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def processed_dir(self) -> Path:
        path = PROCESSED_ROOT / self.raw_subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def metadata_dir(self) -> Path:
        path = METADATA_ROOT / self.raw_subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run(self, limit: int = 50, **kwargs: Any) -> list[dict[str, Any]]:
        """Run parse and normalize, persisting normalized JSON even on partial failure."""
        self.write_source_metadata()
        resources: list[ScrapedResource] = []
        try:
            resources = self.parse(limit=limit, **kwargs)
        except Exception as exc:
            self.log_error("parse_failed", self.entry_url, exc)
            resources = [self.error_resource(self.entry_url, "parse_failed", exc)]

        try:
            normalized = self.normalize(resources)
        except Exception as exc:
            self.log_error("normalize_failed", self.entry_url, exc)
            normalized = [self.error_payload(self.entry_url, "normalize_failed", exc)]

        self.save_normalized_json(normalized)
        return normalized

    def scrape(self, limit: int = 50, **kwargs: Any) -> list[ScrapedResource]:
        """Compatibility wrapper returning intermediate resources."""
        self.write_source_metadata()
        return self.parse(limit=limit, **kwargs)

    def parse(self, limit: int = 50, **kwargs: Any) -> list[ScrapedResource]:
        raise NotImplementedError

    def normalize(self, resources: list[ScrapedResource]) -> list[dict[str, Any]]:
        return [resource.as_dict() for resource in resources]

    def fetch_url(self, url: str, extension: str | None = None, save: bool = True) -> FetchResult:
        accessed_at = datetime.utcnow()
        if not self.can_fetch(url):
            error = f"robots.txt disallows fetch: {url}"
            self.log_error("robots_disallow", url, error)
            return FetchResult(url, accessed_at, None, None, None, error=error)

        self._delay()
        try:
            response = self.session.get(url, timeout=self.timeout)
            content_type = response.headers.get("content-type", "")
            raw_path = None
            if save:
                raw_path = str(self.save_raw(url, response.content, extension or self.extension_for(url, content_type)))
            self.log_fetch(url, response.status_code, raw_path, content_type)
            if response.status_code >= 400:
                return FetchResult(
                    url=url,
                    accessed_at=accessed_at,
                    status_code=response.status_code,
                    content_type=content_type,
                    raw_file_path=raw_path,
                    content=response.content,
                    text=response.text,
                    error=f"HTTP {response.status_code}",
                )
            return FetchResult(
                url=url,
                accessed_at=accessed_at,
                status_code=response.status_code,
                content_type=content_type,
                raw_file_path=raw_path,
                content=response.content,
                text=response.text,
            )
        except requests.RequestException as exc:
            self.log_error("request_failed", url, exc)
            return FetchResult(url, accessed_at, None, None, None, error=str(exc))

    def fetch(self, url: str) -> requests.Response:
        """Compatibility method for older code paths."""
        if not self.can_fetch(url):
            raise RuntimeError(f"robots.txt disallows fetch: {url}")
        self._delay()
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response

    def soup(self, url: str) -> BeautifulSoup:
        result = self.fetch_url(url)
        return BeautifulSoup(result.text or "", "html.parser")

    def save_raw(self, url: str, content: bytes, extension: str | None = None) -> Path:
        parsed = urlparse(url)
        suffix = extension or Path(parsed.path).suffix or ".html"
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        stem = Path(parsed.path).stem or parsed.netloc or "index"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        path = self.raw_dir / f"{timestamp}_{safe_filename(stem)}{suffix}"
        path.write_bytes(content)
        return path

    def save_raw_bytes(self, url: str, content: bytes, extension: str | None = None) -> Path:
        return self.save_raw(url, content, extension)

    def save_normalized_json(self, rows: list[dict[str, Any]]) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        path = self.processed_dir / f"{timestamp}_normalized.json"
        payload = json.dumps(rows, ensure_ascii=False, indent=2, default=json_default)
        path.write_text(payload, encoding="utf-8")
        latest = self.processed_dir / "latest_normalized.json"
        latest.write_text(payload, encoding="utf-8")
        return path

    def write_source_metadata(self) -> None:
        metadata = {
            "source_name": self.source_name,
            "base_url": self.base_url or self.entry_url,
            "entry_url": self.entry_url,
            "raw_subdir": self.raw_subdir,
            "parser_version": self.parser_version,
            "user_agent": USER_AGENT,
            "respect_robots": self.respect_robots,
            "delay_seconds": self.delay_seconds,
            "updated_at": datetime.utcnow().isoformat(),
        }
        (self.metadata_dir / "source_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if not self.respect_robots or parsed.scheme not in {"http", "https"}:
            return True
        key = f"{parsed.scheme}://{parsed.netloc}"
        if key not in self._robots_cache:
            self._robots_cache[key] = self._load_robots(key)
        robots = self._robots_cache[key]
        if robots is None:
            return True
        return robots.can_fetch(USER_AGENT, url)

    def absolutize(self, href: str, base_url: str | None = None) -> str:
        return urljoin(base_url or self.entry_url, href)

    def extension_for(self, url: str, content_type: str | None = None) -> str:
        lowered = (content_type or "").casefold()
        if "pdf" in lowered:
            return ".pdf"
        if "spreadsheet" in lowered or "excel" in lowered:
            return ".xlsx"
        if "csv" in lowered:
            return ".csv"
        suffix = Path(urlparse(url).path).suffix
        return suffix or ".html"

    def error_resource(self, url: str, stage: str, exc: Exception | str) -> ScrapedResource:
        return ScrapedResource(
            source_name=self.source_name,
            source_url=self.entry_url,
            resource_type="source_error",
            title=f"{stage}: {url}",
            url=url,
            accessed_at=datetime.utcnow(),
            metadata={"error": str(exc), "stage": stage},
            parser_version=self.parser_version,
        )

    def error_payload(self, url: str, stage: str, exc: Exception | str) -> dict[str, Any]:
        return {
            "record_type": "error",
            "url": url,
            "error": str(exc),
            "stage": stage,
            "source_name": self.source_name,
            "source_url": self.entry_url,
            "accessed_at": datetime.utcnow().isoformat(),
            "raw_file_path": None,
            "parser_version": self.parser_version,
        }

    def log_fetch(self, url: str, status_code: int | None, raw_path: str | None, content_type: str | None) -> None:
        self._append_jsonl(
            self.metadata_dir / "fetches.jsonl",
            {
                "event": "fetch",
                "url": url,
                "status_code": status_code,
                "raw_file_path": raw_path,
                "content_type": content_type,
                "accessed_at": datetime.utcnow().isoformat(),
            },
        )

    def log_error(self, stage: str, url: str, exc: Exception | str) -> None:
        self.logger.warning("%s failed for %s: %s", stage, url, exc)
        self._append_jsonl(
            self.metadata_dir / "errors.jsonl",
            {
                "event": "error",
                "stage": stage,
                "url": url,
                "error": str(exc),
                "accessed_at": datetime.utcnow().isoformat(),
            },
        )

    def _delay(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        robots_url = urljoin(origin, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            self._delay()
            response = self.session.get(robots_url, timeout=min(self.timeout, 10))
            self.log_fetch(robots_url, response.status_code, None, response.headers.get("content-type"))
            if response.status_code >= 400:
                return None
            parser.parse(response.text.splitlines())
            return parser
        except requests.RequestException as exc:
            self.log_error("robots_fetch_failed", robots_url, exc)
            return None

    def _ensure_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=json_default) + "\n")


def safe_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
    return cleaned[:120] or "resource"


def json_default(value: object) -> str | float | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    return None

