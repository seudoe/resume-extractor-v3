"""Which lines count as "the header" (PROMPT.md §5 Stage 8): page-1 lines from
the top until the first section heading, any block under a CONTACT-style
heading (sidebars read after the main column), and any page-1 line that
carries contact data."""

import re

from ir import Document, Line

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
DATE_RANGE_RE = re.compile(r"(?:19|20)\d{2}\s*[-–—/]\s*(?:(?:19|20)?\d{2}|present)", re.I)

# Section-heading words, only used to find where the header ends. The full
# synonym table is Stage 9's job.
_HEADINGS = {
    "education", "experience", "work experience", "professional experience", "work history", "skills",
    "technical skills", "summary", "professional summary", "objective", "career objective", "projects",
    "academic projects", "profile", "about me", "about", "certifications", "achievements", "awards",
    "employment history", "career focus", "executive profile", "highlights", "qualifications", "languages",
    "interests", "publications", "other", "previous experience", "hard skills", "references",
}
_CONTACT_HEADINGS = {
    "contact", "contact me", "contact info", "contact information", "contact details", "personal details",
    "personal information", "get in touch", "personal", "con tact",
}


def _norm(line: Line) -> str:
    return re.sub(r"[^a-z ]", "", line.text.lower().replace("\t", " ")).strip()


def is_heading(line: Line) -> bool:
    return _norm(line) in _HEADINGS


def contact_text(line: Line) -> str:
    return line.text.replace("\t", " | ")


def has_contact_data(line: Line) -> bool:
    t = DATE_RANGE_RE.sub(" ", contact_text(line))  # "2017 - 2021" is not a phone number
    digits_run = re.search(r"\+?\d[\d\s().\-]{8,}\d", t)
    return bool(
        EMAIL_RE.search(t)
        or (digits_run and sum(c.isdigit() for c in digits_run.group(0)) >= 10)
        or re.search(r"(?i)linkedin|github|https?://|www\.", t)
    )


def header_lines(doc: Document) -> list[Line]:
    """Ordered page-1 header lines (see module docstring)."""
    if not doc.pages:
        return []
    out = []
    mode = "top"  # top | contact | body
    for line in doc.pages[0].lines:
        norm = _norm(line)
        if norm in _CONTACT_HEADINGS:
            mode = "contact"
            continue
        if norm in _HEADINGS:
            mode = "body"
        if mode != "body" or has_contact_data(line):
            out.append(line)
    return out
