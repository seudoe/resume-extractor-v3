"""Name extraction (PROMPT.md §5 Stage 8): largest/boldest short alphabetic
line in the top of page 1 that isn't a heading or job title, boosted when it
matches the filename or the email local part. Layout beats NLP here — h.md's
largest-font rule fixed 5 of 7 v2 name failures with no model."""

import re
import unicodedata
from pathlib import Path

from ir import Document, Line, Provenance

TOP_FRACTION = 0.35

_STOP = {
    # resume furniture
    "resume", "résumé", "curriculum", "vitae", "cv", "profile", "contact", "summary", "objective", "education",
    "experience", "skills", "projects", "about", "personal", "details", "portfolio", "career", "information",
    "professional", "technical", "work", "history", "address", "email", "phone", "mobile", "linkedin", "github",
    # job titles / roles
    "engineer", "developer", "manager", "analyst", "designer", "consultant", "intern", "student", "director",
    "officer", "specialist", "scientist", "architect", "administrator", "coordinator", "executive", "assistant",
    "associate", "accountant", "teacher", "technician", "representative", "programmer", "fresher", "graduate",
    "lead", "head", "president", "founder", "freelancer", "researcher", "software", "web", "full-stack",
    "fullstack", "frontend", "backend", "data", "senior", "junior", "chief",
}
_NAME_CHARS = re.compile(r"^[^\W\d_]+(?:[.'’\-][^\W\d_]+)*\.?$")  # a letters-only token, internal . ' -
_SMALLCAPS = re.compile(r"\b([A-Z])\s([A-Z]{2,}|[a-z]{2,})\b")


def _fix_smallcaps(text: str) -> str:
    """'M OHD ASIF' / 'M ohd' -> 'MOHD ASIF' / 'Mohd': small-caps fonts render the
    first letter larger, which extraction turns into a stray space."""
    return _SMALLCAPS.sub(lambda m: m.group(1) + m.group(2), text)


def _clean_cell(cell: str) -> str:
    cell = "".join(c for c in unicodedata.normalize("NFKC", cell) if c.isprintable())
    return re.sub(r"\s+", " ", _fix_smallcaps(cell)).strip(" |•·-–—,:")


def _tokens_ok(cell: str) -> list[str] | None:
    tokens = cell.split()
    if not 1 <= len(tokens) <= 5:
        return None
    if any(not _NAME_CHARS.match(t) for t in tokens):
        return None
    if any(re.sub(r"[^\w\-]", "", t).lower() in _STOP for t in tokens):
        return None
    return tokens


def _name_parts(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z]+", text.lower()) if len(t) >= 3}


def extract_name(doc: Document, filename: str = "", email: str = "") -> tuple[str, Provenance | None]:
    if not doc.pages:
        return "", None
    page = doc.pages[0]
    stem = Path(filename).stem.lower().replace("_", " ")
    local = email.split("@")[0].lower() if email else ""

    best: tuple[float, str, Line] | None = None
    for line in page.lines:
        if (line.bbox.y0 + line.bbox.y1) / 2 > TOP_FRACTION * page.height:
            continue
        feats = line.features
        for cell in line.text.split("\t"):
            cell = _clean_cell(cell)
            tokens = _tokens_ok(cell)
            if not tokens:
                continue
            score = 3.0 * min(feats.rel_size if feats else 1.0, 3.0)
            score += 1.0 if (feats and feats.bold) else 0.0
            score += {1: 0.5, 2: 2.0, 3: 2.0, 4: 1.0, 5: 0.0}[len(tokens)]
            score -= 2.0 * (line.bbox.y0 / page.height) / TOP_FRACTION  # earlier is better
            low = [t.lower().strip(".") for t in tokens]
            if stem:
                score += 3.0 * sum(1 for t in low if len(t) >= 3 and t in stem.replace(" ", "")) / len(low)
            if local:
                score += 2.0 * sum(1 for t in low if len(t) >= 3 and t in local) / len(low)
            if best is None or score > best[0]:
                best = (score, cell, line)
    if not best:
        return "", None
    score, name, line = best
    ids = [line.id]
    # A name wrapped onto a second line at the same (large) size.
    lines = page.lines
    i = lines.index(line)
    if i + 1 < len(lines) and line.features and lines[i + 1].features:
        nxt = lines[i + 1]
        same_size = abs(nxt.features.rel_size - line.features.rel_size) <= 0.08 * line.features.rel_size
        extra = _tokens_ok(_clean_cell(nxt.text))
        if same_size and extra and line.features.rel_size >= 1.5 and len(name.split()) + len(extra) <= 5:
            name, ids = name + " " + " ".join(extra), ids + [nxt.id]
    return name, Provenance(line_ids=ids, component="header.name", confidence=min(1.0, score / 12))
