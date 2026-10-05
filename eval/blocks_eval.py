"""Block-level field accuracy of GLiNER zero-shot vs the LoRA adapter on held-out data (PROMPT.md §5 Stage 10.2).

    uv run python -m eval.blocks_eval [--adapter models/gliner-lora/best] [--split test_synth] [--device cuda]

`test_synth` = synthetic template families never seen in training (jake, table_docx, banner); `dev_lc` = LiveCareer blocks from
resumes disjoint from the eval pool. For every example the model reads the same block text the pipeline would send and the
prediction is compared with the label string (exact match after whitespace/case folding). Reports precision / recall / F1 per
field at several confidence cut-offs, for the zero-shot model and, if given, the adapter."""

import argparse
import json
import sys
import warnings
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

from rx3.fields.gliner import FIELD_MAP, MODEL_ID, SCHEMAS, THRESHOLD  # noqa: E402

STRUCT_TO_SECTION = {"work": "workHistory", "edu": "education"}
GLINER_FIELDS = {sec: [gf for _, gf in FIELD_MAP[sec]] for sec in SCHEMAS}


def fold(s) -> str:
    return " ".join(str(s or "").lower().split())


def predict(model, rows: list[dict]) -> list[dict]:
    """Per row: {field: (text, confidence)} for the best prediction of every field."""
    by_sec: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by_sec[STRUCT_TO_SECTION[next(iter(r["output"]["json_structures"][0]))]].append(i)
    out: list[dict] = [{} for _ in rows]
    for sec, idx in by_sec.items():
        key = next(iter(SCHEMAS[sec]))
        res = model.batch_extract_json([rows[i]["input"] for i in idx], SCHEMAS[sec], batch_size=16, threshold=THRESHOLD,
                                       include_confidence=True, include_spans=True)
        for i, r in zip(idx, res):
            rec = (r.get(key) or [{}])[0]
            for f in GLINER_FIELDS[sec]:
                v = rec.get(f)
                v = v[0] if isinstance(v, list) and v else v
                if isinstance(v, dict) and v.get("text"):
                    out[i][f] = (v["text"], float(v.get("confidence", 0.0)))
    return out


def score(rows, preds, cut: float) -> dict[str, dict]:
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    for r, p in zip(rows, preds):
        struct = r["output"]["json_structures"][0]
        gold = next(iter(struct.values()))
        sec = STRUCT_TO_SECTION[next(iter(struct))]
        for f in GLINER_FIELDS[sec]:
            g = fold(gold.get(f))
            pv = fold(p[f][0]) if f in p and p[f][1] >= cut else ""
            name = f"{sec}.{f}"
            if g and pv == g:
                tp[name] += 1
            else:
                fp[name] += bool(pv)
                fn[name] += bool(g)
    return {n: {"p": tp[n] / (tp[n] + fp[n]) if tp[n] + fp[n] else 0.0, "r": tp[n] / (tp[n] + fn[n]) if tp[n] + fn[n] else 0.0, "n": tp[n] + fn[n]}
            for n in sorted(set(tp) | set(fp) | set(fn))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter")
    ap.add_argument("--split", default="test_synth")
    ap.add_argument("--device", default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    from gliner2 import AutoExtractor

    rows = [json.loads(l) for l in (ROOT / "data" / "train" / f"{args.split}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        rows = rows[:: max(1, len(rows) // args.limit)][: args.limit]
    kw = {"map_location": args.device} if args.device else {}
    md = [f"# Block-level field accuracy — {args.split} ({len(rows)} blocks) — {date.today().isoformat()}", ""]
    for label, adapter in (("zero-shot", None), ("lora", args.adapter)):
        if label == "lora" and not adapter:
            continue
        model = AutoExtractor.from_pretrained(MODEL_ID, **kw)
        if adapter:
            model.load_adapter(adapter)
        preds = predict(model, rows)
        for cut in (0.5, 0.9):
            md += [f"## {label} @ confidence >= {cut}", "", "| field | n | precision | recall | F1 |", "|---|---|---|---|---|"]
            for name, m in score(rows, preds, cut).items():
                f1 = 2 * m["p"] * m["r"] / (m["p"] + m["r"]) if m["p"] + m["r"] else 0.0
                md.append(f"| {name} | {m['n']} | {m['p']:.1%} | {m['r']:.1%} | {f1:.1%} |")
            md.append("")
        print(f"done {label}", flush=True)
    path = ROOT / "reports" / f"blocks_{args.split}_{date.today().isoformat()}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
