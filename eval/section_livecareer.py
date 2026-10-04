"""Held-out heading check on LiveCareer resumes (PROMPT.md §5 Stage 9 asks for
LiveCareer `sectiontitle` data). The HTML marks each section title with an id
like SECTNAME_EXPR123, so title text + type code is a free weak label. The
section rules were NOT tuned on these resumes (they were tuned on the 32 gold
ones), so this is the closest thing to a held-out number we have.

    uv run python -m eval.section_livecareer [--n 200]

Weak labels: LiveCareer's own titles can be mislabeled (h.md), anonymised
text is irrelevant here (headings are not anonymised), and every LiveCareer
resume is the same template family — so this says little about Canva-style
two-column layouts, which is what the gold set covers.
"""

import argparse
import csv
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401
from _resume_data_layout import RESUME_DATA_ROOT  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from rx3.sections.segment import segment_sections  # noqa: E402
from rx3.sections.synonyms import normalize  # noqa: E402

CSV_PATH = ROOT.parent / "FILES" / "Resume.csv"
CODE_TO_SECTION = {
    "SUMM": "summary", "OBJE": "summary", "HILT": "skills", "SKLL": "skills", "ACCM": "awards", "EXPR": "workHistory",
    "EDUC": "education", "CERT": "certifications", "AFIL": "affiliations", "LANG": "languages", "INTR": "interests",
    "PUBL": "publications", "PROJ": "projects", "HONR": "awards",
}
_TITLE = re.compile(r'<div[^>]*class="[^"]*sectiontitle[^"]*"[^>]*id="SECTNAME_([A-Z]+)\d*"[^>]*>(.*?)</div>', re.S)


def key(text: str) -> str:
    return normalize(text).replace(" ", "")


def titles(html: str) -> list[tuple[str, str]]:
    out = []
    for code, inner in _TITLE.findall(html):
        text = re.sub(r"<[^>]+>|\s+", " ", inner).strip()
        if text:
            out.append((text, CODE_TO_SECTION.get(code, "other")))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()

    csv.field_size_limit(10**9)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_cat[row["Category"]].append(row)
    rng = random.Random(0)
    sample = []
    per_cat = max(1, args.n // len(by_cat))
    for cat, rows in sorted(by_cat.items()):
        sample += rng.sample(rows, min(per_cat, len(rows)))

    tp = fp = fn = canon = scored = 0
    missed, spurious, wrong = Counter(), Counter(), Counter()
    for row in sample:
        pdf = RESUME_DATA_ROOT / "PDFs" / row["Category"] / f"{row['ID']}.pdf"
        gold = titles(row["Resume_html"])
        if not pdf.exists() or not gold:
            continue
        scored += 1
        doc = analyze_layout(ingest_pdf(pdf.read_bytes()))
        pred = [(key(s.heading), s.name) for s in segment_sections(doc) if s.heading]
        pool = list(pred)
        for text, section in gold:
            hit = next((p for p in pool if p[0] == key(text)), None)
            if hit:
                pool.remove(hit)
                tp += 1
                canon += hit[1] == section
                if hit[1] != section:
                    wrong[(text.lower(), section, hit[1])] += 1
            else:
                fn += 1
                missed[text.lower()] += 1
        for p in pool:
            fp += 1
            spurious[p[0]] += 1

    prec, rec = tp / (tp + fp), tp / (tp + fn)
    md = [f"# LiveCareer held-out heading check — {date.today().isoformat()}", "",
          f"{scored} resumes (stratified over {len(by_cat)} categories, seed 0). Weak labels from HTML `sectiontitle`.", "",
          f"- Heading precision {prec:.1%}, recall {rec:.1%} (tp {tp}, fp {fp}, fn {fn})",
          f"- Canonical section on matched headings: {canon}/{tp} = {canon / tp:.1%}", "",
          "### Most-missed titles", ""] + [f"- {t}: {c}" for t, c in missed.most_common(12)]
    md += ["", "### Most common spurious detections", ""] + [f"- {t}: {c}" for t, c in spurious.most_common(12)]
    md += ["", "### Most common canonical disagreements (title, label code -> rules)", ""]
    md += [f"- '{t}': LiveCareer says {g}, rules say {p} ({c}x)" for (t, g, p), c in wrong.most_common(10)]
    out = ROOT / "reports" / f"section_livecareer_{date.today().isoformat()}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
