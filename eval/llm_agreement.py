"""How closely does Groq-with-layout-text agree with Gemini-reading-the-PDF?

Calibration for the LLM-labelled benchmark (resume-data/process_resumes.py):
before running Groq over thousands of PDFs, run it on AAA with
`--only GROQ --category AAA --out-root calibration/groq-layout`, then:

    uv run python -m eval.llm_agreement

This is AGREEMENT between two LLM outputs (Gemini = reference side), not
accuracy: neither is gold. Pair it with `python -m eval.header_eval` (Groq
column vs hand-labelled header gold) for ground-truth numbers on the header
fields.
"""

import sys
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "types"))

from mappings.llm_json import CALIBRATION_GROQ_LAYOUT, load_llm_baseline  # noqa: E402
from metrics import score_entity_section, score_scalar_fields, skills_prf1  # noqa: E402

SECTIONS = ["workHistory", "education", "projects", "certifications", "awards"]


def main() -> None:
    gemini = load_llm_baseline()
    groq = load_llm_baseline(root=CALIBRATION_GROQ_LAYOUT)
    stems = sorted(set(gemini) & set(groq))
    if not stems:
        raise SystemExit(f"no overlap: run process_resumes.py --only GROQ --category AAA --out-root calibration/groq-layout first "
                         f"({len(gemini)} Gemini JSONs, {len(groq)} Groq JSONs found)")

    scalars: dict[str, list[bool]] = {}
    ent: dict[str, list[dict]] = {s: [] for s in SECTIONS}
    skills = []
    for stem in stems:
        g, r = gemini[stem], groq[stem]  # r scored against g
        for field, res in score_scalar_fields(r, g).items():
            if res["applicable"]:
                scalars.setdefault(field, []).append(res["correct"])
        for s in SECTIONS:
            ent[s].append(score_entity_section(r.get(s, []), g.get(s, []), s))
        skills.append(skills_prf1(r, g)["f1"])

    md = [f"# Groq+layout vs Gemini+PDF agreement — {date.today().isoformat()}", "",
          f"{len(stems)} AAA resumes. Gemini = reference side; **agreement, not accuracy** (neither is gold).", "",
          "| Field | Agreement | N |", "|---|---|---|"]
    md += [f"| {f} | {mean(v):.1%} | {len(v)} |" for f, v in scalars.items()]
    md += ["", "| Section | Entity F1 (Groq vs Gemini) | Omission |", "|---|---|---|"]
    md += [f"| {s} | {mean(r['f1'] for r in rs):.3f} | {mean(r['omission_rate'] for r in rs):.1%} |" for s, rs in ent.items()]
    md += ["", f"Skills F1: {mean(skills):.3f}"]
    out = ROOT / "reports" / f"llm_agreement_{date.today().isoformat()}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
