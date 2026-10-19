"""LLM JSONs (resume-data/JSONs) -> GLiNER2 training examples for LiveCareer resumes (RETRAINING.md plan item 5).

    from llm_json_to_gliner import llm_resumes, llm_examples

A field becomes a label only if the LLM value occurs verbatim (whitespace/case tolerant) in the block text the model will see, so invented
or normalised values are dropped; LiveCareer placeholders ("Company Name", "City, State") count as absent. Blocks whose title/institution
is not recoverable or that match two JSON entries equally are skipped (same rule as the synthetic data). Resumes already in the HTML-tag
pools (aligned.jsonl = eval, aligned_train.jsonl = train/dev_lc) and the AAA gold category are never used here.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from _resume_data_layout import RESUME_DATA_ROOT, GOLD_CATEGORY, categories, json_path, pdf_path, stems_in_category  # noqa: E402

PLACEHOLDERS = {"company name", "city", "state", "city, state", "name", "school name", "institution name", "country", "zip code", "n/a", "none"}


def _s(v) -> str:
    v = v.strip() if isinstance(v, str) else ""
    return "" if v.lower() in PLACEHOLDERS else v


def _truth(j: dict) -> dict | None:
    if not isinstance(j, dict):
        return None
    work = [{"title": _s(w.get("title")), "company": _s(w.get("company")), "location": _s(w.get("location"))}
            for w in j.get("workHistory") or [] if isinstance(w, dict)]
    edu = []
    for e in j.get("education") or []:
        if isinstance(e, dict):
            f = e.get("field") if isinstance(e.get("field"), dict) else {}
            edu.append({"institution": _s(e.get("institution")), "degree": _s(f.get("type")), "course": _s(f.get("course"))})
    return {"work": work, "education": edu}


def llm_resumes() -> list[tuple[str, str]]:
    """(category, stem) of LiveCareer resumes with a PDF and a JSON that are in neither HTML-tag pool."""
    used = set()
    for name in ("aligned.jsonl", "aligned_train.jsonl"):
        p = ROOT / "data" / "livecareer" / name
        if p.exists():
            used |= {(r["category"], r["id"]) for r in map(json.loads, p.read_text(encoding="utf-8").splitlines())}
    return [(c, s) for c in categories() if c != GOLD_CATEGORY for s in stems_in_category(c)
            if (c, s) not in used and json_path(c, s).exists()]


def llm_examples(category: str, stem: str, capture, synth_examples) -> list[dict]:
    try:
        truth = _truth(json.loads(json_path(category, stem).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return []
    if not truth:
        return []
    return synth_examples(truth, capture(pdf_path(category, stem)))
