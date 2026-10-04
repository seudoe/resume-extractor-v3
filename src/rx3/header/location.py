"""City / state / country / postal code from the header (PROMPT.md §5 Stage 8).

Only what the text says: a city is never inferred from a state, nor a country
from a city ("Thane" alone stays country-less) — nothing invented. Candidate
lines are the header zone plus any contact line, so a college name further
down ("University of Mumbai") can't become the candidate's city.
"""

import re

from ir import Document, Line, Provenance

from rx3.header import gazetteer as G
from rx3.header.zone import EMAIL_RE, contact_text

_US_ABBR = re.compile(r"\s*,\s*([A-Z]{2})(?!\w)")
PIN_RE = re.compile(r"(?<![\d+])\d{6}(?!\d)")


def _alternation(names: list[str]) -> re.Pattern:
    names = sorted(set(names), key=len, reverse=True)  # longest first
    return re.compile(r"(?<![A-Za-z])(?:" + "|".join(re.escape(n) for n in names) + r")(?![A-Za-z])", re.I)


_CITIES = G.INDIAN_CITIES + G.WORLD_CITIES
_STATES = G.INDIAN_STATES + G.US_STATES
_CITY = _alternation(_CITIES)
_STATE = _alternation(_STATES)
_COUNTRY = _alternation(list(G.COUNTRIES))
_CANON_COUNTRY = {k.lower(): v for k, v in G.COUNTRIES.items()}


def _canon_case(match: str, names: list[str]) -> str:
    return next((n for n in names if n.lower() == match.lower()), match)


def extract_location(doc: Document, header: list[Line]) -> tuple[dict, Provenance | None]:
    out = {"city": "", "state": None, "country": "", "postal_code": None}
    ids: list[str] = []
    for line in header:
        text = EMAIL_RE.sub(" ", contact_text(line))
        # Last city wins: headers list specific to general ("Andheri, Mumbai,
        # Maharashtra"), and the candidate's city is the general one.
        cities = list(_CITY.finditer(text))
        city = cities[-1] if cities else None
        state = _STATE.search(text)
        country = _COUNTRY.search(text)
        if not (city or state):
            continue
        if city and not out["city"]:
            out["city"] = _canon_case(city.group(0), _CITIES)
        # "New York" is a city *and* a US state: don't let the state regex
        # reuse the city's own text.
        if state and out["state"] is None and not (city and state.span() == city.span()):
            out["state"] = _canon_case(state.group(0), _STATES)
        if city and out["state"] is None:  # US-style "Atlanta, GA"
            ab = _US_ABBR.match(text[city.end():])
            if ab:
                out["state"] = ab.group(1)
        if country and not out["country"]:
            out["country"] = _CANON_COUNTRY[country.group(0).lower()]
        pin = PIN_RE.search(text)
        if pin and out["postal_code"] is None:
            out["postal_code"] = pin.group(0)
        ids.append(line.id)
        if out["city"] and (out["country"] or out["state"]):
            break
    return out, (Provenance(line_ids=ids, component="header.location") if ids else None)
