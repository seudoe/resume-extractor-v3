"""Run the rx3 rules baseline over the AAA PDFs (candidates for run_eval --baseline rx3)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401
from _resume_data_layout import GOLD_CATEGORY, pdf_path, stems_in_category  # noqa: E402
from rx3.fields.rules import extract_rules  # noqa: E402
from rx3.ingest.pdf import ingest_pdf  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402


def load_rx3_baseline() -> dict[str, dict]:
    """{stem: ParsedResumeData-shaped dict} (metaDetails included)."""
    out = {}
    for stem in stems_in_category(GOLD_CATEGORY):
        out[stem] = extract_rules(analyze_layout(ingest_pdf(pdf_path(GOLD_CATEGORY, stem).read_bytes())), stem + ".pdf")
    return out
