"""Render an eval run's results as reports/eval_<date>_<sha>.md + .json
(PROMPT.md §4.6)."""

import json
import subprocess
from datetime import date
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=REPORTS_DIR.parent
        )
        sha = out.stdout.strip()
        return sha if sha else "nocommit"
    except FileNotFoundError:
        return "nogit"


def report_paths(label: str) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"eval_{date.today().isoformat()}_{label}"
    return REPORTS_DIR / f"{stem}.md", REPORTS_DIR / f"{stem}.json"


def find_last_report(exclude_label: str | None = None) -> Path | None:
    candidates = sorted(REPORTS_DIR.glob("eval_*.json"))
    if exclude_label:
        candidates = [c for c in candidates if exclude_label not in c.name]
    return candidates[-1] if candidates else None


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render_markdown(summary: dict, label: str, compare: dict | None) -> str:
    lines = [f"# Eval report — {label} — {summary['generated_at']}", ""]
    lines.append(f"Gold set: {summary['n_gold_total']} drafted/verified files "
                 f"({summary['n_gold_verified']} verified, "
                 f"{summary['n_gold_total'] - summary['n_gold_verified']} draft/unverified), "
                 f"plus {summary.get('n_gold_scaffold', 0)} not yet hand-labelled (excluded from scoring).")
    lines.append(f"Candidate: {summary['n_scored']}/{summary['n_gold_total']} gold files had a matching "
                 f"candidate prediction.")
    if summary["n_gold_verified"] == 0:
        lines.append("")
        lines.append("> **All gold used here is unverified draft** (Checkpoint 4B hasn't happened yet). "
                      "Per PROMPT.md §1.5/§4.1, these numbers are NOT to be treated as reported accuracy "
                      "until the user verifies the gold labels.")
    lines.append("")

    lines.append("## Scalar fields")
    lines.append("")
    lines.append("| Field | Accuracy | N applicable |")
    lines.append("|---|---|---|")
    for field, stats in summary["scalar_fields"].items():
        lines.append(f"| {field} | {_fmt_pct(stats['accuracy'])} | {stats['n']} |")
    lines.append("")

    lines.append("## Entity sections")
    lines.append("")
    lines.append("| Section | Precision | Recall | F1 | Omission rate |")
    lines.append("|---|---|---|---|---|")
    for section, stats in summary["entity_sections"].items():
        lines.append(
            f"| {section} | {_fmt_pct(stats['precision'])} | {_fmt_pct(stats['recall'])} | "
            f"{stats['f1']:.3f} | {_fmt_pct(stats['omission_rate'])} |"
        )
    lines.append("")

    lines.append("## Skills")
    lines.append("")
    s = summary["skills"]
    lines.append(f"Precision {_fmt_pct(s['precision'])}, recall {_fmt_pct(s['recall'])}, F1 {s['f1']:.3f}")
    lines.append("")

    lines.append("## Hallucination / schema / determinism")
    lines.append("")
    lines.append(f"- Hallucination rate (mean over scored files): {_fmt_pct(summary['hallucination_rate'])}")
    lines.append(f"- Schema validity: {_fmt_pct(summary['schema_validity'])}")
    lines.append(f"- Crash rate: {_fmt_pct(summary['crash_rate'])}")
    lines.append("")

    if summary["worst_files"]:
        lines.append("## Worst files (lowest mean entity F1)")
        lines.append("")
        for w in summary["worst_files"][:10]:
            lines.append(f"- `{w['id']}`: mean entity F1 {w['mean_f1']:.3f}")
        lines.append("")

    if compare:
        lines.append(f"## Delta vs {compare['label']}")
        lines.append("")
        for section in summary["entity_sections"]:
            prev = compare["entity_sections"].get(section, {}).get("f1")
            cur = summary["entity_sections"][section]["f1"]
            if prev is not None:
                lines.append(f"- {section} F1: {prev:.3f} -> {cur:.3f} ({cur - prev:+.3f})")
        lines.append("")

    return "\n".join(lines)


def write_report(summary: dict, label: str) -> tuple[Path, Path]:
    md_path, json_path = report_paths(label)
    prev_path = find_last_report(exclude_label=label)
    compare = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path else None
    md_path.write_text(render_markdown(summary, label, compare), encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return md_path, json_path
