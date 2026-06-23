from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import pandas as pd

from app.normalizers.text import clean_text, normalize_name


DATASET_EXTENSIONS = {".csv", ".xls", ".xlsx"}
DOWNLOAD_EXTENSIONS = {".csv", ".xls", ".xlsx", ".zip", ".json"}


def discover_links(html: str, base_url: str, absolutize) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[dict[str, str]] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if not href:
            continue
        url = absolutize(href, base_url)
        title = clean_text(anchor.get_text(" ")) or url
        extension = url_extension(url)
        links.append({"url": url, "title": title, "extension": extension})
    return links


def relevant_dataset_links(links: list[dict[str, str]], keywords: set[str]) -> list[dict[str, str]]:
    selected = []
    for link in links:
        haystack = normalize_name(f"{link['url']} {link['title']}")
        if link["extension"] in DOWNLOAD_EXTENSIONS and any(keyword in haystack for keyword in keywords):
            selected.append(link)
    return selected


def read_tabular_file(path: Path) -> list[tuple[str, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return [("csv", read_csv_flexible(path))]
    if suffix in {".xls", ".xlsx"}:
        sheets = pd.read_excel(path, sheet_name=None)
        return [(str(name), frame) for name, frame in sheets.items()]
    return []


def read_csv_flexible(path: Path) -> pd.DataFrame:
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except pd.errors.ParserError:
            return pd.read_csv(path, encoding=encoding, sep=";")
    return pd.read_csv(path, encoding="latin-1", sep=";")


def html_tables_to_dataframes(html: str) -> list[pd.DataFrame]:
    soup = BeautifulSoup(html, "html.parser")
    frames: list[pd.DataFrame] = []
    for table in soup.select("table"):
        headers = [clean_text(cell.get_text(" ")) for cell in table.select("thead th")]
        rows = []
        for tr in table.select("tr"):
            cells = [clean_text(cell.get_text(" ")) for cell in tr.select("td, th")]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        if not headers:
            headers = rows.pop(0)
        width = max(len(headers), *(len(row) for row in rows))
        headers = _pad(headers, width)
        padded_rows = [_pad(row, width) for row in rows]
        frames.append(pd.DataFrame(padded_rows, columns=headers))
    return frames


def rows_to_jsonable(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    jsonable = []
    for record in records:
        jsonable.append({key: (float(value) if hasattr(value, "as_tuple") else value) for key, value in record.items()})
    return jsonable


def url_extension(url: str) -> str:
    path = urlparse(url).path
    return "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""


def _pad(row: list[str], width: int) -> list[str]:
    return row + [""] * (width - len(row))

