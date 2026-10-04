"""Stage 6 OCR benchmark (PROMPT.md §5): rasterise text-based gold PDFs, OCR
them, score CER/WER against the embedded text layer (free ground truth),
plus latency/RAM per page.

    uv run python -m eval.ocr_bench [--dpis 150 200 300] [--limit 6]

Only RapidOCR is wired up; Tesseract isn't installed (Checkpoint 3A,
deferred) — add a second engine here if/when it is.
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import jiwer  # noqa: E402
import pymupdf  # noqa: E402

from _resume_data_layout import GOLD_CATEGORY, pdf_path  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.ocr.rapid import ocr_page  # noqa: E402

# Single-column text resumes: reading-order differences between the OCR and
# the embedded layer would otherwise be scored as OCR character errors.
SAMPLE_STEMS = [
    "Vedant Patil",
    "VickyResume-apr26",
    "Entry_Level_Resume_Template__LaTeX_",
    "Azlan's_Resume-mar26",
    "Aagam_esume-apr26",
    "Mehdiresume-apr26",
]


def _norm(text: str) -> str:
    return " ".join(text.split())


def _nospace(text: str) -> str:
    return "".join(text.split())


def bench(dpis: list[int], stems: list[str]) -> list[dict]:
    import psutil

    proc = psutil.Process()
    rows = []
    for stem in stems:
        path = pdf_path(GOLD_CATEGORY, stem)
        if not path.exists():
            continue
        data = path.read_bytes()
        ref = _norm(" ".join(l.text for l in ingest_pdf(data).pages[0].lines))
        pdf = pymupdf.open(stream=data, filetype="pdf")
        for dpi in dpis:
            rss0 = proc.memory_info().rss
            t = time.perf_counter()
            page = ocr_page(pdf[0], 0, 0, dpi=dpi)
            dt = time.perf_counter() - t
            hyp = _norm(" ".join(l.text for l in page.lines))
            rows.append(
                {
                    "stem": stem,
                    "dpi": dpi,
                    "seconds": round(dt, 2),
                    "cer": round(jiwer.cer(ref, hyp), 4),
                    "cer_nospace": round(jiwer.cer(_nospace(ref), _nospace(hyp)), 4),
                    "wer": round(jiwer.wer(ref, hyp), 4),
                    "rss_delta_mb": round((proc.memory_info().rss - rss0) / 1e6, 1),
                }
            )
            print(rows[-1], flush=True)
        pdf.close()
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpis", type=int, nargs="+", default=[150, 200, 300])
    ap.add_argument("--limit", type=int, default=len(SAMPLE_STEMS))
    args = ap.parse_args()
    rows = bench(args.dpis, SAMPLE_STEMS[: args.limit])

    out = ROOT / "reports" / f"ocr_bench_{date.today().isoformat()}"
    out.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = ["| DPI | mean s/page | max s | mean CER | mean CER (no spaces) | mean WER |", "|---|---|---|---|---|---|"]
    for dpi in args.dpis:
        r = [x for x in rows if x["dpi"] == dpi]
        if r:
            m = lambda k: sum(x[k] for x in r) / len(r)  # noqa: E731
            lines.append(
                f"| {dpi} | {m('seconds'):.1f} | {max(x['seconds'] for x in r):.1f} | "
                f"{m('cer'):.3f} | {m('cer_nospace'):.3f} | {m('wer'):.3f} |"
            )
    out.with_suffix(".md").write_text("# OCR benchmark (RapidOCR)\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
