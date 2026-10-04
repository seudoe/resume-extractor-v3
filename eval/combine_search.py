"""Choose, per field, rules vs GLiNER vs hybrid (PROMPT.md §5 Stage 10: "combine per section by eval results").

    uv run python -m eval.combine_search [--n 100]

Runs rules, pure GLiNER and hybrid at several confidence cut-offs on the same LiveCareer subset + AAA, then prints the
metric table per field (GLiNER outputs are cached in data/cache/gliner_cache.json, so reruns are cheap).
Metrics: LiveCareer weak labels (work.title entry recall, edu.school, edu.degree) and agreement with the LLM JSONs on
AAA (company, title, location, institution, degree type, course). The AAA reference is LLM output, not gold."""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
import fields_eval as fe  # noqa: E402
from rx3.fields.gliner import GlinerRefiner  # noqa: E402

CONFIGS = [("rules", None), ("gliner", 0.0), ("hybrid", 0.6), ("hybrid", 0.8), ("hybrid", 0.9), ("combined", None)]
WANT_LC = ["work.entry_recall", "edu.school", "edu.degree", "edu.entry_recall"]
WANT_AAA = ["workHistory.company", "workHistory.title", "workHistory.location", "education.institution",
            "education.field.type", "education.field.course"]


def table(md: list[str]) -> dict[str, float]:
    out = {}
    for line in md:
        m = re.match(r"\| ([\w.]+) \| ([\d.]+)%", line)
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    fe.N_LIVECAREER = args.n
    rows = {}
    for strat, conf in CONFIGS:
        fe._REFINERS.clear()
        if strat != "rules":
            fe._REFINERS[strat] = GlinerRefiner(strat, default_conf=conf or 0.0)
        # note: every config gets a fresh refiner so no state leaks between rows
        name = f"{strat}+norm"
        label = strat if conf is None else f"{strat}@{conf}" if strat == "hybrid" else strat
        rows[label] = {**table(fe.livecareer(name)), **table(fe.aaa_agreement(name))}
        print("done", label, flush=True)
    keys = WANT_LC + WANT_AAA
    md = ["| config | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
    for label, r in rows.items():
        md.append(f"| {label} | " + " | ".join(f"{r.get(k, float('nan')):.1f}" for k in keys) + " |")
    out = ROOT / "reports" / "combine_search.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
