"""Lean date finder for the Stage 10 rules baseline. Stage 11 owns the full
`parse_period`; this only locates a range inside text and returns ISO-ish
strings ("YYYY-MM-01") so the eval harness can compare them."""

import re
from dataclasses import dataclass

_MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
_MON = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_POINT = rf"(?:{_MON}[\s,.]*(?:'|’)?\s*(?:\d{{4}}|\d{{2}}(?!\d))|\b\d{{1,2}}\s*[/.-]\s*\d{{4}}\b|\b(?:19|20)\d{{2}}\b)"
_CURRENT = r"(?:present|current(?:ly)?|now|ongoing|till\s+date|to\s+date|today)"
_DASH = r"\s*(?:-|–|—|‒|to|until|till|through)\s*"
_YEAR_SPAN = r"\b((?:19|20)\d{2})\s*[-–—/]\s*((?:19|20)?\d{2})\b(?![\d/])"
RANGE_RE = re.compile(rf"({_POINT}){_DASH}({_POINT}|{_CURRENT})", re.I)
POINT_RE = re.compile(_POINT, re.I)
CURRENT_RE = re.compile(rf"\b{_CURRENT}\b", re.I)
YEAR_SPAN_RE = re.compile(_YEAR_SPAN)
_EXPECTED = re.compile(r"\b(?:expected|exp\.?|anticipated)\b[\s:]*", re.I)


@dataclass
class Found:
    span: tuple[int, int]
    start: str  # "" when unknown
    end: str | None  # None when current
    current: bool
    raw: str


def to_iso(point: str) -> str:
    """'Aug 2022' / '08/2023' / "Aug '22" / '2022' -> YYYY-MM-01 (a bare year -> YYYY-01-01)."""
    p = point.strip().lower().replace("’", "'")
    m = re.match(rf"({_MON})[\s,.]*'?\s*(\d{{4}}|\d{{2}})$", p)
    if m:
        y = m.group(2)
        y = int(y) if len(y) == 4 else 2000 + int(y)
        return f"{y:04d}-{_MONTHS[m.group(1)[:3]]:02d}-01"
    m = re.match(r"(\d{1,2})\s*[/.-]\s*(\d{4})$", p)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}-01"
    m = re.match(r"((?:19|20)\d{2})$", p)
    return f"{m.group(1)}-01-01" if m else ""


def find_range(text: str) -> Found | None:
    """First date range in `text`, else a lone date point, else None."""
    m = RANGE_RE.search(text)
    if m:
        cur = bool(CURRENT_RE.fullmatch(m.group(2).strip()))
        return Found(m.span(), to_iso(m.group(1)), None if cur else to_iso(m.group(2)), cur, m.group(0))
    m = YEAR_SPAN_RE.search(text)
    if m:
        a, b = m.group(1), m.group(2)
        b = b if len(b) == 4 else a[:2] + b
        return Found(m.span(), to_iso(a), to_iso(b), False, m.group(0))
    m = POINT_RE.search(text)
    if m:
        e = _EXPECTED.search(text[: m.start()])
        s = e.start() if e else m.start()
        return Found((s, m.end()), "", to_iso(m.group(0)), False, text[s : m.end()])  # lone date: caller decides start/end
    return None


def strip_range(text: str) -> tuple[str, Found | None]:
    f = find_range(text)
    if not f:
        return text, None
    rest = (text[: f.span[0]] + " " + text[f.span[1] :]).strip(" ,;|-–—()[]\t")
    return re.sub(r"\s{2,}", " ", rest), f
