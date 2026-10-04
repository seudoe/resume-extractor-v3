"""Section-heading detection (PROMPT.md §5 Stage 9).

Two passes over the laid-out lines:
1. A short line whose text reads as a known heading (synonym table, fuzzy) and
   that looks like a heading (bold / caps / larger / coloured / rule below, or
   simply alone on a very short line) is a heading with a canonical section.
   "Skills: Python, Java" and "Languages<tab>English, Hindi" are *inline*
   headings: the label starts a one-line section.
2. Headings the table doesn't know ("Curriculum", "Strengths") are found by
   style propagation: a short line with the same style signature as the
   resume's known headings, plus a strong heading cue (caps / rule / bigger /
   coloured), becomes an `other` heading — never silently glued onto the
   previous section (v2's bug).
"""

import re
from collections import Counter
from dataclasses import dataclass

from ir import Document, Line

from rx3.layout.bullets import is_bullet
from rx3.sections.synonyms import normalize as normalize_label
from rx3.sections.synonyms import AMBIGUOUS_ONE_WORD, MAX_HEADING_WORDS, keyword_section, match_heading

INLINE_MIN_SCORE = 97.0  # inline labels must be (near-)exact, they sit mid-content
STYLE_MAX_WORDS = 5


@dataclass
class Heading:
    line_id: str
    label: str  # heading text without any inline content
    section: str
    inline: bool = False
    source: str = "synonym"  # synonym | style
    score: float = 100.0
    styled: bool = False  # label is bold / caps / larger / coloured
    colon: bool = False  # written "Label:" (vs a plain tab-separated cell)
    rest: str = ""  # inline content after the label ("C, C++, Java" in "Languages: C, C++, Java")


_PROGRAMMING = {
    "python", "java", "c", "c++", "c#", "javascript", "typescript", "sql", "html", "css", "go", "golang", "rust",
    "kotlin", "swift", "php", "ruby", "r", "matlab", "bash", "scala", "dart", "html5", "css3", "js",
}


def looks_like_programming(rest: str) -> bool:
    """True if an inline "Languages: ..." row lists programming languages
    (Skills sub-row), not spoken languages (the Languages section)."""
    tokens = {t.strip(" .()").lower() for t in re.split(r"[,/|\t;]", rest)}
    tokens |= {w.lower().strip("(),.") for w in rest.split()}
    return len(tokens & _PROGRAMMING) >= 2


def _label_and_rest(text: str) -> tuple[str, str]:
    """Split "Label<tab>rest" / "Label: rest" at the first cell/colon."""
    if "\t" in text:
        label, _, rest = text.partition("\t")
    elif ":" in text:
        label, _, rest = text.partition(":")
    else:
        label, rest = text, ""
    return label.strip(" :•·-–—|"), rest.strip()


def _layout_ok(line: Line) -> bool:
    f = line.features
    return bool(f and (f.bold or f.all_caps or f.rel_size >= 1.08 or f.rule_below or f.color_differs))


def _label_styled(line: Line, label: str) -> bool:
    """Layout cue for the *label*, not the whole line: in "Languages<tab>English"
    rows the value text dominates the line's dominant-bold flag, so also look
    at the first span (the label)."""
    first_bold = bool(line.spans and line.spans[0].bold)
    return _layout_ok(line) or first_bold or (sum(c.isalpha() for c in label) >= 2 and label.isupper())


def _has_colon(text: str, label: str) -> bool:
    return text.lstrip().startswith(label) and text.lstrip()[len(label):].lstrip().startswith(":")


def _strong_cue(line: Line) -> bool:
    f = line.features
    return bool(f and (f.all_caps or f.rule_below or f.rel_size >= 1.15 or f.color_differs))


def _signature(line: Line) -> tuple:
    f = line.features
    return (f.bold, f.all_caps, round(f.rel_size * 5) / 5, f.color_differs, f.rule_below)


def _heading_styles(heading_lines: list[Line]) -> set[tuple] | None:
    """Style signatures that count as "this resume's heading style": the most
    common one plus any other seen at least twice (a sidebar's tag-style
    headings vs the main column's rule-underlined ones)."""
    if not heading_lines:
        return None
    counts = Counter(_signature(l) for l in heading_lines)
    top = counts.most_common(1)[0][0]
    styles = {sig for sig, n in counts.items() if n >= 2} | {top}
    plain = (False, False, 1.0, False, False)  # no cue at all: not a heading *style*
    return (styles - {plain}) or styles


def detect_headings(doc: Document) -> dict[str, Heading]:
    """line id -> Heading for every heading/inline-heading in the document."""
    lines = [l for p in doc.pages for l in p.lines if l.features is not None]
    found: dict[str, Heading] = {}

    cands = []  # (line, label, rest, section, score)
    for line in lines:
        if is_bullet(line.text):
            continue
        label, rest = _label_and_rest(line.text)
        hit = match_heading(label)
        if hit and len(label.split()) <= MAX_HEADING_WORDS:
            cands.append((line, label, rest, hit[0], hit[1]))

    # Some resumes (every LiveCareer PDF) have no heading styling at all. If
    # none of the exact-match headings carries a cue, the document is "plain":
    # an exact synonym alone on a line is then heading enough, at any length
    # ("Education and Training"), and unknown title-case headings with a
    # section keyword are found below.
    exact_pure = [c for c in cands if not c[2] and c[4] >= 100.0]
    plain_doc = bool(exact_pure) and not any(_layout_ok(c[0]) for c in exact_pure)

    def pure_ok(line: Line, label: str) -> bool:
        if plain_doc and not _layout_ok(line):
            # No cue to lean on: "Leadership"/"Research" alone on a line is a
            # skill tag, and "Accomplishments:" is a sub-label inside a job.
            ambiguous = len(label.split()) == 1 and normalize_label(label) in AMBIGUOUS_ONE_WORD
            return not ambiguous and not line.text.rstrip().endswith(":")
        return _layout_ok(line) or len(label.split()) <= 2

    # The resume's own heading style, from its exact-match headings. A fuzzy
    # near-match in a different style is an entry subtitle ("Personal Project"
    # under a project title), not a heading.
    exact = [c for c in cands if not c[2] and c[4] >= 100.0 and pure_ok(c[0], c[1])]
    styles = _heading_styles([c[0] for c in exact])  # None if no exact headings at all

    for line, label, rest, section, score in cands:
        if rest:
            if score >= INLINE_MIN_SCORE:
                found[line.id] = Heading(
                    line.id, label, section, True, "synonym", score, _label_styled(line, label), _has_colon(line.text, label), rest
                )
        elif pure_ok(line, label) and (
            (score >= 100.0 and _layout_ok(line))
            or (score >= 100.0 and not plain_doc and line.text.rstrip().endswith(":"))  # "Languages:" label line
            or styles is None
            or _signature(line) in styles
        ):
            found[line.id] = Heading(line.id, label, section, False, "synonym", score, _label_styled(line, label))

    # Style propagation for headings the table doesn't know.
    pure = [h for h in found.values() if not h.inline]
    if pure:
        by_id = {l.id: l for l in lines}
        styles = _heading_styles([by_id[h.line_id] for h in pure])
        first_heading_idx = min(i for i, l in enumerate(lines) if l.id in found)
        for i, line in enumerate(lines):
            if i < first_heading_idx or line.id in found or is_bullet(line.text) or "\t" in line.text:
                continue
            text = line.text.strip()
            words = text.split()
            if not 1 <= len(words) <= STYLE_MAX_WORDS or re.search(r"\d|:", text):
                continue
            if sum(c.isalpha() for c in text) < 0.8 * len(text.replace(" ", "")):
                continue
            if _signature(line) in styles and _strong_cue(line):
                found[line.id] = Heading(line.id, text, keyword_section(text) or "other", False, "style", 0.0)

    if plain_doc:
        by_id = {l.id: l for l in lines}
        first_heading_idx = min((i for i, l in enumerate(lines) if l.id in found), default=len(lines))
        for i, line in enumerate(lines):
            if i < first_heading_idx or line.id in found or is_bullet(line.text) or "\t" in line.text:
                continue
            text = line.text.strip()
            words = text.split()
            if not 1 <= len(words) <= STYLE_MAX_WORDS or re.search(r"\d|[:.,;]", text):
                continue
            small = {"and", "of", "&", "the", "in", "for"}
            if not all(w[:1].isupper() or w.lower() in small for w in words):
                continue
            section = keyword_section(text, strict=True) if len(words) >= 2 else None
            if section:
                found[line.id] = Heading(line.id, text, section, False, "style", 0.0)
    return found
