"""Bullet detection, wrapped-line merging and dehyphenation (PROMPT.md §5
Stage 7). Wrapped continuation lines were a major source of v2 errors."""

import re

from ir import BBox, Line

from rx3.layout.lines import CELL_SEP, cell_starts
from rx3.sections.synonyms import match_heading

BULLET_GLYPHS = "•●○◦▪▫■□–—-*➢➤►✓✔·"
_BULLET_RE = re.compile(rf"^\s*[{re.escape(BULLET_GLYPHS)}]\s*\S")
_TERMINAL = ".:;!?"
_ENDS_WITH_DATE = re.compile(r"(?i)(\b(19|20)\d{2}|present|current)\s*$")


def is_bullet(text: str) -> bool:
    return bool(_BULLET_RE.match(text))


def _strip_bullet(text: str) -> str:
    return text.lstrip().lstrip(BULLET_GLYPHS).lstrip()


def _text_x0(line: Line) -> float:
    """x where a bullet's *text* starts (after the glyph) — the hanging indent
    continuation lines align to. The glyph is often in the same span as the
    text, so estimate by character proportion; falls back to the line's x0."""
    if not is_bullet(line.text):
        return line.bbox.x0
    if len(line.spans) > 1:
        return line.spans[1].bbox.x0
    text = line.text
    prefix = len(text) - len(_strip_bullet(text))
    width = line.bbox.x1 - line.bbox.x0
    return line.bbox.x0 + width * prefix / max(len(text), 1)


def _join(a: Line, b: Line) -> Line:
    ta, tb = a.text.rstrip(), b.text.lstrip()
    # ponytail: drops the hyphen whenever the next fragment starts lowercase;
    # a real compound broken at its hyphen ("full-\nstack") becomes "fullstack".
    if ta.endswith("-") and len(ta) > 1 and ta[-2].isalpha() and tb[:1].islower():
        text = ta[:-1] + tb
    else:
        text = f"{ta} {tb}"
    bbox = BBox(
        x0=min(a.bbox.x0, b.bbox.x0), y0=min(a.bbox.y0, b.bbox.y0),
        x1=max(a.bbox.x1, b.bbox.x1), y1=max(a.bbox.y1, b.bbox.y1),
    )
    return a.model_copy(update={"text": text, "bbox": bbox, "spans": a.spans + b.spans})


def _size(line: Line) -> float:
    return max((s.size for s in line.spans), default=0.0)


def _bold(line: Line) -> bool:
    return any(s.bold for s in line.spans)


def _is_continuation(prev: Line, cur: Line, right_edge: float, body_height: float) -> bool:
    if is_bullet(cur.text):
        return False
    if abs(_size(cur) - _size(prev)) > 0.06 * max(_size(prev), 1.0) or _bold(cur) != _bold(prev):
        return False
    if cur.bbox.y0 - prev.bbox.y1 > 0.8 * body_height:  # paragraph/section gap
        return False
    if cur.bbox.y0 < prev.bbox.y0:  # not below
        return False
    cur_text = cur.text.strip()
    if len(cur_text.split()) <= 5 and cur_text.isupper() and not prev.text.strip().isupper():
        return False  # a short ALL-CAPS line after mixed-case text is a heading
    heading = match_heading(cur_text)
    if heading and heading[1] >= 100.0:
        return False  # "Additional Information" right after a full-width skills line
    prev_start = _text_x0(prev)
    if CELL_SEP in prev.text:
        # A table-like row (degree | institution | dates, label | values) is a
        # row, never a wrapped line — except its last cell wrapping onto the
        # next line, which aligns to that cell's start.
        if CELL_SEP in cur.text:
            return False
        prev_start = cell_starts(prev)[-1]
    hanging = is_bullet(prev.text) and prev.bbox.x0 < cur.bbox.x0 <= prev.bbox.x0 + 30.0
    first_line_indent = not is_bullet(prev.text) and 0 < prev.bbox.x0 - cur.bbox.x0 <= 30.0
    if CELL_SEP in prev.text:
        aligned = abs(cur.bbox.x0 - prev_start) <= 4.0  # only the row's last cell can wrap
    else:
        aligned = abs(cur.bbox.x0 - prev_start) <= 4.0 or hanging or first_line_indent or (
            not is_bullet(prev.text) and abs(cur.bbox.x0 - prev.bbox.x0) <= 3.0
        )
    if not aligned:
        return False
    stripped = prev.text.rstrip()
    if stripped.endswith("-"):
        return True
    # A line that wrapped is a sentence fragment: several words. Single-token
    # lines (emails, URLs, handles stacked in a contact list) never wrap.
    if len(_strip_bullet(stripped).split()) < 3 or stripped[-1:] in _TERMINAL or _ENDS_WITH_DATE.search(stripped):
        return False  # short/complete items and "Title ... 2020 - Present" header rows
    # Wrapped lines run to the right margin; a lowercase start is the other tell.
    near_edge = prev.bbox.x1 >= right_edge - 0.12 * (right_edge - prev.bbox.x0 + 1e-9)
    return near_edge or cur.text.lstrip()[:1].islower()


def merge_wrapped(lines: list[Line], body_height: float) -> list[Line]:
    """Merge continuation lines into the line they wrap from. `lines` must be
    one region, already in reading order."""
    if not lines:
        return []
    right_edge = max(l.bbox.x1 for l in lines)
    out = [lines[0]]
    for cur in lines[1:]:
        if _is_continuation(out[-1], cur, right_edge, body_height):
            out[-1] = _join(out[-1], cur)
        else:
            out.append(cur)
    return out
