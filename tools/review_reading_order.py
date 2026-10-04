"""Render each resume page with its lines numbered in reading order, colour-
coded by region, so a human can judge the order at a glance (Stage 7,
Checkpoint 7A). Output: data/gold/reading_order/<stem>_p<N>.png + index.html.

    uv run python tools/review_reading_order.py [stem ...]   # default: all AAA
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import pymupdf  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from _resume_data_layout import GOLD_CATEGORY, pdf_path, stems_in_category  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402

OUT = ROOT / "data" / "gold" / "reading_order"
PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080", "#9a6324", "#800000"]
DPI = 100


def render(stem: str) -> list[str]:
    data = pdf_path(GOLD_CATEGORY, stem).read_bytes()
    doc = analyze_layout(ingest_pdf(data, filename=stem))
    src = pymupdf.open(stream=data, filetype="pdf")
    names = []
    for page in doc.pages:
        pix = src[page.number].get_pixmap(dpi=DPI)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)
        k = DPI / 72.0
        for n, line in enumerate(page.lines):
            color = PALETTE[(line.features.region if line.features else 0) % len(PALETTE)]
            b = line.bbox
            draw.rectangle([b.x0 * k, b.y0 * k, b.x1 * k, b.y1 * k], outline=color, width=1)
            draw.text((b.x0 * k - 14, b.y0 * k), str(n), fill=color)
        name = f"{stem}_p{page.number + 1}.png".replace(" ", "_")
        img.save(OUT / name)
        names.append(name)
    return names


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stems = sys.argv[1:] or stems_in_category(GOLD_CATEGORY)
    html = ["<html><body style='font-family:sans-serif'><h2>Reading-order review</h2>"]
    for stem in stems:
        for name in render(stem):
            html.append(f"<h4>{name}</h4><img src='{name}' style='max-width:900px;border:1px solid #ccc'>")
        print("rendered", stem, flush=True)
    (OUT / "index.html").write_text("\n".join(html) + "</body></html>", encoding="utf-8")


if __name__ == "__main__":
    main()
