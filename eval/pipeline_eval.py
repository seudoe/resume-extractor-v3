"""Stage 12 exit check: hallucination, schema validity, determinism, stage timing on the full pipeline.

    uv run python -m eval.pipeline_eval [--n 200]

Sample: all AAA resumes + a stratified LiveCareer sample. Hallucination is measured by the *independent*
metric in eval/metrics.py against PyMuPDF plain text + link annotations (not the pipeline's own text), with the
documented exemption for normalised values. Determinism: the same files are extracted in two fresh processes with
different PYTHONHASHSEEDs and the JSON compared byte for byte."""

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "eval"))

import pymupdf  # noqa: E402
import rx3  # noqa: E402,F401
from _resume_data_layout import GOLD_CATEGORY, categories, pdf_path, stems_in_category, text_path  # noqa: E402
from metrics import hallucination_rate, is_schema_valid  # noqa: E402
from perf import _percentile  # noqa: E402
from rx3.pipeline import extract  # noqa: E402


def sample(n: int) -> list[tuple[str, str]]:
    rng = random.Random(0)
    out = [(GOLD_CATEGORY, s) for s in stems_in_category(GOLD_CATEGORY)]
    cats = [c for c in categories() if c != GOLD_CATEGORY]
    per = max(1, n // len(cats))
    for c in cats:
        stems = stems_in_category(c)
        out += [(c, s) for s in rng.sample(stems, min(per, len(stems)))]
    return out


def independent_source(cat: str, stem: str) -> str:
    """Source text for the hallucination metric that does not go through the pipeline's layout/merge logic:
    PyMuPDF plain text + link-annotation targets (an annotation URL is legitimate output). Scanned PDFs (no text
    layer) fall back to the pypdf text in resume-data/TEXTs."""
    with pymupdf.open(pdf_path(cat, stem)) as pdf:
        text = "\n".join(p.get_text() for p in pdf)
        uris = "\n".join(l.get("uri", "") for p in pdf for l in p.get_links() if l.get("uri"))
    if len(text.strip()) < 200 and text_path(cat, stem).exists():
        text = text_path(cat, stem).read_text(encoding="utf-8", errors="ignore")
    return text + "\n" + uris


def digest(items: list[tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for cat, stem in items:
        out = extract(pdf_path(cat, stem).read_bytes(), stem + ".pdf", with_confidence=True)
        h.update(json.dumps(out, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--digest", help="internal: print the digest of 'cat/stem' items (JSON list) and exit")
    args = ap.parse_args()
    if args.digest:
        print(digest([tuple(x) for x in json.loads(args.digest)]))
        return

    items = sample(args.n)
    stage = defaultdict(list)
    halluc, valid, dropped, crashes, flagged = [], [], [], [], []
    by_set = defaultdict(list)
    for cat, stem in items:
        try:
            out = extract(pdf_path(cat, stem).read_bytes(), stem + ".pdf", debug=True)
        except Exception as e:  # noqa: BLE001
            crashes.append((cat, stem, repr(e)))
            continue
        dbg = out.pop("_debug")
        for k, v in dbg["timings_ms"].items():
            stage[k].append(v)
        dropped += [(cat, stem, d["path"], d["value"]) for d in dbg["dropped_ungrounded"]]
        ok, err = is_schema_valid(out)
        valid.append(ok)
        h = hallucination_rate(out, independent_source(cat, stem))
        halluc.append(h)
        by_set["AAA" if cat == GOLD_CATEGORY else "LiveCareer"].append(h["rate"])
        for ex in h["examples"]:
            flagged.append((cat, stem, ex))

    det_items = [list(x) for x in items[:: max(1, len(items) // 12)]][:12]
    digests = []
    for seed in ("0", "1"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([sys.executable, "-m", "eval.pipeline_eval", "--digest", json.dumps(det_items)], cwd=ROOT, env=env, capture_output=True, text=True)
        digests.append(r.stdout.strip() or r.stderr[-200:])
    deterministic = len(set(digests)) == 1 and len(digests[0]) == 64

    n_str = sum(h["n_checked"] for h in halluc)
    n_bad = sum(h["n_hallucinated"] for h in halluc)
    md = [f"# Stage 12 pipeline eval — {date.today().isoformat()}", "",
          f"{len(items)} resumes (AAA all + stratified LiveCareer), {len(crashes)} crashes.", "",
          f"- Schema validity: **{mean(valid):.1%}** ({sum(valid)}/{len(valid)})",
          f"- Hallucination (independent metric, derived values exempt): **{n_bad / max(n_str, 1):.2%}** "
          f"({n_bad}/{n_str} strings); per-resume mean AAA {mean(by_set['AAA']):.2%}, LiveCareer {mean(by_set['LiveCareer']):.2%}",
          f"- Strings dropped by the pipeline's own grounding: {len(dropped)}",
          f"- Determinism (2 processes, PYTHONHASHSEED 0 vs 1, {len(det_items)} files, byte-identical JSON): **{deterministic}**", "",
          "### Latency per stage (ms, warm process, this machine)", "", "| stage | p50 | p95 |", "|---|---|---|"]
    for k, v in stage.items():
        md.append(f"| {k} | {_percentile(v, 50):.1f} | {_percentile(v, 95):.1f} |")
    if crashes:
        md += ["", "### Crashes", ""] + [f"- {c}/{s}: {e}" for c, s, e in crashes[:10]]
    md += ["", "### Hallucination examples (independent metric)", ""] + [f"- {c}/{s}: {x[:110]!r}" for c, s, x in flagged[:25]]
    md += ["", "### Dropped by grounding (first 15)", ""] + [f"- {c}/{s} {p}: {v!r}" for c, s, p, v in dropped[:15]]
    path = ROOT / "reports" / f"pipeline_{date.today().isoformat()}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
