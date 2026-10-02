"""Map resume-extract (v2)'s raw output shape to v3's ParsedResumeData shape,
the same way ifind/lib/resumeParser.ts's `normaliseHFOutput` does: v2's
`_meta` (name/email/phone/linkedin/github/otherLinks) becomes `metaDetails`.

v2's ISO datetimes ("2024-08-01T00:00:00") are truncated to v3's date-only
("2024-08-01") for comparison; v2's extra per-entry fields (e.g.
`workHistory[].techStack`) are left as-is and simply ignored by v3's schema
(Pydantic drops unknown fields by default) rather than stripped here.
"""

import json
from pathlib import Path


def _truncate_dates(node):
    if isinstance(node, str) and "T00:00:00" in node:
        return node.split("T")[0]
    if isinstance(node, dict):
        return {k: _truncate_dates(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_truncate_dates(v) for v in node]
    return node


def normalise_v2_output(raw: dict) -> dict:
    meta = raw.get("_meta") or {}
    metaDetails = {
        "name": meta.get("name") or "",
        "phone_no": meta.get("phone") or "",
        "gender": None,
        "email": meta.get("email") or "",
        "github_profile": meta.get("github") or None,
        "linkedin": meta.get("linkedin") or None,
        "address": {"city": "", "state": None, "country": "", "postal_code": None},
        "extra_links": [
            {"name": link.get("label") or link.get("url") or "", "link": link.get("url") or ""}
            for link in (meta.get("otherLinks") or [])
        ],
    }
    rest = {k: v for k, v in raw.items() if k != "_meta"}
    rest["metaDetails"] = metaDetails
    return _truncate_dates(rest)


def load_v2_baseline(tested_jsons_dir: Path) -> dict[str, dict]:
    """Returns {source_filename_stem: normalised_output} for every
    pre-computed v2 JSON in resume-data/resume-extract-tested-jsons/."""
    out = {}
    for path in Path(tested_jsons_dir).glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        out[path.stem] = normalise_v2_output(raw)
    return out
