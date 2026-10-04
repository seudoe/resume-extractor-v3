"""Per-field confidence in 0-1 (PROMPT.md §5 Stage 12).

Calibrated fields (work title, education institution / degree type, period): a feature bucket per field maps to
the accuracy measured on held-out LiveCareer weak labels (`eval/calibrate_confidence.py` writes
`_calibration.json`). Other fields use fixed heuristics and are listed in `UNCALIBRATED`, so a consumer knows
which numbers are measured and which are priors."""

import json
import re
from functools import lru_cache
from pathlib import Path

from rx3.fields.rules.lex import is_company, is_title
from rx3.normalise.skills import _canon_map, _db_names

_CAL = Path(__file__).with_name("_calibration.json")
UNCALIBRATED = ["workHistory.company", "workHistory.location", "projects.*", "awards.*", "certifications.*",
                "affiliations.*", "publications.*", "languages.*", "interests.*", "skills.*", "summary"]
_PRIOR = {"hit": 0.9, "miss": 0.5}


@lru_cache(maxsize=1)
def _calibration() -> dict:
    return json.loads(_CAL.read_text(encoding="utf-8")) if _CAL.exists() else {}


def bucket(field: str, e: dict) -> str:
    """Feature bucket for a calibrated field of entry `e` (shared with the calibration script)."""
    if field == "work.title":
        t = e["title"]
        return f"lex={int(is_title(t))}|short={int(len(t.split()) <= 6)}|dated={int(bool(e['period']['start'] or e['period']['isCurrent']))}"
    if field == "edu.institution":
        i = e["institution"]
        kw = bool(re.search(r"\b(university|college|institute|school|academy|polytechnic)\b", i, re.I))
        return f"kw={int(kw)}|short={int(len(i.split()) <= 6)}"
    if field == "edu.degree":
        t = e["field"]["type"]
        from rx3.normalise.education import _COMPILED  # canonical names only

        return f"canon={int(any(n == t for n, _ in _COMPILED))}|has_course={int(bool(e['field']['course']))}"
    if field == "period":
        p = e["period"]
        return f"both={int(bool(p['start'] and (p['end'] or p['isCurrent'])))}|any={int(bool(p['start'] or p['end'] or p['isCurrent']))}"
    raise KeyError(field)


def _calibrated(field: str, e: dict, empty: bool) -> float:
    if empty:
        return 0.0
    row = _calibration().get(field, {}).get(bucket(field, e))
    return round(row["acc"], 3) if row else _PRIOR["miss"]


def score(data: dict, header_prov: dict | None = None) -> dict[str, float]:
    """Flat path -> confidence for the scalar/entity fields of the cleaned (still private-keyed) data."""
    out: dict[str, float] = {}
    for i, e in enumerate(data.get("workHistory", [])):
        out[f"workHistory[{i}].title"] = _calibrated("work.title", e, not e["title"])
        out[f"workHistory[{i}].company"] = (0.8 if is_company(e["company"]) else 0.5) if e["company"] else 0.0
        out[f"workHistory[{i}].period"] = _calibrated("period", e, False)
    for i, e in enumerate(data.get("education", [])):
        out[f"education[{i}].institution"] = _calibrated("edu.institution", e, not e["institution"])
        out[f"education[{i}].field.type"] = _calibrated("edu.degree", e, not e["field"]["type"])
        out[f"education[{i}].period"] = _calibrated("period", e, False)
    for section, key in (("projects", "title"), ("awards", "name"), ("certifications", "name"), ("affiliations", "organization"),
                         ("publications", "title"), ("languages", "lang"), ("interests", "activity")):
        for i, e in enumerate(data.get(section, [])):
            out[f"{section}[{i}].{key}"] = 0.7 if e.get(key) else 0.0
    for i, s in enumerate(data.get("skills", [])):
        for j, t in enumerate(s["tools"]):
            n = t["name"].lower()
            out[f"skills[{i}].tools[{j}]"] = 0.95 if n in _canon_map() else 0.8 if n in _db_names() else 0.6
    for k, prov in (header_prov or {}).items():
        out[f"metaDetails.{k}"] = round(float(prov.confidence), 3)
    return out
