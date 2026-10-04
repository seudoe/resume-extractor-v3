"""Stage 9 metrics: heading detection P/R, canonical-section accuracy on matched
headings, and line-level section-assignment accuracy against the hand-labelled
section gold (data/gold/sections/section_gold.json).

    uv run python -m eval.section_eval

Line-level gold is derived from the gold headings: walking the laid-out lines
in order, each gold heading is located at the next line whose label matches
it; lines then take the section of the last non-inline heading (inline
headings label only their own line); lines before the first heading are
`header`. A gold heading that matches no line is reported as unlocatable and
skipped (it cannot be scored line-wise).
"""

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401
from _resume_data_layout import GOLD_CATEGORY, pdf_path  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from rx3.sections.headings import _label_and_rest  # noqa: E402
from rx3.sections.segment import line_sections, segment_sections  # noqa: E402
from rx3.sections.synonyms import normalize  # noqa: E402

GOLD = ROOT / "data" / "gold" / "sections" / "section_gold.json"
TARGET = 0.95  # PROMPT.md §4.7


def key(text: str) -> str:
    return normalize(text).replace(" ", "")


def gold_line_labels(lines, gold_headings) -> tuple[dict[str, str], list[str]]:
    labels, unlocatable = {}, []
    pos, current = 0, "header"
    for entry in gold_headings:
        text, section, inline = entry[0], entry[1], len(entry) > 2 and entry[2]
        found = next((i for i in range(pos, len(lines)) if key(_label_and_rest(lines[i].text)[0]) == key(text)), None)
        if found is None:
            unlocatable.append(text)
            continue
        for l in lines[pos:found]:
            labels[l.id] = current
        if inline:
            labels[lines[found].id] = section
            pos = found + 1
        else:
            current = section
            pos = found
    for l in lines[pos:]:
        labels.setdefault(l.id, current)
    return labels, unlocatable


def main() -> None:
    gold_all = json.loads(GOLD.read_text(encoding="utf-8"))
    gold = {k: v for k, v in gold_all.items() if not k.startswith("_")}

    tp = fp = fn = canon_ok = 0
    line_ok = line_total = 0
    per_file, confusions, errors = [], Counter(), []
    unloc_total = 0
    for stem, headings in gold.items():
        path = pdf_path(GOLD_CATEGORY, stem)
        if not path.exists():
            continue
        doc = analyze_layout(ingest_pdf(path.read_bytes(), filename=path.name))
        lines = [l for p in doc.pages for l in p.lines]
        sections = segment_sections(doc)

        pred = [(key(s.heading), s.name, s.inline) for s in sections if s.heading]
        gold_keys = [(key(h[0]), h[1]) for h in headings]
        pred_pool = list(pred)
        for gk, gsec in gold_keys:
            hit = next((p for p in pred_pool if p[0] == gk), None)
            if hit:
                pred_pool.remove(hit)
                tp += 1
                canon_ok += hit[1] == gsec
                if hit[1] != gsec:
                    errors.append((stem, f"heading '{gk}' gold={gsec} pred={hit[1]}"))
            else:
                fn += 1
                errors.append((stem, f"MISSED heading '{gk}' ({gsec})"))
        for p in pred_pool:
            fp += 1
            errors.append((stem, f"SPURIOUS heading '{p[0]}' -> {p[1]}"))

        gl, unloc = gold_line_labels(lines, headings)
        unloc_total += len(unloc)
        pl = line_sections(sections)
        ok = total = 0
        for l in lines:
            g, p = gl.get(l.id), pl.get(l.id)
            if g is None:
                continue
            total += 1
            ok += g == p
            if g != p:
                confusions[(g, p)] += 1
        line_ok, line_total = line_ok + ok, line_total + total
        per_file.append((stem, ok / total if total else 1.0, total))

    prec, rec = tp / (tp + fp) if tp + fp else 1.0, tp / (tp + fn) if tp + fn else 1.0
    md = [f"# Section eval — {date.today().isoformat()}", ""]
    md.append(f"Gold: {len(per_file)} resumes, status **{gold_all['_meta']['status']}** "
              f"(verified_by: {gold_all['_meta']['verified_by']}). **Unverified gold: not a reported accuracy.** "
              f"Rules were tuned on these resumes (development set).")
    md += ["", f"- Heading detection: precision {prec:.1%}, recall {rec:.1%} (tp {tp}, fp {fp}, fn {fn})",
           f"- Canonical section on matched headings: {canon_ok}/{tp} = {canon_ok / tp:.1%}" if tp else "",
           f"- **Line-level section assignment: {line_ok}/{line_total} = {line_ok / line_total:.1%}** "
           f"(target {TARGET:.0%}: {'MET' if line_ok / line_total >= TARGET else 'MISSED'})",
           f"- Unlocatable gold headings (no matching line): {unloc_total}", "",
           "### Worst files (line accuracy)", ""]
    for stem, acc, n in sorted(per_file, key=lambda t: t[1])[:10]:
        md.append(f"- `{stem}`: {acc:.1%} of {n} lines")
    md += ["", "### Top line confusions (gold -> predicted)", ""]
    for (g, p), c in confusions.most_common(10):
        md.append(f"- {g} -> {p}: {c} lines")
    md += ["", "### Heading errors", ""] + [f"- `{s}` {e}" for s, e in errors]

    out = ROOT / "reports" / f"section_eval_{date.today().isoformat()}"
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
