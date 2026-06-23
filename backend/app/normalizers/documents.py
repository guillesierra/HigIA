from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from app.normalizers.text import clean_text, extract_year, infer_document_type, infer_geography, infer_therapeutic_group


def extract_pdf_text(path: Path, max_pages: int | None = 5) -> str:
    """Extract bounded PDF text for cataloging and manual review."""
    chunks: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            pages = pdf.pages[:max_pages] if max_pages else pdf.pages
            for page in pages:
                chunks.append(page.extract_text() or "")
    except Exception:
        reader = PdfReader(str(path))
        pages = reader.pages[:max_pages] if max_pages else reader.pages
        for page in pages:
            chunks.append(page.extract_text() or "")
    return clean_text("\n".join(chunks))


def infer_document_metadata(path: Path, text: str) -> dict[str, object]:
    """Infer safe metadata. Do not infer structured metrics from PDF prose."""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), path.stem)
    year = extract_year(text) or extract_year(path.name)
    context = f"{path.name} {text[:2000]}"
    return {
        "title": first_line[:300] or path.stem,
        "year": year,
        "document_type": infer_document_type(context, default="pdf"),
        "geography": infer_geography(context),
        "therapeutic_group": infer_therapeutic_group(context),
        "summary": text[:1000] if text else None,
        "pending_work": "Manual review required before structured data extraction.",
    }
