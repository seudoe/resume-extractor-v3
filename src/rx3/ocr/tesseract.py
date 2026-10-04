"""Tesseract -> IR lines (PROMPT.md §5 Stage 6). Same interface as rapid.py."""

import os
import shutil
from collections import defaultdict

import pymupdf
import pytesseract
from PIL import Image

from ir import BBox, Line, Page, Span

_DEFAULT_WINDOWS_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def available() -> bool:
    return bool(os.environ.get("TESSERACT_CMD") or shutil.which("tesseract") or os.path.exists(_DEFAULT_WINDOWS_PATH))


def _configure() -> None:
    cmd = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract") or _DEFAULT_WINDOWS_PATH
    pytesseract.pytesseract.tesseract_cmd = cmd
    os.environ.setdefault("OMP_THREAD_LIMIT", os.environ.get("RX3_OCR_THREADS", "2"))  # HF free tier: 2 vCPU


def ocr_page(pdf_page: "pymupdf.Page", page_index: int, first_line_id: int, dpi: int = 300, psm: int = 3) -> Page:
    _configure()
    pix = pdf_page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    data = pytesseract.image_to_data(img, lang="eng", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)

    groups: dict[tuple, list[tuple[str, float, float, float, float]]] = defaultdict(list)
    for i, word in enumerate(data["text"]):
        if word.strip() and float(data["conf"][i]) >= 0:
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            groups[key].append((word.strip(), x, y, x + w, y + h))

    scale = 72.0 / dpi
    lines = []
    for words in groups.values():
        words.sort(key=lambda t: t[1])
        spans = []
        # One size per line (tallest word ~ ascender..descender): a word of
        # only x-height letters would otherwise look tiny and make ordinary
        # word gaps look like table-cell gaps.
        size = max(y1 - y0 for _, _, y0, _, y1 in words) * scale * 0.9
        for n, (w, x0, y0, x1, y1) in enumerate(words):
            bb = BBox(x0=x0 * scale, y0=y0 * scale, x1=x1 * scale, y1=y1 * scale)
            # per-word spans keep horizontal gaps visible to the layout's cell logic
            spans.append(Span(text=w + (" " if n < len(words) - 1 else ""), bbox=bb, size=size))
        bbox = BBox(
            x0=min(s.bbox.x0 for s in spans), y0=min(s.bbox.y0 for s in spans),
            x1=max(s.bbox.x1 for s in spans), y1=max(s.bbox.y1 for s in spans),
        )
        lines.append((bbox.y0, bbox.x0, bbox, spans))
    lines.sort(key=lambda t: (t[0], t[1]))
    out = [
        Line(id=f"L{first_line_id + i}", page=page_index, bbox=bb, spans=sp, text="".join(s.text for s in sp), source="ocr")
        for i, (_, _, bb, sp) in enumerate(lines)
    ]
    return Page(number=page_index, width=pdf_page.rect.width, height=pdf_page.rect.height, lines=out)
