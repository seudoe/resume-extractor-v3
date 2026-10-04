"""Replace text-poor pages of an ingested PDF with OCR output.

Engine choice is by benchmark (DECISIONS.md Stage 6): Tesseract ~2 s/page at
300 DPI vs RapidOCR ~24 s at 150 DPI on 2 threads, with lower WER. RapidOCR
is the fallback when no Tesseract binary exists (e.g. a bare dev machine).
"""

import os

import pymupdf

from ir import Document

from rx3.ingest.quality import page_quality
from rx3.ocr import rapid, tesseract


def get_engine(name: str | None = None):
    """Returns (ocr_page function, default DPI)."""
    name = name or os.environ.get("RX3_OCR_ENGINE") or ("tesseract" if tesseract.available() else "rapid")
    if name == "tesseract":
        return tesseract.ocr_page, 300
    if name == "rapid":
        return rapid.ocr_page, 150
    raise ValueError(f"unknown OCR engine {name!r}")


def apply_ocr_fallback(doc: Document, pdf_bytes: bytes, dpi: int | None = None, engine: str | None = None) -> Document:
    """OCR every page `page_quality` flags; keep line ids contiguous across
    pages. Returns `doc` unchanged if no page needs OCR."""
    flagged = [p.number for p in doc.pages if page_quality(p)["needs_ocr"]]
    if not flagged:
        return doc

    ocr_page, default_dpi = get_engine(engine)
    pdf = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        for idx in flagged:
            doc.pages[idx] = ocr_page(pdf[idx], idx, 0, dpi=dpi or default_dpi)
    finally:
        pdf.close()

    n = 0  # renumber so ids stay unique and in document order
    for page in doc.pages:
        for line in page.lines:
            line.id = f"L{n}"
            n += 1
    return doc
