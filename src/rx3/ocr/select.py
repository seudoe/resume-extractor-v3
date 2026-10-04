"""Replace text-poor pages of an ingested PDF with OCR output."""

import pymupdf

from ir import Document

from rx3.ingest.quality import page_quality
from rx3.ocr.rapid import ocr_page


def apply_ocr_fallback(doc: Document, pdf_bytes: bytes, dpi: int = 150) -> Document:
    """OCR every page `page_quality` flags; keep line ids contiguous across
    pages. Returns `doc` unchanged if no page needs OCR."""
    flagged = [p.number for p in doc.pages if page_quality(p)["needs_ocr"]]
    if not flagged:
        return doc

    pdf = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        for idx in flagged:
            doc.pages[idx] = ocr_page(pdf[idx], idx, first_line_id=0, dpi=dpi)
    finally:
        pdf.close()

    n = 0  # renumber so ids stay unique and in document order
    for page in doc.pages:
        for line in page.lines:
            line.id = f"L{n}"
            n += 1
    return doc
