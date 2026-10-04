"""RapidOCR (PP-OCR on ONNX Runtime) -> IR lines (PROMPT.md §5 Stage 6)."""

import os

import numpy as np
import pymupdf

from ir import BBox, Line, Page, Span

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        # Default 2 threads = the HF free-tier budget (2 vCPU); override locally.
        threads = int(os.environ.get("RX3_OCR_THREADS", "2"))
        _engine = RapidOCR(intra_op_num_threads=threads, inter_op_num_threads=1)
    return _engine


def ocr_page(pdf_page: "pymupdf.Page", page_index: int, first_line_id: int, dpi: int = 150) -> Page:
    """Render one PDF page, OCR it, return an IR Page with source="ocr" lines.

    Font size is estimated from box height; bold is unknown from OCR, so it's
    False (layout code must not rely on bold for OCR pages).
    """
    pix = pdf_page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    result, _ = _get_engine()(img)

    scale = 72.0 / dpi  # pixels -> PDF points
    lines = []
    for box, text, _score in result or []:
        text = text.strip()
        if not text:
            continue
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        bbox = BBox(x0=min(xs) * scale, y0=min(ys) * scale, x1=max(xs) * scale, y1=max(ys) * scale)
        size = (bbox.y1 - bbox.y0) * 0.8  # glyph height ≈ 80% of the detected box
        lines.append(
            Line(
                id=f"L{first_line_id + len(lines)}",
                page=page_index,
                bbox=bbox,
                spans=[Span(text=text, bbox=bbox, size=size)],
                text=text,
                source="ocr",
            )
        )
    return Page(number=page_index, width=pdf_page.rect.width, height=pdf_page.rect.height, lines=lines)
