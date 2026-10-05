"""Helpers for hand-drafting gold entries (PROMPT.md §4.1: the agent may draft gold by reading the resume's raw text,
offline, no hosted-LLM output). Each constructor fills schema defaults so a drafted resume is just the facts that were
read; `save()` merges them into data/gold/drafts/<id>.json, takes metaDetails from the hand-checked header gold, marks
the file `drafted` (never `verified`: only the user verifies) and keeps a note on judgement calls.

    from gold_fill import W, E, P, C, A, SK, save
"""

import json
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent / "data" / "gold"


def period(start="", end="", cur=False) -> dict:
    return {"start": start, "end": None if cur else end, "isCurrent": cur}


def W(title, company, start="", end="", cur=False, loc="", bullets=(), ach=(), type="job") -> dict:
    return {"title": title, "company": company, "location": loc, "type": type, "period": period(start, end, cur),
            "responsibilities": list(bullets), "achievements": list(ach)}


def E(inst, dtype="", course="", start="", end="", cur=False, out="") -> dict:
    return {"institution": inst, "field": {"type": dtype, "course": course}, "period": period(start, end, cur), "output": out}


def P(title, tech=(), desc=(), repo="", live=None, role="", metrics=()) -> dict:
    return {"title": title, "role": role, "links": {"repo": repo, "live": live, "demo": None}, "techStack": list(tech), "problemStatement": None,
            "metrics": list(metrics), "technicalChallenges": [], "description": list(desc), "architecture": ""}


def C(name, issuer="", date="", type="certification") -> dict:
    return {"name": name, "issuer": issuer, "skillsEarned": [], "type": type, "date": date}


def A(name, body="", date="", why="") -> dict:
    return {"name": name, "issuingBody": body, "date": date, "justification": why}


def SK(field, *tools) -> dict:
    return {"field": field, "yearsOfExperience": 0, "lastUsed": "", "tools": [{"name": t} for t in tools]}


def LANG(lang, prof="") -> dict:
    return {"lang": lang, "proficiency": prof, "score": None}


def AFF(org, role="", impact=(), start="", end="", cur=False, type="") -> dict:
    return {"organization": org, "role": role, "type": type, "impact": list(impact), "period": period(start, end, cur)}


def save(rid: str, summary="", work=(), edu=(), skills=(), projects=(), certs=(), awards=(), langs=(), affs=(), interests=(), pubs=(), note="") -> None:
    path = GOLD / "drafts" / f"{rid}.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["status"] != "verified", f"{rid} is user-verified; not overwriting"
    hdr = json.loads((GOLD / "header" / "header_gold.json").read_text(encoding="utf-8")) if (GOLD / "header" / "header_gold.json").exists() else {}
    p = d["parsed"]
    p.update({"summary": summary, "workHistory": list(work), "education": list(edu), "skills": list(skills), "projects": list(projects),
              "certifications": list(certs), "awards": list(awards), "languages": list(langs), "affiliations": list(affs),
              "interests": [{"activity": i, "description": "", "commitmentMetric": None} for i in interests], "publications": list(pubs)})
    h = hdr.get(Path(d["source_file"]).stem)
    if isinstance(h, dict):
        m = p["metaDetails"]
        m.update({k: h[k] for k in ("name", "phone_no", "email", "github_profile", "linkedin") if k in h})
        m["address"].update({"city": h.get("city", ""), "state": h.get("state"), "country": h.get("country", ""), "postal_code": h.get("postal_code")})
        m["extra_links"] = [x for x in h.get("extra", []) if isinstance(x, dict) and "link" in x]
    d["status"] = "drafted"
    d["drafting_notes"] = ("Hand-drafted by Claude from data/gold/raw text (not LLM-pipeline output); UNVERIFIED. " + note).strip()
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
