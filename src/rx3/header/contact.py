"""Email and phone extraction (PROMPT.md §5 Stage 8)."""

import re

import phonenumbers

from ir import Document, Provenance

from rx3.header.zone import EMAIL_RE, contact_text

_DATE_RANGE = re.compile(r"(?:19|20)\d{2}\s*[-\u2013\u2014/]\s*(?:(?:19|20)?\d{2}|present)", re.I)


def extract_email(doc: Document) -> tuple[str, Provenance | None]:
    """Visible text first, `mailto:` as fallback. Template-derived PDFs often
    keep a stale mailto target from the template's author (seen twice in the
    gold set: the link pointed at a different person's address), while the
    visible address is what the candidate actually wrote."""
    for page in doc.pages:
        for line in page.lines:
            m = EMAIL_RE.search(contact_text(line))
            if m:
                return m.group(0).rstrip(".,;"), Provenance(line_ids=[line.id], component="header.email.regex")
    for page in doc.pages:
        for link in page.links:
            if link.uri.lower().startswith("mailto:"):
                m = EMAIL_RE.search(link.uri[7:].split("?")[0])
                if m:
                    return m.group(0), Provenance(component="header.email.mailto")
    return "", None


def _digits(s: str) -> int:
    return sum(c.isdigit() for c in s)


def _find_number(text: str) -> str | None:
    """E.164 of the first plausible phone number in `text`, else None."""
    if _DATE_RANGE.search(text):  # "2024 - 2028" parses as a number
        text = _DATE_RANGE.sub(" ", text)
    for region, leniency in (("IN", phonenumbers.Leniency.VALID), (None, phonenumbers.Leniency.VALID)):
        for m in phonenumbers.PhoneNumberMatcher(text, region, leniency=leniency):
            if _digits(m.raw_string) >= 10:
                return phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
    # Template/US-style numbers with an explicit +CC that aren't "valid" (e.g.
    # +1 555 ...): accept only when the country code is spelled out.
    for m in phonenumbers.PhoneNumberMatcher(text, None, leniency=phonenumbers.Leniency.POSSIBLE):
        if m.raw_string.lstrip().startswith("+") and _digits(m.raw_string) >= 10:
            return phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
    # Last resort: an explicit "+CC ..." number phonenumbers rejects (placeholder
    # numbers in templates). Kept as digits so it's at least comparable.
    m = re.search(r"\+\d{1,3}[\s\-.]?\(?\d[\d\s\-.()]{7,}\d", text)
    if m and _digits(m.group(0)) >= 10:
        return "+" + re.sub(r"\D", "", m.group(0))
    return None


def extract_phone(doc: Document) -> tuple[str, Provenance | None]:
    for page in doc.pages:
        for link in page.links:
            if link.uri.lower().startswith("tel:"):
                num = _find_number(link.uri[4:].replace("%20", " "))
                if num:
                    return num, Provenance(component="header.phone.tel")
    for page in doc.pages:
        for line in page.lines:
            text = EMAIL_RE.sub(" ", contact_text(line))  # digits inside emails aren't phones
            num = _find_number(text)
            if num:
                return num, Provenance(line_ids=[line.id], component="header.phone.regex")
    return "", None
