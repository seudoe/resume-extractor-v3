"""Merge same-baseline segments into one line (PROMPT.md §5 Stage 7).
Tolerance is relative to font size, not a fixed 3 px."""

from ir import BBox, Line

BASELINE_TOL = 0.5  # fraction of the smaller line height
CELL_GAP = 1.0  # horizontal gap (x font size) that separates table-like cells
CELL_SEP = "	"  # joins cells inside Line.text; later stages split on it


def _cy(l: Line) -> float:
    return (l.bbox.y0 + l.bbox.y1) / 2


def _is_gap(prev, nxt) -> bool:
    return nxt.bbox.x0 - prev.bbox.x1 >= CELL_GAP * max(prev.size, nxt.size)


def cell_text(line: Line) -> str:
    """Line text with big horizontal gaps between spans made explicit as
    CELL_SEP, so "degree  institution  dates  CGPA" stays four cells instead
    of one run of text (tab stops are invisible in plain extracted text)."""
    spans = sorted(line.spans, key=lambda sp: sp.bbox.x0)
    if len(spans) < 2:
        return line.text
    text = spans[0].text
    for prev, sp in zip(spans, spans[1:]):
        text = text.rstrip() + CELL_SEP + sp.text.lstrip() if _is_gap(prev, sp) else text + sp.text
    return text.strip()


def cell_starts(line: Line) -> list[float]:
    """x0 of each cell in the line (first cell, then after each big gap)."""
    spans = sorted(line.spans, key=lambda sp: sp.bbox.x0)
    if not spans:
        return [line.bbox.x0]
    return [spans[0].bbox.x0] + [b.bbox.x0 for a, b in zip(spans, spans[1:]) if _is_gap(a, b)]


def merge_baseline(lines: list[Line]) -> list[Line]:
    """Within one region: group segments on the same visual row (e.g. an
    institution and its right-aligned dates), left-to-right, top-to-bottom."""
    rows: list[list[Line]] = []
    for line in sorted(lines, key=_cy):
        for row in rows:
            ref = row[0]
            h = min(ref.bbox.y1 - ref.bbox.y0, line.bbox.y1 - line.bbox.y0)
            if abs(_cy(line) - _cy(ref)) <= BASELINE_TOL * h:
                row.append(line)
                break
        else:
            rows.append([line])

    merged = []
    for row in rows:
        row.sort(key=lambda l: l.bbox.x0)
        text = cell_text(row[0])
        for prev, line in zip(row, row[1:]):
            gap = line.bbox.x0 - prev.bbox.x1
            size = max((sp.size for sp in prev.spans + line.spans), default=10.0)
            text += (CELL_SEP if gap >= CELL_GAP * size else " ") + cell_text(line).strip()
        merged.append(
            row[0].model_copy(
                update={
                    "text": text.strip(),
                    "spans": [sp for l in row for sp in l.spans],
                    "bbox": BBox(
                        x0=min(l.bbox.x0 for l in row), y0=min(l.bbox.y0 for l in row),
                        x1=max(l.bbox.x1 for l in row), y1=max(l.bbox.y1 for l in row),
                    ),
                }
            )
        )
    return merged
