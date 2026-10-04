"""Recursive XY-cut on line bboxes (PROMPT.md §5 Stage 7): split a page into
reading-order regions — full-width header/footer bands, columns, sidebars of
any width on either side. Replaces v2's "middle-third x0 histogram".
"""

import re

from ir import Line

MIN_GUTTER = 10.0  # pt of empty vertical space that counts as a gutter
MIN_SIDE_WIDTH = 40.0  # a column narrower than this isn't a column
ALIGNED_CELLS = 0.75  # see _is_aligned_cells


def _cy(l: Line) -> float:
    return (l.bbox.y0 + l.bbox.y1) / 2


def _h(l: Line) -> float:
    return max(l.bbox.y1 - l.bbox.y0, 1e-6)


def _gaps(intervals: list[tuple[float, float]], min_gap: float) -> list[tuple[float, float]]:
    """Empty (start, end) gaps >= min_gap between the merged intervals."""
    merged: list[list[float]] = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1) if merged[i + 1][0] - merged[i][1] >= min_gap]


_DATEISH = re.compile(
    r"(?i)^[\s\W]*((jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?|(19|20)\d{2}|present|current|now|till|to"
    r"|q[1-4]|\d{1,2}[/-]\d{2,4}|[-–—/.,'’\s])+$"
)


def _spans_gap(l: Line, g0: float, g1: float) -> bool:
    return l.bbox.x0 < g0 and l.bbox.x1 > g1


def _is_aligned_cells(left: list[Line], right: list[Line]) -> bool:
    """Right-aligned dates / table cells share baselines with the text beside
    them, so they're one row, not a column. In a true column layout the two
    sides' baselines are independent, so few lines on the smaller side have a
    partner on the other."""
    small, big = (left, right) if len(left) <= len(right) else (right, left)
    if sum(1 for s in small if _DATEISH.match(s.text.strip())) / len(small) >= 0.7:
        return True  # a column of dates beside entries: same rows, not a column
    partnered = sum(1 for s in small if any(abs(_cy(s) - _cy(b)) <= 0.2 * max(_h(s), _h(b)) for b in big))
    return partnered / len(small) >= ALIGNED_CELLS


def _vertical_cut(lines: list[Line]):
    """Best valid gutter as (gutter_start, gutter_end, left, right), or None."""
    best = None
    for g0, g1 in _gaps([(l.bbox.x0, l.bbox.x1) for l in lines], MIN_GUTTER):
        left = [l for l in lines if l.bbox.x1 <= g0 + 1e-6]
        right = [l for l in lines if l.bbox.x0 >= g1 - 1e-6]
        if not left or not right or len(left) + len(right) != len(lines):
            continue
        if min(max(l.bbox.x1 for l in left) - min(l.bbox.x0 for l in left),
               max(l.bbox.x1 for l in right) - min(l.bbox.x0 for l in right)) < MIN_SIDE_WIDTH:
            continue
        if _is_aligned_cells(left, right):
            continue
        if best is None or g1 - g0 > best[1] - best[0]:
            best = (g0, g1, left, right)
    return best


def _top(lines: list[Line]) -> float:
    return min(l.bbox.y0 for l in lines)


def _slabs(lines: list[Line], min_hgap: float) -> list[list[Line]]:
    """Partition at every full-width horizontal gap, top to bottom."""
    cuts = [(a + b) / 2 for a, b in _gaps([(l.bbox.y0, l.bbox.y1) for l in lines], min_hgap)]
    slabs = [[] for _ in range(len(cuts) + 1)]
    for l in lines:
        slabs[sum(1 for y in cuts if _cy(l) >= y)].append(l)
    return [s for s in slabs if s]


def split_regions(lines: list[Line], min_hgap: float) -> list[list[Line]]:
    """Ordered regions (header/footer bands, columns, sidebars). Each region
    is a list of lines in no particular order — `reading_order` sorts within
    regions.

    Full-width horizontal gaps cut first (peels headers/footers, separates
    sections whose column structure differs). Adjacent slabs that share the
    same gutter are re-joined and cut vertically *once*, so a two-column body
    reads column-by-column instead of slab-by-slab.
    """
    if len(lines) <= 1:
        return [lines] if lines else []

    slabs = _slabs(lines, min_hgap)
    if len(slabs) > 1:
        out: list[list[Line]] = []
        group: list[Line] = []
        plain: list[Line] = []  # consecutive gutter-less slabs -> one region
        gutter: tuple[float, float] | None = None  # shared gutter of the open group

        def emit_plain():
            nonlocal plain
            if plain:
                out.append(plain)
            plain = []

        def flush():
            nonlocal group, gutter
            if group:
                out.extend(_split_no_slab(group, min_hgap))
            group, gutter = [], None

        cuts = [_vertical_cut(sl) for sl in slabs]
        for idx, slab in enumerate(slabs):
            cut = cuts[idx]
            if gutter is not None:
                if cut:
                    lo, hi = max(gutter[0], cut[0]), min(gutter[1], cut[1])
                    if hi - lo >= MIN_GUTTER:  # same gutter as the open group
                        group, gutter = group + slab, (lo, hi)
                        continue
                elif len({(l.bbox.x0 + l.bbox.x1) / 2 < (gutter[0] + gutter[1]) / 2 for l in slab}) == 1:
                    group = group + slab  # one-sided slab: sits inside one column of the group
                    continue
                flush()
            if cut:
                emit_plain()
                group, gutter = list(slab), (cut[0], cut[1])
            else:
                # A row of column headings (one cell per column) fails the
                # aligned-cells test on its own, but belongs to the column
                # group right below it: open the group if that group's gutter
                # isn't crossed by this slab's lines.
                nxt = cuts[idx + 1] if idx + 1 < len(slabs) else None
                if nxt and not any(_spans_gap(l, nxt[0], nxt[1]) for l in slab) and len(slab) > 1:
                    emit_plain()
                    group, gutter = list(slab), (nxt[0], nxt[1])
                else:
                    plain.extend(slab)
        flush()
        emit_plain()
        return out
    return _split_no_slab(lines, min_hgap)


def _split_no_slab(lines: list[Line], min_hgap: float) -> list[list[Line]]:
    cut = _vertical_cut(lines)
    if not cut:
        return [lines] if lines else []
    _, _, left, right = cut
    # Columns normally read left-to-right. If one side starts far below the
    # other (e.g. a banner name sitting over only the main column), the
    # higher side reads first.
    first, second = (left, right)
    if _top(left) - _top(right) > 2 * min_hgap:
        first, second = right, left
    return split_regions(first, min_hgap) + split_regions(second, min_hgap)
