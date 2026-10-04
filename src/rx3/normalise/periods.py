"""`parse_period(text) -> DateRange` (PROMPT.md §5 Stage 11).

Empty-value policy: an unknown start stays "" and an unknown end stays None;
nothing is ever filled with today's date (v2 did that). Dates are "YYYY-MM-01"
(a bare year -> "YYYY-01-01"; a season/quarter -> its first month).
"""

import re
from datetime import date

from generics import DateRange

from rx3.fields.rules.dates import CURRENT_RE, find_range, to_iso

_SEASON = {"spring": 3, "summer": 6, "fall": 9, "autumn": 9, "winter": 1}
_SEASON_RE = re.compile(r"\b(spring|summer|fall|autumn|winter)\s*(?:of\s+)?'?((?:19|20)?\d{2})\b", re.I)
_QUARTER_RE = re.compile(r"\bQ([1-4])\s*[-'’ ]?\s*((?:19|20)\d{2})\b", re.I)
_EXPECTED_RE = re.compile(r"\b(?:expected|exp\.?|anticipated|pursuing|ongoing|in progress)\b", re.I)


def _year(y: str) -> int:
    return int(y) if len(y) == 4 else 2000 + int(y)


def _special(text: str) -> str:
    """Season / quarter point -> ISO, else ""."""
    m = _QUARTER_RE.search(text)
    if m:
        return f"{int(m.group(2)):04d}-{(int(m.group(1)) - 1) * 3 + 1:02d}-01"
    m = _SEASON_RE.search(text)
    if m:
        return f"{_year(m.group(2)):04d}-{_SEASON[m.group(1).lower()]:02d}-01"
    return ""


def parse_period(text: str, today: date | None = None, lone_is_end: bool = False) -> DateRange:
    """Range -> DateRange. A lone date is a start for jobs and an end for education (`lone_is_end`);
    "Expected May 2027" is always an end. `isCurrent` is True for Present/Current and for an expected end
    in the future (so a student still enrolled is current)."""
    today = today or date.today()
    if not text or not text.strip():
        return DateRange()
    expected = bool(_EXPECTED_RE.search(text))
    # seasons / quarters ("Summer 2024 - Fall 2024", "Q3 2023") are not understood by the range regex
    parts = re.split(r"\s*(?:-|–|—|\bto\b|until|through)\s*", text, maxsplit=1)
    sp = [_special(p) for p in parts]
    f0 = find_range(text)
    if any(sp) and not (f0 and (f0.start or f0.current)):
        if len(parts) == 2 and sp[0] and CURRENT_RE.search(parts[1]):
            return DateRange(start=sp[0], end=None, isCurrent=True)
        if len(parts) == 2 and sp[0] and sp[1]:
            return DateRange(start=sp[0], end=sp[1], isCurrent=False)
        one = next(x for x in sp if x)
        return DateRange(start="", end=one, isCurrent=False) if (lone_is_end or expected) else DateRange(start=one)
    f = find_range(text)
    if not f:
        return DateRange(isCurrent=bool(CURRENT_RE.search(text)))
    if f.current:
        return DateRange(start=f.start, end=None, isCurrent=True)
    if f.start == "" and f.end:  # lone date
        if lone_is_end or expected:
            future = f.end > today.isoformat()[:10]
            return DateRange(start="", end=f.end, isCurrent=future)
        return DateRange(start=f.end, end=None, isCurrent=False)
    future = bool(expected and f.end and f.end > today.isoformat()[:10])
    return DateRange(start=f.start, end=f.end, isCurrent=future)


def finish_period(p: dict, kind: str, today: date | None = None) -> dict:
    """Apply the isCurrent policy to a period dict from the rules stage: an education entry whose end date
    lies in the future is still being studied (end kept); a work entry never has a future end."""
    today = today or date.today()
    end = p.get("end") or ""
    if kind == "education" and end and end > today.isoformat()[:10]:
        return {**p, "isCurrent": True}
    return p


__all__ = ["parse_period", "finish_period", "to_iso"]
