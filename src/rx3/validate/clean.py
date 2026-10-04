"""Validation, dedupe and ordering of the final object (PROMPT.md §5 Stage 12)."""

import re

from rapidfuzz.distance import JaroWinkler
from resume import ParsedResumeData

from rx3.validate.grounding import norm

DEDUPE_SIM = 0.95
# section -> (key function over an entry, field(s) that make an entry non-empty)
_KEYS = {
    "workHistory": lambda e: f"{norm(e['company'])}|{norm(e['title'])}|{e['period']['start']}",
    "education": lambda e: f"{norm(e['institution'])}|{norm(e['field']['type'])}",
    "projects": lambda e: norm(e["title"]),
    "certifications": lambda e: norm(e["name"]),
    "awards": lambda e: norm(e["name"]),
    "affiliations": lambda e: f"{norm(e['organization'])}|{norm(e['role'])}",
    "publications": lambda e: norm(e["title"]),
    "languages": lambda e: norm(e["lang"]),
    "interests": lambda e: norm(e["activity"]),
}
_LIST_FIELDS = {"workHistory": ("responsibilities", "achievements"), "projects": ("description", "metrics", "techStack"),
                "affiliations": ("impact",)}


def _line_no(e: dict) -> int:
    nums = [int(x[1:]) for x in e.get("_lines", []) if re.fullmatch(r"L\d+", x)]
    return min(nums) if nums else 10**9


def _non_empty(section: str, e: dict) -> bool:
    if section == "workHistory":
        return bool(e["title"] or e["company"] or e["period"]["start"] or e["period"]["end"] or e["period"]["isCurrent"])
    if section == "education":
        return bool(e["institution"] or e["field"]["type"] or e["field"]["course"])
    return bool(_KEYS[section](e).strip("|"))


def _merge(a: dict, b: dict, section: str) -> None:
    """Fold duplicate `b` into `a`: fill empty scalars, append unseen list items."""
    for k, v in b.items():
        if k.startswith("_") or k == "period":
            continue
        if isinstance(v, str) and v and not a.get(k):
            a[k] = v
        elif isinstance(v, list) and isinstance(a.get(k), list):
            a[k] += [x for x in v if x not in a[k]]
    a["_lines"] = sorted(set(a.get("_lines", [])) | set(b.get("_lines", [])), key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)


def dedupe_and_order(data: dict) -> tuple[dict, list[str]]:
    """Drop empty entries, merge near-duplicates (fuzzy key >= 0.95), keep document order. Returns (data, notes)."""
    out, notes = dict(data), []
    for section, key_fn in _KEYS.items():
        entries = [e for e in data.get(section, []) if _non_empty(section, e)]
        entries.sort(key=_line_no)  # stable: same-line entries keep their order
        kept: list[dict] = []
        for e in entries:
            k = key_fn(e)
            dup = next((x for x in kept if k and JaroWinkler.similarity(key_fn(x), k) >= DEDUPE_SIM), None)
            if dup is not None and (section != "workHistory" or dup["period"]["start"] == e["period"]["start"]):
                notes.append(f"{section}: merged duplicate {k[:40]!r}")
                _merge(dup, e, section)
            else:
                kept.append(e)
        out[section] = kept
    # skills: same group label (case-insensitive) merges; tools unique across the whole list
    groups: dict[str, dict] = {}
    seen: set[str] = set()
    for s in data.get("skills", []):
        tools = []
        for t in s["tools"]:
            n = norm(t["name"])
            if n and n not in seen:
                seen.add(n)
                tools.append(t)
        if not tools:
            continue
        g = groups.setdefault(norm(s["field"]), {**s, "tools": []})
        g["tools"] += tools
    out["skills"] = list(groups.values())
    return out, notes


def validate(data: dict) -> tuple[dict, list[str]]:
    """Pydantic-validate; on failure drop the offending list entry (or reset the field) and retry. Never raises."""
    notes: list[str] = []
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    for _ in range(50):
        try:
            return ParsedResumeData.model_validate(data).model_dump(), notes
        except Exception as e:  # pydantic.ValidationError
            errs = getattr(e, "errors", lambda: [])()
            if not errs:
                break
            loc = errs[0]["loc"]
            notes.append(f"validation: dropped {'.'.join(map(str, loc[:2]))}: {errs[0]['msg']}")
            if len(loc) >= 2 and isinstance(loc[1], int) and isinstance(data.get(loc[0]), list):
                data[loc[0]] = [v for i, v in enumerate(data[loc[0]]) if i != loc[1]]
            else:
                data.pop(loc[0], None)
    return ParsedResumeData.model_validate({}).model_dump(), notes + ["validation: gave up, returned empty object"]
