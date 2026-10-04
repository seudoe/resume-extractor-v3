"""Calibrate Stage 12 field confidences on LiveCareer weak labels.

    uv run python tools/livecareer_align.py --n 500     # more labelled resumes first
    uv run python -m eval.calibrate_confidence

Even resume ids fit the bucket -> accuracy table, odd ids report how well it holds out (mean predicted
confidence vs observed accuracy per field, plus ECE). The shipped `_calibration.json` is refit on all resumes.
Labels are weak (HTML tags of one template family), so this calibrates against that source, not real-world data."""

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "eval"))

import rx3  # noqa: E402,F401
from _resume_data_layout import pdf_path  # noqa: E402
from fields_eval import ALIGNED, SIM, _jw, _label_date, _ym  # noqa: E402
from matching import match_entities  # noqa: E402
from rx3.normalise.education import canonical_degree  # noqa: E402
from rx3.pipeline import extract  # noqa: E402
from rx3.validate.confidence import bucket  # noqa: E402

OUT = ROOT / "src" / "rx3" / "validate" / "_calibration.json"


def observations() -> list[tuple[int, str, str, bool]]:
    """(resume id, field, bucket, correct)."""
    obs = []
    for line in ALIGNED.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        pdf = pdf_path(rec["category"], rec["id"])
        pred = extract(pdf.read_bytes(), pdf.name)
        rid = int(rec["id"])
        gw = [{k: v["value"] for k, v in e["fields"].items()} for e in rec["entries"] if e["section"] == "workHistory"]
        ge = [{k: v["value"] for k, v in e["fields"].items()} for e in rec["entries"] if e["section"] == "education" and (e["fields"].get("degree") or e["fields"].get("school"))]
        m, _, _ = match_entities(pred["workHistory"], [{"title": g.get("title", "")} for g in gw], lambda e: e.get("title", ""))
        match = dict(m)
        for i, p in enumerate(pred["workHistory"]):
            if p["title"]:
                ok = i in match and _jw(p["title"], gw[match[i]].get("title", "")) >= SIM
                obs.append((rid, "work.title", bucket("work.title", p), ok))
            g = gw[match[i]] if i in match else None
            if g and g.get("start") and g.get("end"):
                cur = g["end"].lower() in ("current", "present", "now")
                ok = _ym(p["period"]["start"]) == _label_date(g["start"]) and (p["period"]["isCurrent"] if cur else _ym(p["period"]["end"]) == _label_date(g["end"]))
                obs.append((rid, "period", bucket("period", p), ok))
        m, _, _ = match_entities([{"k": f"{e['field']['type']} {e['field']['course']}"} for e in pred["education"]],
                                 [{"k": f"{g.get('degree', '')} {g.get('program', '') or g.get('field', '')}"} for g in ge], lambda e: e["k"])
        for i, j in m:
            p, g = pred["education"][i], ge[j]
            if g.get("school") and p["institution"]:
                obs.append((rid, "edu.institution", bucket("edu.institution", p), _jw(p["institution"], g["school"]) >= 0.85))
            if g.get("degree") and p["field"]["type"]:
                obs.append((rid, "edu.degree", bucket("edu.degree", p), _jw(p["field"]["type"], canonical_degree(g["degree"])) >= 0.85))
    return obs


def table(obs) -> dict:
    agg = defaultdict(lambda: [0, 0])
    for _, f, b, ok in obs:
        agg[(f, b)][0] += ok
        agg[(f, b)][1] += 1
    out: dict = defaultdict(dict)
    for (f, b), (k, n) in agg.items():
        out[f][b] = {"acc": (k + 1) / (n + 2), "n": n}  # Laplace smoothing keeps small buckets off 0/1
    return out


def main() -> None:
    obs = observations()
    fit = table([o for o in obs if o[0] % 2 == 0])
    held = [o for o in obs if o[0] % 2 == 1]
    md = [f"# Confidence calibration — {date.today().isoformat()}", "",
          f"{len(obs)} observations ({len(held)} held out, odd ids). Fit on even ids; labels are weak (LiveCareer HTML).", "",
          "| field | n | mean confidence | observed accuracy | abs gap (ECE) |", "|---|---|---|---|---|"]
    by_field = defaultdict(list)
    for _, f, b, ok in held:
        by_field[f].append((fit.get(f, {}).get(b, {"acc": 0.5})["acc"], ok, b))
    for f, rows in sorted(by_field.items()):
        conf = sum(r[0] for r in rows) / len(rows)
        acc = sum(r[1] for r in rows) / len(rows)
        buckets = defaultdict(list)
        for c, ok, b in rows:
            buckets[b].append((c, ok))
        ece = sum(len(v) * abs(sum(c for c, _ in v) / len(v) - sum(ok for _, ok in v) / len(v)) for v in buckets.values()) / len(rows)
        md.append(f"| {f} | {len(rows)} | {conf:.3f} | {acc:.3f} | {ece:.3f} |")
    md += ["", "### Buckets (fit on all)", ""]
    final = table(obs)
    for f, bs in sorted(final.items()):
        for b, v in sorted(bs.items()):
            md.append(f"- {f} `{b}`: acc {v['acc']:.3f} (n={v['n']})")
    OUT.write_text(json.dumps(final, indent=1, sort_keys=True), encoding="utf-8")
    path = ROOT / "reports" / f"confidence_calibration_{date.today().isoformat()}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
