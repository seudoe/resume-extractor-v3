"""Rules baseline: entries -> ParsedResumeData-shaped dicts, per section."""

import re

from ir import Line

from rx3.fields.rules.dates import Found, find_range, strip_range
from rx3.fields.rules.lex import is_company as _is_company, is_title as _is_title
from rx3.fields.rules.entries import CELL, Entry, cells, per_line_entries, split_entries, strip_glyph

_DEGREE = re.compile(
    r"\b(bachelor|master|doctor|associate|diploma|certificate|b\.?\s?tech|m\.?\s?tech|b\.?\s?e|m\.?\s?e|b\.?\s?sc|m\.?\s?sc|"
    r"b\.?\s?a|m\.?\s?a|b\.?\s?s|m\.?\s?s|mba|bba|bca|mca|ph\.?\s?d|hsc|ssc|cbse|icse|high school|secondary|"
    r"higher secondary|intermediate|12th|10th|xii|a levels?|o levels?|ged)\b", re.I)
_INSTITUTION = re.compile(
    r"\b(university|college|institute|school|academy|polytechnic|vidyalaya|vidyapeeth|iit|nit|iiit|bits|campus|"
    r"universit[ày]|institut|faculty)\b", re.I)
_SCORE = re.compile(r"\b(cgpa|gpa|percentage|percent|grade|score|aggregate)\b\s*[:\-]?\s*([\d.]+\s*(?:%|/\s*\d+(?:\.\d+)?)?)", re.I)
_TECH_LINE = re.compile(r"^\s*(?:tools?|tech(?:nolog(?:y|ies))?(?: stack| used)?|stack|built with|skills used|environment)\s*[:\-]\s*(.+)$", re.I)
_SEP = re.compile(r"\s+(?:\||at|@|[-–—]|ï1⁄4​?|ï¼​?)\s+|\s*\|\s*|\s+(?=Company Name\b)", re.I)
_LOC = re.compile(r"^[A-Z][A-Za-z.' -]+,\s*[A-Z][A-Za-z.' -]+$|^remote$", re.I)


def _body(entry: Entry) -> list[str]:
    return [t for t in (strip_glyph(l.text.replace(CELL, " ")) for l in entry.body) if t]


def _head_candidates(entry: Entry) -> tuple[list[str], Found | None]:
    """Head cells with the date range removed; split fragments merged ('Jan 2022 -' + 'Present')."""
    texts = [c for l in entry.head for c in cells(l.text)]
    joined = " ⇥ ".join(texts)
    found = find_range(joined)
    if not found or found.start == "" and found.end is not None and not found.current:
        # dates wrapped over two cells ("Jan 2022 -" ... "Present"): stitch them
        for i, t in enumerate(texts):
            if re.search(r"[-–—]\s*$|\bto\s*$", t):
                for j in range(i + 1, len(texts)):
                    if re.fullmatch(r"\s*(?:\w+\.?\s*)?(?:'?\d{2,4}|present|current|now)\s*", texts[j], re.I):
                        texts[i] = f"{t} {texts[j]}"
                        del texts[j]
                        break
                break
    out, found = [], None
    for t in texts:
        rest, f = strip_range(t)
        if f and found is None:
            found = f
        if rest:
            out.append(rest)
    return out, found


_PLACEHOLDER = re.compile(r"\bCompany Name\b(?:\s*(?:ï1⁄4​?|ï¼​?|[-－–])?\s*,?\s*City(?:\s*,\s*State)?)?|\bCity\s*,\s*State\b|^(?:City|State)$", re.I)


def _split_candidates(cands: list[str]) -> list[str]:
    out = []
    for c in cands:
        c = _PLACEHOLDER.sub("", c).strip(" ,;-–")  # LiveCareer anonymisation leftovers
        if not c:
            continue
        parts = [p.strip(" ,;") for p in _SEP.split(c) if p and p.strip(" ,;")]
        if len(parts) > 1 and all(_is_title(p) for p in parts) and not re.search(r"\s(?:at|@|\|)\s", c):
            parts = [c]  # "Accountant - Payables / Accounting Clerk" is one title
        if len(parts) == 1 and ", " in c:  # "Senior Engineer, Acme Inc." (but not "Pune, India")
            a, b = c.split(", ", 1)
            if (_is_title(a) and not _is_title(b)) or (_is_company(a) and _is_title(b)):
                parts = [a.strip(), b.strip()]
        out += parts or [c]
    return out


def _period(found: Found | None, lone_is_end: bool = False) -> dict:
    if not found:
        return {"start": "", "end": None, "isCurrent": False}
    if found.start == "" and found.end and not lone_is_end:
        return {"start": found.end, "end": None, "isCurrent": False}  # a lone work date reads as a start
    return {"start": found.start, "end": found.end if not found.current else None, "isCurrent": found.current}


def _roles(cands: list[str]) -> tuple[str, str, str]:
    cands = _split_candidates(cands)
    title = company = location = ""
    rest = []
    for c in cands:
        if not location and _LOC.match(c) and not _is_title(c) and not _is_company(c):
            location = c
        else:
            rest.append(c)
    for c in rest:
        if not title and _is_title(c) and not (_is_company(c) and not _is_title(c.split()[-1])):
            title = c
    rest = [c for c in rest if c != title]
    for c in rest:
        if _is_company(c):
            company = c
            break
    if not company and rest:
        company = rest[0]
    if not title and company:  # nothing title-like: first head cell is the title
        title, company = company, (rest[1] if len(rest) > 1 else "")
    return title, company, location


def work(entry: Entry) -> dict:
    cands, found = _head_candidates(entry)
    title, company, location = _roles(cands)
    return {
        "title": title, "company": company, "location": location,
        "type": "internship" if re.search(r"\bintern(ship)?\b", title, re.I) else "job",
        "period": _period(found), "responsibilities": _body(entry), "achievements": [],
    }


def _degree_split(text: str) -> tuple[str, str]:
    parts = re.split(r"\s+in\s+|\s*:\s*|\s*[,–—-]\s+", text, maxsplit=1)
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (text.strip(), "")


_INST_OF = re.compile(r"\b(?:University|College|Institute|School)\s+of\s+(?:the\s+)?(?:[A-Z][\w'’&.-]*\s*){1,3}")
_INST_RUN = re.compile(r"(?:[A-Z][\w'’&.-]*\s+){0,3}(?:University|College|Institute|School|Academy|Polytechnic)\b")


def _lift_institution(cands: list[str]) -> list[str]:
    """Plain-document rows glue everything into one cell ("Associate of Science : Health Administration
    El Centro Community College"): pull the institution out as its own candidate, leave the rest in place."""
    out = []
    for c in cands:
        m = _INST_OF.search(c) or _INST_RUN.search(c)
        if m and len(c) > len(m.group(0)) + 3 and _DEGREE.search(c):  # only when degree text shares the cell
            out += [m.group(0).strip(), (c[: m.start()] + " " + c[m.end() :]).strip(" ,;:-")]
        else:
            out.append(c)
    return [c for c in out if c]


_DEGREE_START = re.compile(r"(?=\b(?:Master|Bachelor|Associate|Doctor|Diploma)(?:'s)?\s+(?:of|in|degree)\b)", re.I)


def _split_degrees(lines: list[Line]) -> list[Line]:
    """One plain row listing several degrees ("Master of Science : X ... Bachelor of Science : Y") becomes one row each."""
    out = []
    for l in lines:
        parts = [p for p in _DEGREE_START.split(l.text) if p.strip()]
        out += [l.model_copy(update={"text": p.strip()}) for p in parts] if len(parts) > 1 else [l]
    return out


def _edu_head(l: Line) -> tuple[bool, bool]:
    return bool(_DEGREE.search(l.text)), bool(_INSTITUTION.search(l.text))


def _edu_opens(cur: Entry, l: Line) -> bool:
    """A second degree (or second institution) line can't belong to the same entry."""
    deg, inst = _edu_head(l)
    cdeg = any(_edu_head(h)[0] for h in cur.head)
    cinst = any(_edu_head(h)[1] for h in cur.head)
    return (deg and cdeg) or (inst and cinst and not deg)


def education(entry: Entry) -> dict:
    cands, found = _head_candidates(entry)
    cands = _lift_institution(_split_candidates(cands))
    inst = next((c for c in cands if _INSTITUTION.search(c)), "")
    deg = next((c for c in cands if c != inst and _DEGREE.search(c)), "")
    if not inst:
        rest = [c for c in cands if c != deg and not _LOC.match(c)]
        inst = rest[0] if rest else ""
    dtype, course = _degree_split(deg) if deg else ("", "")
    if not course:  # "Bachelor of Technology ⇥ Information Technology" on separate cells
        extra = [c for c in cands if c not in (inst, deg) and not _LOC.match(c) and not find_range(c)]
        course = extra[0] if extra and deg else ""
    out = ""
    for t in [l.text for l in entry.lines]:
        m = _SCORE.search(t)
        if m:
            out = f"{m.group(1).upper() if len(m.group(1)) <= 4 else m.group(1).title()}: {m.group(2).strip()}"
            break
    return {"institution": inst, "field": {"type": dtype, "course": course}, "period": _period(found, lone_is_end=True), "output": out}


def project(entry: Entry) -> dict:
    cands = [c for l in entry.head for c in cells(l.text)]
    title = cands[0] if cands else ""
    desc, tech = [], []
    m = re.match(r"^(.{2,60}?)\s*[:|]\s+(.+)$", title)
    if m:
        title, tail = m.group(1), m.group(2)
        t = _TECH_LINE.match(tail)
        (tech.extend if t else desc.append)(re.split(r"\s*[,;/]\s*", t.group(1)) if t else tail)
    for line in [c for l in entry.head[1:] for c in cells(l.text)] + _body(entry):
        t = _TECH_LINE.match(line)
        if t:
            tech += [x.strip() for x in re.split(r"\s*[,;|]\s*", t.group(1)) if x.strip()]
        else:
            desc.append(line)
    return {"title": title, "role": "", "links": {"repo": "", "live": None, "demo": None}, "techStack": tech,
            "problemStatement": None, "metrics": [], "technicalChallenges": [], "description": desc, "architecture": ""}


def award(entry: Entry) -> dict:
    cands, found = _head_candidates(entry)
    cands = _split_candidates(cands)
    return {"name": cands[0] if cands else "", "issuingBody": cands[1] if len(cands) > 1 else "",
            "date": found.raw if found else "", "justification": " ".join(_body(entry))}


def certification(entry: Entry) -> dict:
    cands, found = _head_candidates(entry)
    return {"name": cands[0] if cands else "", "issuer": cands[1] if len(cands) > 1 else "", "skillsEarned": [],
            "type": "", "date": found.raw if found else ""}


def affiliation(entry: Entry) -> dict:
    cands, found = _head_candidates(entry)
    title, org, _ = _roles(cands)
    return {"organization": org, "role": title, "type": "", "impact": _body(entry), "period": _period(found)}


def publication(entry: Entry) -> dict:
    cands, found = _head_candidates(entry)
    return {"title": (cands[0] if cands else "").strip("\"'“”"), "platform": cands[1] if len(cands) > 1 else "",
            "type": "paper", "link": "", "keywords": [], "date": found.raw if found else ""}


def languages(lines: list[Line]) -> list[dict]:
    out = []
    for l in lines:
        for item in re.split(r"\s*[,;|]\s*|\t", strip_glyph(l.text)):
            m = re.match(r"^([A-Za-z][A-Za-z ]{1,24}?)\s*(?:[(:–-]\s*)?([A-Za-z ]*?)\)?$", item.strip())
            if m and item.strip():
                out.append({"lang": m.group(1).strip(), "proficiency": m.group(2).strip(), "score": None})
    return out


def interests(lines: list[Line]) -> list[dict]:
    items = [i.strip() for l in lines for i in re.split(r"\s*[,;|•]\s*|\t", strip_glyph(l.text)) if i.strip()]
    return [{"activity": i, "description": "", "commitmentMetric": None} for i in items]


def skills(lines: list[Line]) -> list[dict]:
    out = []
    for l in lines:
        text = strip_glyph(l.text.replace(CELL, ", "))
        label, _, rest = text.partition(":") if re.match(r"^[^:]{1,40}:\s*\S", text) else ("", "", text)
        names = [n.strip() for n in re.split(r"\s*[,;|•]\s*", rest) if n.strip()]
        if names:
            out.append({"field": label.strip(), "yearsOfExperience": 0, "lastUsed": "", "tools": [{"name": n, "score": None} for n in names]})
    return out


ENTRY_BUILDERS = {"workHistory": work, "education": education, "projects": project, "awards": award,
                  "certifications": certification, "affiliations": affiliation, "publications": publication}
PER_LINE = {"awards", "certifications", "publications"}  # one bullet = one entry when nothing is styled


def build_section(name: str, lines: list[Line]) -> list[dict] | str:
    if name == "summary":
        return " ".join(strip_glyph(l.text.replace(CELL, " ")) for l in lines)
    if name == "skills":
        return skills(lines)
    if name == "languages":
        return languages(lines)
    if name == "interests":
        return interests(lines)
    if name in ENTRY_BUILDERS:
        edu = name == "education"
        entries = split_entries(_split_degrees(lines) if edu else lines, _edu_opens if edu else None)
        if name in PER_LINE and len(entries) <= 1 and len(lines) > 2:
            entries = per_line_entries(lines)
        return [e for e in (ENTRY_BUILDERS[name](x) for x in entries) if any(v for v in e.values() if v)]
    return []
