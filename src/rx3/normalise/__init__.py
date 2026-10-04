"""Stage 11: normalise and enrich the rules (or later GLiNER) output. Pure functions over dicts; every output
string still comes from the source text except normalised dates/degree names (their raw text keeps provenance
through `_lines`, stripped at the end)."""

from datetime import date

from ir import Document

from rx3.normalise.education import normalise_education
from rx3.normalise.enrich import enrich_project, enrich_work, split_awards_and_certs
from rx3.normalise.periods import finish_period, parse_period
from rx3.normalise.skills import build_skills

__all__ = ["normalise", "parse_period", "strip_private"]


def strip_private(node):
    """Drop provenance keys (`_lines`, `_heading`) recursively."""
    if isinstance(node, dict):
        return {k: strip_private(v) for k, v in node.items() if not k.startswith("_")}
    if isinstance(node, list):
        return [strip_private(v) for v in node]
    return node


def normalise(parsed: dict, doc: Document, today: date | None = None, keep_private: bool = False) -> dict:
    out = {**parsed}
    out["workHistory"] = [enrich_work(e) for e in parsed["workHistory"]]
    out["education"] = [{**normalise_education(e), "period": finish_period(e["period"], "education", today)} for e in parsed["education"]]
    out["projects"] = [enrich_project(e, doc) for e in parsed["projects"]]
    out["awards"], out["certifications"] = split_awards_and_certs(parsed["awards"], parsed["certifications"])
    out["skills"] = build_skills(out)
    return out if keep_private else strip_private(out)
