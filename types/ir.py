"""Internal Document IR shared by every pipeline stage (Stage 5+).

Pointer principle (PROMPT.md §3): later stages refer to text by `Line.id`,
never by retyping it, so the final output can always be traced back to a
source line.
"""

from typing import Literal

from pydantic import BaseModel

SourceKind = Literal["pdf", "ocr", "docx"]


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Span(BaseModel):
    text: str
    bbox: BBox
    size: float
    bold: bool = False
    italic: bool = False
    font: str = ""
    color: int | None = None
    # True when a PUA/icon glyph (U+E000-F8FF) was stripped immediately
    # before this span on the same line — PROMPT.md §5 Stage 5: an icon
    # before a number/handle usually means a phone/email/location line.
    # Added here (not in the original Stage 2 IR) once Stage 5 needed it.
    icon_before: bool = False


class Line(BaseModel):
    id: str  # stable id in reading order, e.g. "L0", "L1", ...
    page: int
    bbox: BBox
    spans: list[Span] = []
    text: str
    source: SourceKind = "pdf"


class Block(BaseModel):
    lines: list[Line] = []
    bbox: BBox


class Link(BaseModel):
    bbox: BBox
    uri: str


class Drawing(BaseModel):
    bbox: BBox
    kind: str = ""  # e.g. "line", "rect" — used to detect rules under headings


class Page(BaseModel):
    number: int
    width: float
    height: float
    lines: list[Line] = []
    links: list[Link] = []
    drawings: list[Drawing] = []


class DocumentMeta(BaseModel):
    filename: str = ""
    page_count: int = 0
    source: SourceKind = "pdf"


class Document(BaseModel):
    pages: list[Page] = []
    meta: DocumentMeta = DocumentMeta()


class Provenance(BaseModel):
    line_ids: list[str] = []
    char_span: tuple[int, int] | None = None
    component: str = ""
    confidence: float = 1.0
