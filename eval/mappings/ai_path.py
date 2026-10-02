"""Optional reference baseline (PROMPT.md §4.5 #2, Checkpoint 4C): existing
Gemini/GPT `parsedData` exported from MongoDB via ../mongo-runner/output.json.

Most records in that export are demo/seed accounts unrelated to our gold set
(see DECISIONS.md Stage 4) — only match by name against gold resumes we
actually have, never assume full coverage.
"""

import json
from pathlib import Path


def load_ai_path_baseline(output_json_path: Path) -> dict[str, dict]:
    """Returns {name_lower: parsedData} for every record that has one."""
    records = json.loads(Path(output_json_path).read_text(encoding="utf-8"))
    out = {}
    for rec in records:
        parsed = (rec.get("resume") or {}).get("parsedData")
        name = rec.get("name")
        if parsed and name:
            out[name.strip().lower()] = parsed
    return out


def match_by_name(gold_name: str, ai_candidates: dict[str, dict]) -> dict | None:
    return ai_candidates.get((gold_name or "").strip().lower())
