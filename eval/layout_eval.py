"""Stage 7 bullet metric: does each gold bullet (responsibilities/
achievements/project descriptions/affiliation impact) come out as exactly one
layout line? Catches both splits (wrapped line not merged) and over-merges
(bullet glued to its neighbour).

    uv run python -m eval.layout_eval
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from rapidfuzz.fuzz import partial_ratio  # noqa: E402

from _resume_data_layout import GOLD_CATEGORY, pdf_path  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from rx3.layout.bullets import BULLET_GLYPHS  # noqa: E402


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lstrip().lstrip(BULLET_GLYPHS).strip().lower())


def gold_bullets(parsed: dict) -> list[str]:
    out = []
    for w in parsed.get("workHistory", []):
        out += w.get("responsibilities", []) + w.get("achievements", [])
    for p in parsed.get("projects", []):
        out += p.get("description", [])
    for a in parsed.get("affiliations", []):
        out += a.get("impact", [])
    return [b for b in out if b.strip()]


def main() -> None:
    total = hit = 0
    for path in sorted((ROOT / "data" / "gold" / "drafts").glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry.get("status") == "scaffold":
            continue
        pdf = pdf_path(GOLD_CATEGORY, Path(entry["source_file"]).stem)
        if not pdf.exists():
            continue
        doc = analyze_layout(ingest_pdf(pdf.read_bytes()))
        lines = [_norm(l.text) for p in doc.pages for l in p.lines]
        bullets = gold_bullets(entry["parsed"])
        ok = 0
        for b in bullets:
            nb = _norm(b)
            ok += any(partial_ratio(nb, ln) >= 95 and len(nb) / max(len(ln), 1) >= 0.8 for ln in lines)
        print(f"{entry['id']}: {ok}/{len(bullets)} gold bullets come out as exactly one line")
        total, hit = total + len(bullets), hit + ok
    print(f"TOTAL bullet accuracy: {hit}/{total} = {hit / total:.1%}" if total else "no drafted gold with bullets")


if __name__ == "__main__":
    main()
