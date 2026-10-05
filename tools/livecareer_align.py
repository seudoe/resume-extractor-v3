"""LiveCareer aligner (PROMPT.md §5 Stage 10.1).

Parses `Resume_html` entries (div.paragraph = one entry; spans carry a 4-letter
code in their id) and fuzzy-aligns each tagged value to the IR lines of the
matching PDF. Output: data/livecareer/aligned.jsonl, one resume per line.

    uv run python tools/livecareer_align.py [--n 300] [--category HR]

Tag findings are logged in DECISIONS.md (Stage 10). Short version: company and
school names and cities are mostly anonymised to placeholders ("Company Name",
"City"), so those carry no label and are skipped; titles, dates, degrees,
programs and bullets are real.
"""

import argparse
import csv
import html as htmllib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401
from _resume_data_layout import RESUME_DATA_ROOT  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402

CSV_PATH = ROOT.parent / "FILES" / "Resume.csv"
OUT_PATH = ROOT / "data" / "livecareer" / "aligned.jsonl"
MIN_SIM = 0.9
PLACEHOLDERS = {"company name", "city", "state", "name", "school name", "institution name", "country", "zip code"}

SECTION_OF = {"EXPR": "workHistory", "WRKH": "workHistory", "EDUC": "education", "CERT": "certifications",
              "AFIL": "affiliations", "ACCM": "awards", "PROJ": "projects"}
CODE_FIELD = {  # span id code -> (field name)
    "JSTD": "start", "EDDT": "end", "JTIT": "title", "COMP": "company", "JCIT": "city", "JSTA": "state",
    "JDES": "description", "GRYR": "gradyear", "DGRE": "degree", "STUY": "program", "SCHO": "school",
    "SCIT": "city", "SSTA": "state", "FRFM": "field",
}
_SECTION = re.compile(r'id="SECTION_([A-Z]+)\d*"')
_PARAGRAPH = re.compile(r'<div class="paragraph')
_SPAN = re.compile(r'<span[^>]*\bid="\d+([A-Z]{4})\d+"[^>]*>(.*?)</span>', re.S)
_LI = re.compile(r"<li[^>]*>(.*?)</li>", re.S)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_entries(html: str) -> list[dict]:
    """[{section, fields: {name: str}, bullets: [str]}] in document order."""
    entries = []
    marks = [(m.start(), m.group(1)) for m in _SECTION.finditer(html)]
    for k, (pos, code) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(html)
        section = SECTION_OF.get(code)
        if not section:
            continue
        chunk = html[pos:end]
        starts = [m.start() for m in _PARAGRAPH.finditer(chunk)] + [len(chunk)]
        for a, b in zip(starts, starts[1:]):
            fields, bullets = {}, []
            for sc, inner in _SPAN.findall(chunk[a:b]):
                name = CODE_FIELD.get(sc)
                if not name:
                    continue
                if name == "description":
                    bullets = [t for t in (_clean(li) for li in _LI.findall(inner)) if t] or ([_clean(inner)] if _clean(inner) else [])
                    continue
                text = _clean(inner)
                if text and text.lower() not in PLACEHOLDERS:
                    fields.setdefault(name, text)
            if fields or bullets:
                entries.append({"section": section, "fields": fields, "bullets": bullets})
    return entries


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _find_line(value: str, lines: list[tuple[str, str]], start: int) -> tuple[str, float, int] | None:
    """First line at/after `start` that holds `value` (entries come in document order,
    so an entry never aligns before the previous one ended)."""
    v = _norm(value)
    if not v:
        return None
    for i in range(start, len(lines)):
        t = lines[i][1]
        if t:
            sim = 1.0 if v in t else fuzz.partial_ratio(v, t) / 100 if len(v) >= 4 else 0.0
            if sim >= MIN_SIM:
                return lines[i][0], sim, i
    return None


def align(entries: list[dict], doc) -> list[dict]:
    from rx3.sections.segment import segment_sections

    lines = [(ln.id, _norm(ln.text)) for p in doc.pages for ln in p.lines]
    index = {lid: i for i, (lid, _) in enumerate(lines)}
    heading_at: dict[str, int] = {}  # canonical section -> its first heading line
    for s in segment_sections(doc):
        if s.heading_id and s.name not in heading_at:
            heading_at[s.name] = index[s.heading_id]
    floor, last_section, out = 0, None, []
    for e in entries:
        if e["section"] != last_section:
            floor, last_section = heading_at.get(e["section"], 0), e["section"]
        fields, top = {}, floor
        for name, value in e["fields"].items():
            hit = _find_line(value, lines, floor)
            fields[name] = {"value": value, "line_id": hit[0] if hit else None, "sim": round(hit[1], 3) if hit else 0.0}
            if hit:
                top = max(top, hit[2])
        bullets = []
        for b in e["bullets"]:
            hit = _find_line(b[:120], lines, floor)  # bullets can wrap; the head is enough
            bullets.append({"value": b, "line_id": hit[0] if hit else None, "sim": round(hit[1], 3) if hit else 0.0})
            if hit:
                top = max(top, hit[2])
        floor = top
        out.append({"section": e["section"], "fields": fields, "bullets": bullets})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--category")
    ap.add_argument("--out", help="output jsonl (default data/livecareer/aligned.jsonl, the eval pool)")
    ap.add_argument("--exclude-from", help="jsonl whose resume ids are never sampled (keeps train and eval pools disjoint)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT_PATH
    skip = {json.loads(l)["id"] for l in Path(args.exclude_from).read_text(encoding="utf-8").splitlines()} if args.exclude_from else set()

    csv.field_size_limit(10**9)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (not args.category or row["Category"] == args.category) and row["ID"] not in skip:
                by_cat[row["Category"]].append(row)
    rng = random.Random(args.seed)
    per_cat = max(1, args.n // len(by_cat))
    sample = [r for _, rows in sorted(by_cat.items()) for r in rng.sample(rows, min(per_cat, len(rows)))]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen, ok, n_resumes = Counter(), Counter(), 0
    with open(out_path, "w", encoding="utf-8") as out:
        for row in sample:
            pdf = RESUME_DATA_ROOT / "PDFs" / row["Category"] / f"{row['ID']}.pdf"
            entries = parse_entries(row["Resume_html"])
            if not pdf.exists() or not entries:
                continue
            doc = analyze_layout(ingest_pdf(pdf.read_bytes()))
            aligned = align(entries, doc)
            n_resumes += 1
            for e in aligned:
                for name, f in e["fields"].items():
                    seen[(e["section"], name)] += 1
                    ok[(e["section"], name)] += f["line_id"] is not None
                for b in e["bullets"]:
                    seen[(e["section"], "bullet")] += 1
                    ok[(e["section"], "bullet")] += b["line_id"] is not None
            out.write(json.dumps({"id": row["ID"], "category": row["Category"], "entries": aligned}, ensure_ascii=False) + "\n")

    print(f"{n_resumes} resumes -> {out_path}")
    for (sec, name), n in sorted(seen.items()):
        print(f"{sec:14} {name:12} aligned {ok[(sec, name)]}/{n} = {ok[(sec, name)] / n:.1%}")


if __name__ == "__main__":
    main()
