"""The one eval command (PROMPT.md §4.6):

    uv run python -m eval.run_eval --set gold --baseline v2 --compare last

Scores a baseline's pre-computed/produced output against data/gold/drafts/*.json
and writes reports/eval_<date>_<label>.{md,json}.

Today only `--baseline v2` exists (resume-extract's pre-computed outputs,
PROMPT.md §4.5 baseline #1). `--baseline v3` will call `rx3.pipeline.extract`
once it exists (Stage 12+).
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "types"))
sys.path.insert(0, str(ROOT / "eval"))

from mappings.ai_path import load_ai_path_baseline  # noqa: E402
from mappings.v2 import load_v2_baseline  # noqa: E402
from metrics import (  # noqa: E402
    hallucination_rate,
    is_schema_valid,
    score_entity_section,
    score_scalar_fields,
    skills_prf1,
)
from report import write_report  # noqa: E402

GOLD_DIR = ROOT / "data" / "gold"
V2_TESTED_JSONS = ROOT.parent / "resume-data" / "resume-extract-tested-jsons"
AI_PATH_OUTPUT = ROOT.parent / "mongo-runner" / "output.json"

ENTITY_SECTIONS = ["workHistory", "education", "projects", "certifications", "awards"]


def load_gold(include_scaffolds: bool = False) -> list[dict]:
    """By default, excludes status="scaffold" entries: those are empty
    placeholders waiting to be hand-labelled (PROMPT.md §4.1), not resumes
    that genuinely have zero fields. Scoring against them would silently
    tank every metric with fake zero-entity "gold" (caught during Stage 4
    build — see DECISIONS.md)."""
    gold = []
    for path in sorted((GOLD_DIR / "drafts").glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry.get("status") == "scaffold" and not include_scaffolds:
            continue
        gold.append(entry)
    return gold


def source_text_for(gold_entry: dict) -> str:
    raw_path = GOLD_DIR / "raw" / f"{gold_entry['id']}.txt"
    return raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""


def match_candidate(gold_entry: dict, candidates: dict[str, dict], baseline: str) -> dict | None:
    if baseline == "ai":
        name = ((gold_entry.get("parsed") or {}).get("metaDetails") or {}).get("name")
        return candidates.get((name or "").strip().lower())
    stem = Path(gold_entry["source_file"]).stem
    return candidates.get(stem)


def run(baseline: str) -> dict:
    all_gold = load_gold(include_scaffolds=True)
    gold_entries = [g for g in all_gold if g.get("status") != "scaffold"]
    n_scaffold = len(all_gold) - len(gold_entries)
    n_verified = sum(1 for g in gold_entries if g.get("verified_by"))

    if baseline == "v2":
        candidates = load_v2_baseline(V2_TESTED_JSONS)
    elif baseline == "ai":
        candidates = load_ai_path_baseline(AI_PATH_OUTPUT)
    else:
        raise SystemExit(f"unknown --baseline {baseline!r} (only 'v2'/'ai' exist before Stage 12)")

    scalar_totals: dict[str, list[bool]] = {}
    entity_totals: dict[str, list[dict]] = {s: [] for s in ENTITY_SECTIONS}
    skills_scores = []
    hallucination_scores = []
    schema_valid_flags = []
    per_file_mean_f1 = []
    n_scored = 0
    n_no_candidate = 0

    for gold_entry in gold_entries:
        candidate = match_candidate(gold_entry, candidates, baseline)
        source_text = source_text_for(gold_entry)

        if candidate is not None:
            valid, _err = is_schema_valid(candidate)
            schema_valid_flags.append(valid)
            if source_text:
                hallucination_scores.append(hallucination_rate(candidate, source_text)["rate"])

        gold_parsed = gold_entry.get("parsed")
        if candidate is None or gold_parsed is None:
            n_no_candidate += 1
            continue
        n_scored += 1

        scalars = score_scalar_fields(candidate, gold_parsed)
        for field, result in scalars.items():
            if result["applicable"]:
                scalar_totals.setdefault(field, []).append(result["correct"])

        file_f1s = []
        for section in ENTITY_SECTIONS:
            result = score_entity_section(candidate.get(section, []), gold_parsed.get(section, []), section)
            entity_totals[section].append(result)
            file_f1s.append(result["f1"])
        per_file_mean_f1.append({"id": gold_entry["id"], "mean_f1": mean(file_f1s) if file_f1s else 0.0})

        skills_scores.append(skills_prf1(candidate, gold_parsed))

    summary = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "label": f"baseline-{baseline}",
        "baseline": baseline,
        "n_gold_total": len(gold_entries),
        "n_gold_scaffold": n_scaffold,
        "n_gold_verified": n_verified,
        "n_scored": n_scored,
        "n_no_candidate": n_no_candidate,
        "scalar_fields": {
            field: {"accuracy": mean(vals) if vals else None, "n": len(vals)}
            for field, vals in scalar_totals.items()
        },
        "entity_sections": {
            section: {
                "precision": mean(r["precision"] for r in results) if results else 0.0,
                "recall": mean(r["recall"] for r in results) if results else 0.0,
                "f1": mean(r["f1"] for r in results) if results else 0.0,
                "omission_rate": mean(r["omission_rate"] for r in results) if results else 0.0,
            }
            for section, results in entity_totals.items()
        },
        "skills": {
            "precision": mean(s["precision"] for s in skills_scores) if skills_scores else 0.0,
            "recall": mean(s["recall"] for s in skills_scores) if skills_scores else 0.0,
            "f1": mean(s["f1"] for s in skills_scores) if skills_scores else 0.0,
        },
        "hallucination_rate": mean(hallucination_scores) if hallucination_scores else 0.0,
        "schema_validity": mean(1.0 if v else 0.0 for v in schema_valid_flags) if schema_valid_flags else 0.0,
        "crash_rate": n_no_candidate / len(gold_entries) if gold_entries else 0.0,
        "worst_files": sorted(per_file_mean_f1, key=lambda x: x["mean_f1"]),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="gold")
    parser.add_argument("--baseline", default="v2")
    parser.add_argument("--compare", default=None)
    args = parser.parse_args()

    summary = run(args.baseline)
    label = f"baseline-{args.baseline}"
    md_path, json_path = write_report(summary, label)
    print(f"Scored {summary['n_scored']}/{summary['n_gold_total']} gold files "
          f"({summary['n_no_candidate']} had no matching candidate).")
    print(f"Report written to:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
