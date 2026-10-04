"""Skills: canonical names, grouping into `field` buckets, years/lastUsed from work periods (Stage 11).

Sources of skills: (1) the resume's own skill lists (their `Label: a, b` grouping is kept), (2) explicit
tech-stack lines of projects/work (`techStack`), (3) optionally curated-technology mentions in bullets.
Skills that appear only under Interests are never skills (interests are a separate list and never read here)."""

import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from rx3.normalise._tech import CASE_SENSITIVE, LIST_ONLY, TECH

_NAMES_FILE = Path(__file__).with_name("_skill_names.txt")
_STRIP = " \t.,;:-–—•*()[]"


@lru_cache(maxsize=1)
def _canon_map() -> dict[str, tuple[str, str]]:
    """alias (lower) -> (canonical, group); first listing wins."""
    out: dict[str, tuple[str, str]] = {}
    for group, entries in TECH.items():
        for entry in entries:
            canonical, *aliases = entry.split("|")
            for a in [canonical, *aliases]:
                out.setdefault(a.lower(), (canonical, group))
    return out


@lru_cache(maxsize=1)
def _db_names() -> dict[str, str]:
    return {n.lower(): n for n in _NAMES_FILE.read_text(encoding="utf-8").splitlines() if n}


def canonical(item: str) -> tuple[str, str]:
    """(name, group) for a raw skill item; group is '' when unknown. Case-sensitive names (C, R, Go...) keep
    their exact spelling so 'c' in running text isn't a language."""
    t = item.strip(_STRIP)
    hit = _canon_map().get(t.lower())
    if hit and (hit[0] not in CASE_SENSITIVE or t == hit[0] or len(t) > 2):
        return hit
    db = _db_names().get(t.lower())
    return (db, "") if db else (t, "")


@lru_cache(maxsize=1)
def _discovery_patterns() -> list[tuple[str, str, re.Pattern]]:
    pats = []
    for alias, (name, group) in _canon_map().items():
        if name in LIST_ONLY or len(alias) < 2:
            continue
        flags = 0 if name in CASE_SENSITIVE else re.I
        pats.append((name, group, re.compile(rf"(?<![\w+#.]){re.escape(alias if name in CASE_SENSITIVE else alias)}(?![\w+#]|\.\w)", flags)))
    return pats


def find_in_text(text: str) -> list[tuple[str, str]]:
    """Curated technologies mentioned in free text, as (name, group), first-seen order."""
    seen, out = set(), []
    for name, group, rx in _discovery_patterns():
        if name not in seen and rx.search(text):
            seen.add(name)
            out.append((name, group))
    return out


def _months(p: dict) -> tuple[int, int] | None:
    s = p.get("start") or ""
    e = p.get("end") or ""
    if not s:
        return None
    y0, m0 = int(s[:4]), int(s[5:7])
    if p.get("isCurrent") or not e:
        if not p.get("isCurrent"):
            return None  # no end and not current: unknown span, never guessed
        y1, m1 = date.today().year, date.today().month
    else:
        y1, m1 = int(e[:4]), int(e[5:7])
    a, b = y0 * 12 + m0, y1 * 12 + m1
    return (a, b) if b >= a else None


def _years_and_last(entries: list[dict]) -> tuple[float, str]:
    spans = sorted(s for s in (_months(e["period"]) for e in entries) if s)
    merged: list[list[int]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    years = round(sum(b - a for a, b in merged) / 12, 1)
    last = ""
    if any(e["period"].get("isCurrent") for e in entries):
        last = "Present"
    else:
        ends = [e["period"]["end"][:7] for e in entries if e["period"].get("end")]
        last = max(ends) if ends else ""
    return years, last


def _entry_text(e: dict) -> str:
    return " ".join([e.get("title", ""), *e.get("responsibilities", []), *e.get("achievements", []), *e.get("techStack", []),
                     *e.get("description", [])])


def _mentions(tool: str, text: str) -> bool:
    for alias, (name, _) in _canon_map().items():
        if name == tool:
            flags = 0 if name in CASE_SENSITIVE else re.I
            if re.search(rf"(?<![\w+#.]){re.escape(alias)}(?![\w+#]|\.\w)", text, flags):
                return True
    return bool(re.search(rf"(?<![\w+#.]){re.escape(tool)}(?![\w+#])", text, re.I))


def build_skills(parsed: dict, discover_in_bullets: bool = True) -> list[dict]:
    """Merge listed skills, tech-stack lines and (optionally) bullet mentions into grouped Skill dicts."""
    groups: dict[str, list[str]] = {}  # field -> tool names (ordered, unique)
    seen: set[str] = set()

    def add(field: str, name: str) -> None:
        key = name.lower()
        if not name or key in seen or len(name.split()) > 6:
            return
        seen.add(key)
        groups.setdefault(field, []).append(name)

    for s in parsed.get("skills", []):
        label = s.get("field", "").strip(_STRIP)
        for t in s.get("tools", []):
            name, group = canonical(t["name"])
            add(label or group or "Other Skills", name)
    for sec in ("projects", "workHistory"):
        for e in parsed.get(sec, []):
            for t in e.get("techStack", []):
                name, group = canonical(t)
                add(group or "Other Skills", name)
            if discover_in_bullets:
                for name, group in find_in_text(_entry_text(e)):
                    add(group, name)

    work = [e for e in parsed.get("workHistory", []) if e.get("period")]
    out = []
    for field, tools in groups.items():
        hits = [e for e in work if any(_mentions(t, _entry_text(e)) for t in tools)]
        years, last = _years_and_last(hits) if hits else (0.0, "")
        out.append({"field": field, "yearsOfExperience": years, "lastUsed": last, "tools": [{"name": t, "score": None} for t in tools]})
    return out
