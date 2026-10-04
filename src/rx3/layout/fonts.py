"""Body-font statistics and per-line layout features (PROMPT.md §5 Stage 7)."""

from collections import Counter
from statistics import median

from ir import Document, Line, LineFeatures, Page

from rx3.layout.bullets import is_bullet


def _dominant(line: Line, attr: str):
    weights: Counter = Counter()
    for s in line.spans:
        weights[getattr(s, attr)] += len(s.text)
    return weights.most_common(1)[0][0] if weights else None


def body_stats(doc: Document) -> tuple[float, int | None, float]:
    """(body font size, body colour, body line height). Body = char-weighted
    mode of sizes (rounded to 0.5pt) / colours across the whole document."""
    sizes: Counter = Counter()
    colors: Counter = Counter()
    heights = []
    for page in doc.pages:
        for line in page.lines:
            for s in line.spans:
                sizes[round(s.size * 2) / 2] += len(s.text)
                colors[s.color] += len(s.text)
            heights.append(line.bbox.y1 - line.bbox.y0)
    body_size = sizes.most_common(1)[0][0] if sizes else 10.0
    body_color = colors.most_common(1)[0][0] if colors else None
    body_height = median(heights) if heights else body_size * 1.2
    return body_size, body_color, body_height


def _rule_below(line: Line, page: Page) -> bool:
    width = line.bbox.x1 - line.bbox.x0
    h = line.bbox.y1 - line.bbox.y0
    for d in page.drawings:
        if d.bbox.y1 - d.bbox.y0 > 2.0:  # not a thin horizontal rule
            continue
        if not (line.bbox.y1 - 1.0 <= d.bbox.y0 <= line.bbox.y1 + 0.8 * h):
            continue
        overlap = min(line.bbox.x1, d.bbox.x1) - max(line.bbox.x0, d.bbox.x0)
        if overlap >= 0.5 * width:
            return True
    return False


def annotate_features(doc: Document, region_of: dict[str, int]) -> None:
    """Fill `Line.features` for every line. `region_of` maps line id -> region
    index (set by the reading-order pass)."""
    body_size, body_color, body_height = body_stats(doc)
    for page in doc.pages:
        region_left: dict[int, float] = {}
        for line in page.lines:
            r = region_of.get(line.id, 0)
            region_left[r] = min(region_left.get(r, line.bbox.x0), line.bbox.x0)
        prev_by_region: dict[int, Line] = {}
        for line in page.lines:
            r = region_of.get(line.id, 0)
            size = _dominant(line, "size") or body_size
            alpha = [c for c in line.text if c.isalpha()]
            prev = prev_by_region.get(r)
            line.features = LineFeatures(
                rel_size=size / body_size,
                bold=bool(_dominant(line, "bold")),
                all_caps=len(alpha) >= 2 and all(c.isupper() for c in alpha),
                color_differs=body_color is not None and _dominant(line, "color") not in (None, body_color),
                rule_below=_rule_below(line, page),
                indent=line.bbox.x0 - region_left[r],
                gap_above=max(0.0, (line.bbox.y0 - prev.bbox.y1) / body_height) if prev else 0.0,
                is_bullet=is_bullet(line.text),
                region=r,
            )
            prev_by_region[r] = line
