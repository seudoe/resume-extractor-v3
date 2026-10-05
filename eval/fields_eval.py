"""Stage 10 field-level eval for the rules baseline (and later GLiNER).

    uv run python -m eval.fields_eval [--extractor rules] [--n 0]

Two proxies, because only 3 gold resumes are hand-drafted so far:
  A. LiveCareer (held-out; weak labels from HTML tags, aligned by
     tools/livecareer_align.py -> data/livecareer/aligned.jsonl). Work: title,
     start, end; education: degree, programline/field, school, graduation year.
     Company/city are anonymised in the source, so they carry no label.
  B. AAA agreement with the Gemini/Groq-labelled JSONs (LLM output, NOT gold):
     entity F1 + sub-field accuracy via eval.metrics.score_entity_section.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "eval"))

import rx3  # noqa: E402,F401
from _resume_data_layout import GOLD_CATEGORY, RESUME_DATA_ROOT, json_path, pdf_path, stems_in_category  # noqa: E402
from matching import match_entities  # noqa: E402
from metrics import score_entity_section, skills_prf1  # noqa: E402
from rapidfuzz.distance import JaroWinkler  # noqa: E402
from rx3.fields.rules import extract_rules  # noqa: E402
from rx3.fields.rules.dates import find_range, to_iso  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from rx3.normalise import normalise  # noqa: E402
from rx3.normalise.education import canonical_degree  # noqa: E402
from rx3.normalise.skills import build_skills  # noqa: E402

ALIGNED = ROOT / "data" / "livecareer" / "aligned.jsonl"
SIM = 0.9
N_LIVECAREER = 0  # 0 = every aligned resume; set by --n


def _jw(a: str, b: str) -> float:
    return JaroWinkler.similarity((a or "").lower().strip(), (b or "").lower().strip())


def _ym(s: str | None) -> str:
    return (s or "")[:7]


def _label_date(v: str) -> str:
    f = find_range(v)
    return _ym(to_iso(v) or (f.end or f.start if f else ""))


_REFINERS: dict = {}


def refiner_for(strategy: str):
    if strategy not in _REFINERS:
        if strategy.startswith("lora"):  # lora[@cut-off]: fine-tuned adapter, override at confidence >= cut-off (default 0.5)
            from rx3.fields.gliner import GlinerRefiner

            cut = float(strategy.split("@")[1]) if "@" in strategy else 0.5
            _REFINERS[strategy] = GlinerRefiner("hybrid", default_conf=cut, adapter=str(ROOT / "models" / "gliner-lora" / "best"), tag="lora")
        elif strategy.startswith("slm"):
            from rx3.fields.slm import SlmRefiner

            _REFINERS[strategy] = SlmRefiner(strategy)
        else:
            from rx3.fields.gliner import GlinerRefiner

            _REFINERS[strategy] = GlinerRefiner(strategy)
    return _REFINERS[strategy]


def run_extractor(name: str, pdf: Path) -> dict:
    """name = <rules|gliner|hybrid>[+norm]: rules entries, optionally GLiNER-refined, optionally Stage 11 normalised."""
    base, _, norm = name.partition("+")
    if base not in ("rules", "gliner", "hybrid", "combined", "slm06", "slm17") and not base.startswith("lora"):
        raise SystemExit(f"unknown extractor {name!r}")
    doc = analyze_layout(ingest_pdf(pdf.read_bytes()))
    raw = extract_rules(doc, pdf.name, refiner=None if base == "rules" else refiner_for(base))
    return normalise(raw, doc) if norm else raw


def livecareer(extractor: str) -> list[str]:
    tallies: dict[str, list[bool]] = defaultdict(list)
    n_pred = n_gold = n_match = 0
    lines = ALIGNED.read_text(encoding="utf-8").splitlines()
    if N_LIVECAREER:  # evenly spaced subset (aligned.jsonl is category-ordered)
        lines = lines[:: max(1, len(lines) // N_LIVECAREER)][:N_LIVECAREER]
    for line in lines:
        rec = json.loads(line)
        pdf = pdf_path(rec["category"], rec["id"])
        pred = run_extractor(extractor, pdf)
        gold = {"workHistory": [], "education": []}
        for e in rec["entries"]:
            f = {k: v["value"] for k, v in e["fields"].items()}
            if e["section"] == "workHistory" and f.get("title"):
                gold["workHistory"].append(f)
            elif e["section"] == "education" and (f.get("degree") or f.get("school")):
                gold["education"].append(f)
        # work: key = title
        m, up, ug = match_entities(pred["workHistory"], gold["workHistory"], lambda e: e.get("title", ""))
        n_pred += len(pred["workHistory"]); n_gold += len(gold["workHistory"])
        hits = [(i, j) for i, j in m if _jw(pred["workHistory"][i]["title"], gold["workHistory"][j]["title"]) >= SIM]
        n_match += len(hits)
        tallies["work.entry_recall"] += [True] * len(hits) + [False] * (len(gold["workHistory"]) - len(hits))
        for i, j in hits:
            p, g = pred["workHistory"][i], gold["workHistory"][j]
            if g.get("start"):
                tallies["work.start"].append(_ym(p["period"]["start"]) == _label_date(g["start"]))
            if g.get("end"):
                cur = g["end"].lower() in ("current", "present", "now")
                tallies["work.end"].append(p["period"]["isCurrent"] if cur else _ym(p["period"]["end"]) == _label_date(g["end"]))
        # education: key = degree text, school/year as sub-fields
        m, up, ug = match_entities(
            [{"k": f"{e['field']['type']} {e['field']['course']}"} for e in pred["education"]],
            [{"k": f"{g.get('degree', '')} {g.get('program', '') or g.get('field', '')}"} for g in gold["education"]],
            lambda e: e["k"])
        tallies["edu.entry_recall"] += [True] * len(m) + [False] * len(ug)
        for i, j in m:
            p, g = pred["education"][i], gold["education"][j]
            if g.get("school"):
                tallies["edu.school"].append(_jw(p["institution"], g["school"]) >= 0.85)
            if g.get("degree"):
                tallies["edu.degree"].append(_jw(p["field"]["type"], canonical_degree(g["degree"])) >= 0.85)  # both sides canonical
            if g.get("gradyear"):
                tallies["edu.year"].append(_ym(p["period"]["end"]) == _label_date(g["gradyear"]))
    md = ["| metric | accuracy | n |", "|---|---|---|"]
    for k, v in sorted(tallies.items()):
        md.append(f"| {k} | {mean(v):.1%} | {len(v)} |")
    md.append(f"\nwork entries predicted {n_pred} vs labelled {n_gold} (title-correct matches {n_match})")
    return md


def aaa_agreement(extractor: str) -> list[str]:
    sections = ["workHistory", "education", "projects", "certifications", "awards"]
    res = defaultdict(list)
    sub = defaultdict(lambda: defaultdict(list))
    n = 0
    for stem in stems_in_category(GOLD_CATEGORY)[: int(os.environ.get("RX3_EVAL_AAA_LIMIT", "0")) or None]:
        jp = json_path(GOLD_CATEGORY, stem)
        if not jp.exists():
            continue
        ref = json.loads(jp.read_text(encoding="utf-8"))
        if "+norm" in extractor:  # LLM wrote "B.Tech"; compare canonical degree names on both sides
            for e in ref.get("education", []):
                e["field"]["type"] = canonical_degree(e["field"].get("type", ""))
        pred = run_extractor(extractor, pdf_path(GOLD_CATEGORY, stem))
        n += 1
        for s in sections:
            r = score_entity_section(pred.get(s, []), ref.get(s, []), s)
            res[s].append((r["precision"], r["recall"], r["f1"]))
            for k, v in r["subfield_accuracy"].items():
                sub[s][k].append(v)
    md = [f"{n} AAA resumes vs LLM JSON (reference is LLM output, not gold)", "",
          "| section | P | R | F1 |", "|---|---|---|---|"]
    for s in sections:
        if res[s]:
            md.append(f"| {s} | " + " | ".join(f"{mean(x[i] for x in res[s]):.1%}" for i in range(3)) + " |")
    md += ["", "| sub-field | acc |", "|---|---|"]
    for s in sections:
        for k, v in sub[s].items():
            md.append(f"| {s}.{k} | {mean(v):.1%} |")
    return md


def skills_eval(extractor: str) -> list[str]:
    """Skills P/R/F1 vs the LLM JSONs (names only), with and without bullet-mention discovery."""
    rows = {"listed + tech lines": [], "+ bullet mentions": []}
    for stem in stems_in_category(GOLD_CATEGORY):
        jp = json_path(GOLD_CATEGORY, stem)
        if not jp.exists():
            continue
        ref = json.loads(jp.read_text(encoding="utf-8"))
        doc = analyze_layout(ingest_pdf(pdf_path(GOLD_CATEGORY, stem).read_bytes()))
        raw = extract_rules(doc, stem + ".pdf")
        norm = normalise(raw, doc, keep_private=True)
        for label, discover in (("listed + tech lines", False), ("+ bullet mentions", True)):
            rows[label].append(skills_prf1({"skills": build_skills(norm, discover_in_bullets=discover)}, ref))
    md = ["| variant | P | R | F1 |", "|---|---|---|---|"]
    for label, r in rows.items():
        md.append(f"| {label} | " + " | ".join(f"{mean(x[k] for x in r):.1%}" for k in ("precision", "recall", "f1")) + " |")
    return md


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", default="rules")
    ap.add_argument("--n", type=int, default=0, help="LiveCareer resumes to score (evenly spaced); 0 = all aligned")
    args = ap.parse_args()
    global N_LIVECAREER
    N_LIVECAREER = args.n
    out = [f"# Stage 10 field eval — {args.extractor} — {date.today().isoformat()}", "",
           "## A. LiveCareer (weak HTML labels, held-out)", ""] + livecareer(args.extractor)
    out += ["", "## B. AAA agreement with LLM JSONs", ""] + aaa_agreement(args.extractor)
    if args.extractor == "rules+norm":
        out += ["", "## C. Skills names vs LLM JSONs (AAA)", ""] + skills_eval(args.extractor)
    path = ROOT / "reports" / f"fields_{args.extractor}_n{args.n}_{date.today().isoformat()}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
