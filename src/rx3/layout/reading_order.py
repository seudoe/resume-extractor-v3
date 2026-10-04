"""Layout pipeline: regions -> baseline merge -> wrapped-line merge -> stable
ids L0..Ln -> features (PROMPT.md §5 Stage 7)."""

import re
from statistics import median

from ir import Document

from rx3.layout.bullets import merge_wrapped
from rx3.layout.columns import split_regions
from rx3.layout.fonts import annotate_features, body_stats
from rx3.layout.lines import merge_baseline


_RULE_ONLY = re.compile(r"[\s_=~*.─-╿-]{4,}")  # text drawn as a horizontal rule


def analyze_layout(doc: Document) -> Document:
    """Reorders each page's lines into reading order, merges wrapped lines
    and re-assigns ids L0..Ln across the document. Mutates and returns doc."""
    _, _, body_height = body_stats(doc)
    region_of: dict[str, int] = {}
    counter = 0
    ruled = []  # lines that had a text-drawn rule right under them

    for page in doc.pages:
        heights = [l.bbox.y1 - l.bbox.y0 for l in page.lines]
        min_hgap = 0.6 * (median(heights) if heights else body_height)
        ordered = []
        for r_idx, region in enumerate(split_regions(page.lines, min_hgap)):
            merged = []
            for line in merge_wrapped(merge_baseline(region), body_height):
                if _RULE_ONLY.fullmatch(line.text.strip()):
                    if merged:
                        ruled.append(merged[-1])
                    continue
                merged.append(line)
            for line in merged:
                line.id = f"L{counter}"
                region_of[line.id] = r_idx
                counter += 1
            ordered.extend(merged)
        page.lines = ordered

    annotate_features(doc, region_of)
    for line in ruled:
        line.features.rule_below = True
    return doc
