"""PDF -> Document IR (PROMPT.md §5 Stage 5).

Keeps layout signal (size/bold/italic/font/color/bbox) per span — the thing
the old extractor threw away before making any structural decision
(h.md's root-cause finding). No reading-order sorting here: that's Stage 7.
Lines are emitted in PyMuPDF's own block/line order, which is already
correct for simple single-column resumes and wrong for multi-column ones —
Stage 7's job, not this one.
"""

import unicodedata

import ftfy
import pymupdf

from ir import BBox, Document, DocumentMeta, Drawing, Line, Link, Page, Span

BOLD_FLAG = 1 << 4  # PyMuPDF span flags: bit 4 = bold (PROMPT.md §2)
ITALIC_FLAG = 1 << 1  # bit 1 = italic
BOLD_FONT_HINTS = ("bold", "black", "semibold", "heavy")

# Private Use Area glyphs (icon fonts: FontAwesome etc.) and the Unicode
# replacement character. Stripped from text but recorded as `icon_before` on
# whatever span follows, since "icon before a number" is a strong signal
# for phone/email/location lines (PROMPT.md §5).
_PUA_RANGE = (0xE000, 0xF8FF)
_REPLACEMENT_CHAR = "�"


def _is_icon_char(ch: str) -> bool:
    return ch == _REPLACEMENT_CHAR or _PUA_RANGE[0] <= ord(ch) <= _PUA_RANGE[1]


def _clean_span_text(raw: str) -> tuple[str, bool]:
    """Returns (cleaned_text, had_leading_icon)."""
    text = unicodedata.normalize("NFKC", raw)
    text = ftfy.fix_text(text)
    had_icon = False
    while text and _is_icon_char(text[0]):
        had_icon = True
        text = text[1:]
    text = "".join(c for c in text if not _is_icon_char(c))
    return text, had_icon


def _font_implies_bold(font_name: str) -> bool:
    lower = font_name.lower()
    return any(hint in lower for hint in BOLD_FONT_HINTS)


def _bbox(rect) -> BBox:
    return BBox(x0=rect[0], y0=rect[1], x1=rect[2], y1=rect[3])


def ingest_pdf(data: bytes, filename: str = "") -> Document:
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        pages = []
        line_counter = 0
        for page_index in range(len(doc)):
            page = doc[page_index]
            raw = page.get_text("dict")

            lines: list[Line] = []
            for block in raw["blocks"]:
                if block.get("type") != 0:  # 0 = text, 1 = image
                    continue
                for raw_line in block["lines"]:
                    spans: list[Span] = []
                    pending_icon = False
                    for raw_span in raw_line["spans"]:
                        text, had_icon = _clean_span_text(raw_span["text"])
                        if not text:
                            pending_icon = pending_icon or had_icon
                            continue
                        flags = raw_span["flags"]
                        spans.append(
                            Span(
                                text=text,
                                bbox=_bbox(raw_span["bbox"]),
                                size=raw_span["size"],
                                bold=bool(flags & BOLD_FLAG) or _font_implies_bold(raw_span["font"]),
                                italic=bool(flags & ITALIC_FLAG),
                                font=raw_span["font"],
                                color=raw_span.get("color"),
                                icon_before=pending_icon or had_icon,
                            )
                        )
                        pending_icon = False
                    line_text = "".join(s.text for s in spans).strip()
                    if not line_text:
                        continue
                    lines.append(
                        Line(
                            id=f"L{line_counter}",
                            page=page_index,
                            bbox=_bbox(raw_line["bbox"]),
                            spans=spans,
                            text=line_text,
                            source="pdf",
                        )
                    )
                    line_counter += 1

            links = [Link(bbox=_bbox(tuple(link["from"])), uri=link["uri"]) for link in page.get_links() if link.get("uri")]
            drawings = [
                Drawing(bbox=_bbox(tuple(d["rect"])), kind=d.get("type", ""))
                for d in page.get_drawings()
                if d.get("rect") is not None
            ]

            pages.append(
                Page(
                    number=page_index,
                    width=page.rect.width,
                    height=page.rect.height,
                    lines=lines,
                    links=links,
                    drawings=drawings,
                )
            )

        return Document(pages=pages, meta=DocumentMeta(filename=filename, page_count=len(pages), source="pdf"))
    finally:
        doc.close()
