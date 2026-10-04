"""Merge same-baseline segments into one line (PROMPT.md §5 Stage 7).
Tolerance is relative to font size, not a fixed 3 px."""

from ir import BBox, Line

BASELINE_TOL = 0.5  # fraction of the smaller line height


def _cy(l: Line) -> float:
    return (l.bbox.y0 + l.bbox.y1) / 2


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
        if len(row) == 1:
            merged.append(row[0])
            continue
        merged.append(
            row[0].model_copy(
                update={
                    "text": " ".join(l.text.strip() for l in row),
                    "spans": [s for l in row for s in l.spans],
                    "bbox": BBox(
                        x0=min(l.bbox.x0 for l in row), y0=min(l.bbox.y0 for l in row),
                        x1=max(l.bbox.x1 for l in row), y1=max(l.bbox.y1 for l in row),
                    ),
                }
            )
        )
    return merged
