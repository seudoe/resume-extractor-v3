"""Run the rx3 pipeline over the AAA PDFs (candidates for run_eval --baseline v3 / rx3)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import rx3  # noqa: E402,F401
from _resume_data_layout import GOLD_CATEGORY, pdf_path, stems_in_category  # noqa: E402
from rx3.pipeline import extract  # noqa: E402


def load_rx3_baseline() -> dict[str, dict]:
    """{stem: ParsedResumeData-shaped dict} from the full Stage 12 pipeline (grounded, deduped, validated)."""
    return {stem: extract(pdf_path(GOLD_CATEGORY, stem).read_bytes(), stem + ".pdf") for stem in stems_in_category(GOLD_CATEGORY)}
