"""Build GLiNER2 fine-tuning data from entry blocks (PROMPT.md §5 Stage 10.1).

    uv run python tools/build_gliner_data.py [--max-synth 8000] [--max-lc 4000]

Input blocks are exactly what inference sees: the rules stage's entry head lines through `block_text` (cells joined with
' | ', LiveCareer placeholders removed). Labels:
  * synthetic PDFs (tools/synth): the printed ground truth, matched to the block by which field values occur in it;
  * LiveCareer (data/livecareer/aligned_train.jsonl, disjoint from the eval pool aligned.jsonl): title / school /
    degree / program from the HTML tags, matched through the aligned line ids. Company and city are anonymised in the
    source, so those fields are simply absent from LiveCareer blocks (the cleaned text has no company either).
Only values found verbatim in the block text become labels (GLiNER trains on spans). Splits: synthetic by *family*
(train / dev / test families from tools/synth/families.py); gold-real (AAA) is never read here.
Outputs data/train/{train,dev,test_synth,dev_lc}.jsonl in GLiNER2's `json_structures` format."""

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401
from _resume_data_layout import pdf_path  # noqa: E402
from rx3.fields.gliner import SCHEMAS, block_text  # noqa: E402
from rx3.fields.rules import extract_rules  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from synth.families import DEV_FAMILIES, EXTRA_FAMILIES, TEST_FAMILIES, TRAIN_FAMILIES  # noqa: E402

OUT = ROOT / "data" / "train"
STRUCT = {"workHistory": "work", "education": "edu"}


def descriptions(section: str) -> dict:
    name = STRUCT[section]
    return {name: {f.split("::")[0]: f.split("::")[2] for f in SCHEMAS[section][name]}}


def locate(value: str, text: str) -> str | None:
    """The exact substring of `text` that spells `value` (whitespace / case tolerant), else None."""
    value = (value or "").strip()
    if not value:
        return None
    i = text.find(value)
    if i >= 0:
        return text[i : i + len(value)]
    m = re.search(r"\s+".join(re.escape(w) for w in value.split()), text, re.I)
    return m.group(0) if m else None


def capture(pdf: Path) -> list[tuple[str, str]]:
    """[(section, block text)] for every work / education entry the rules stage finds."""
    blocks: list[tuple[str, str]] = []

    def cap(section, entries, dicts):
        if section in STRUCT:
            blocks.extend((section, block_text(e)[0]) for e in entries)
        return dicts

    extract_rules(analyze_layout(ingest_pdf(pdf.read_bytes())), refiner=cap)
    return [(s, t) for s, t in blocks if t]


def record(section: str, text: str, fields: dict) -> dict:
    return {"input": text, "output": {"json_structures": [{STRUCT[section]: {k: v for k, v in fields.items() if v}}],
                                      "json_descriptions": descriptions(section)}}


def synth_examples(truth: dict, blocks) -> list[dict]:
    out = []
    for section, text in blocks:
        if section == "workHistory":
            cands = [(sum(1 for k in ("title", "company") if locate(g[k], text)), g) for g in truth["work"]]
            keys = {"company": "company", "title": "title", "location": "location"}
        else:
            cands = [(sum(1 for k in ("institution", "degree") if locate(g[k], text)), g) for g in truth["education"]]
            keys = {"institution": "institution", "degree": "degree", "field_of_study": "course"}
        cands = [c for c in cands if c[0] > 0]
        if not cands or sum(1 for c in cands if c[0] == max(x[0] for x in cands)) > 1:
            continue  # nothing matches, or two truth entries match equally (ambiguous): skip
        g = max(cands, key=lambda c: c[0])[1]
        fields = {f: locate(g[k], text) for f, k in keys.items()}
        if any(g[k] and not fields[f] and k in ("title", "company", "institution", "degree") for f, k in keys.items()):
            continue  # a key field is printed but not recoverable verbatim from the block: don't teach a wrong "absent"
        out.append(record(section, text, fields))
    return out


def lc_examples(rec: dict, pdf: Path) -> list[dict]:
    """LiveCareer entries -> examples, matching blocks to HTML entries through the aligned line ids of their key fields."""
    doc = analyze_layout(ingest_pdf(pdf.read_bytes()))
    got: list[dict] = []

    def cap(section, entries, dicts):
        if section not in STRUCT:
            return dicts
        gold = [e for e in rec["entries"] if e["section"] == section]
        for e in entries:
            text, starts = block_text(e)
            ids = {lid for _, lid in starts}
            hit = next((g for g in gold if any(f.get("line_id") in ids for k, f in g["fields"].items()
                                               if k in (("title",) if section == "workHistory" else ("school", "degree")))), None)
            if not text or not hit:
                continue
            f = {k: v["value"] for k, v in hit["fields"].items()}
            if section == "workHistory":
                fields = {"title": locate(f.get("title", ""), text)}
                if f.get("title") and not fields["title"]:
                    continue
            else:
                fields = {"institution": locate(f.get("school", ""), text), "degree": locate(f.get("degree", ""), text),
                          "field_of_study": locate(f.get("program", "") or f.get("field", ""), text)}
                if any(len(v or "") > 80 for v in fields.values()) or not any(fields.values()):
                    continue  # LiveCareer edu tags are noisy (whole paragraphs); keep short, clean spans only
            got.append(record(section, text, fields))
        return dicts

    extract_rules(doc, refiner=cap)
    return got


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-synth", type=int, default=8000)
    ap.add_argument("--max-lc", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--include-extra", action="store_true", help="also train on the tagline-style families (did not help; see families.py)")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    sets: dict[str, list[dict]] = {"train": [], "dev": [], "test_synth": [], "dev_lc": []}

    n_pdf = Counter()
    for fam_dir in sorted((ROOT / "data" / "synthetic").glob("*/")):
        if not fam_dir.is_dir():
            continue
        fam = fam_dir.name
        target = "train" if fam in TRAIN_FAMILIES or (args.include_extra and fam in EXTRA_FAMILIES) else "dev" if fam in DEV_FAMILIES else "test_synth" if fam in TEST_FAMILIES else None
        if target is None:
            continue  # extra families are rendered but not used unless --include-extra
        for pdf in sorted(fam_dir.glob("*.pdf")):
            truth = json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))
            sets[target] += synth_examples(truth, capture(pdf))
            n_pdf[fam] += 1

    lc_path = ROOT / "data" / "livecareer" / "aligned_train.jsonl"
    lc = [json.loads(l) for l in lc_path.read_text(encoding="utf-8").splitlines()] if lc_path.exists() else []
    lc_train: list[dict] = []
    for i, rec in enumerate(lc):
        pdf = pdf_path(rec["category"], rec["id"])
        ex = lc_examples(rec, pdf)
        (sets["dev_lc"] if i % 20 == 0 else lc_train).extend(ex)
    rng.shuffle(lc_train)
    sets["train"] += lc_train[: args.max_lc]
    for k in ("train",):
        rng.shuffle(sets[k])
    sets["train"] = [e for e in sets["train"]][: args.max_synth + args.max_lc]

    from rx3.fields.gliner import MAX_BLOCK_CHARS

    for name in sets:  # drop runaway blocks (one huge plain-text paragraph swallowed into a head)
        sets[name] = [r for r in sets[name] if len(r["input"]) <= MAX_BLOCK_CHARS + 100]
    for name, rows in sets.items():
        (OUT / f"{name}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")
    kinds = Counter(next(iter(r["output"]["json_structures"][0])) for r in sets["train"])
    print({k: len(v) for k, v in sets.items()}, "train by section:", dict(kinds), "pdfs per family:", dict(n_pdf))


if __name__ == "__main__":
    main()
