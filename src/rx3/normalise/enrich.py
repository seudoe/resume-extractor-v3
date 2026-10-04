"""Work type, award/certification split, project fields (Stage 11)."""

import re

from ir import BBox, Document

from rx3.normalise.bullets import has_number, split_bullets
from rx3.normalise.skills import find_in_text

_INTERN = re.compile(r"\bintern(?:ship)?s?\b|\btrainee\b|\bapprentice\b", re.I)
_VOLUNTEER = re.compile(r"\bvolunteer(?:ing|s)?\b|\bcommunity service\b", re.I)
_COOP = re.compile(r"\bco-?op\b", re.I)
_AWARD = re.compile(
    r"\b(?:winner|won|wins|rank(?:ed)?|runner[- ]?up|finalist|prize|scholarship|medal(?:ist)?|top\s*\d+|topper|1st|2nd|3rd|"
    r"first place|second place|third place|hackathon|honou?rs?|dean'?s list|employee of the|award(?:ed)?|fellowship|champion|"
    r"specialist on|\d+[- ]star|grand prix|olympiad|contest|competition)\b", re.I)
_CERT = re.compile(
    r"\b(?:certified|certification|certificate|certificates|course|specialization|nanodegree|coursera|nptel|udemy|edx|udacity|"
    r"linkedin learning|simplilearn|great learning|pluralsight|license|licen[cs]ed|diploma|training|bootcamp|"
    r"aws|azure|google|microsoft|oracle|cisco|comptia|pmp|scrum master)\b", re.I)
_REPO_HOSTS = ("github.com", "gitlab.com", "bitbucket.org")


def work_type(e: dict) -> str:
    """internship / volunteer / co-op from the title, company and the section heading it sat under; else job."""
    hay = f"{e['title']} {e['company']}"
    heading = e.get("_heading", "")
    if _INTERN.search(hay) or _INTERN.search(heading):
        return "internship"
    if _VOLUNTEER.search(hay) or _VOLUNTEER.search(heading):
        return "volunteer"
    if _COOP.search(hay) or _COOP.search(heading):
        return "co-op"
    return e["type"] if e["type"] in ("job", "internship", "volunteer", "co-op") else "job"


def enrich_work(e: dict) -> dict:
    resp, ach = split_bullets(e["responsibilities"] + e["achievements"])
    return {**e, "type": work_type(e), "responsibilities": resp, "achievements": ach}


def classify_award_or_cert(name: str, issuer: str = "") -> str | None:
    """'award' / 'certification' by keywords, or None when it is a tie or has no signal (keep the source section)."""
    text = f"{name} {issuer}"
    a, c = bool(_AWARD.search(text)), bool(_CERT.search(text))
    if a and not c:
        return "award"
    if c and not a:
        return "certification"
    return None


def split_awards_and_certs(awards: list[dict], certs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Reclassify every entry by wording, regardless of which section it sat in; ambiguous ones stay put."""
    out_a, out_c = [], []
    for a in awards:
        kind = classify_award_or_cert(a["name"], a["issuingBody"]) or "award"
        if kind == "award":
            out_a.append(a)
        else:
            out_c.append({"name": a["name"], "issuer": a["issuingBody"], "skillsEarned": [], "type": "", "date": a["date"],
                          **{k: v for k, v in a.items() if k.startswith("_")}})
    for c in certs:
        kind = classify_award_or_cert(c["name"], c["issuer"]) or "certification"
        if kind == "certification":
            out_c.append(c)
        else:
            out_a.append({"name": c["name"], "issuingBody": c["issuer"], "date": c["date"], "justification": "",
                          **{k: v for k, v in c.items() if k.startswith("_")}})
    return out_a, out_c


def _bbox_of(doc: Document, line_ids: list[str]) -> tuple[int, BBox] | None:
    ids = set(line_ids)
    lines = [l for p in doc.pages for l in p.lines if l.id in ids]
    if not lines:
        return None
    page = lines[0].page
    ls = [l for l in lines if l.page == page]
    return page, BBox(x0=min(l.bbox.x0 for l in ls), y0=min(l.bbox.y0 for l in ls),
                      x1=max(l.bbox.x1 for l in ls), y1=max(l.bbox.y1 for l in ls))


def _links_in(doc: Document, page_no: int, box: BBox) -> list[str]:
    page = next((p for p in doc.pages if p.lines and p.lines[0].page == page_no), None)
    if not page:
        return []
    out = []
    for lk in page.links:
        cx, cy = (lk.bbox.x0 + lk.bbox.x1) / 2, (lk.bbox.y0 + lk.bbox.y1) / 2
        if box.x0 - 2 <= cx <= box.x1 + 2 and box.y0 - 2 <= cy <= box.y1 + 2 and lk.uri.startswith(("http://", "https://")):
            out.append(lk.uri)
    return out


def enrich_project(e: dict, doc: Document) -> dict:
    links = dict(e["links"])
    found = _bbox_of(doc, e.get("_lines", []))
    if found:
        for uri in _links_in(doc, *found):
            if any(h in uri for h in _REPO_HOSTS):
                links["repo"] = links["repo"] or uri
            elif not links.get("live"):
                links["live"] = uri
    tech = list(e["techStack"])
    if not tech:  # no "Tools:" line: curated technologies named inside the block
        tech = [n for n, _ in find_in_text(" ".join([e["title"], *e["description"]]))]
    title = re.sub(r"\s*[|–—]\s*.*$", "", e["title"]).strip() if " | " in e["title"] else e["title"]
    return {**e, "title": title, "links": links, "techStack": tech, "metrics": [d for d in e["description"] if has_number(d)]}
