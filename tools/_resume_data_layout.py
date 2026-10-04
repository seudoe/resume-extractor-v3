"""Canonical layout of ../resume-data/ (standardized by the user 2026-10-03,
see DECISIONS.md Stage 6):

    resume-data/
      PDFs/<CATEGORY>/<name>.pdf
      JSONs/<CATEGORY>/<name>.json              # LLM-generated ParsedResumeData-shaped output
      TEXTs/<CATEGORY>/<name>.txt                # extracted plain text
      Extraction-details/<CATEGORY>/<name>.json  # LLM call metadata (model, timestamps, cost)

`AAA` is the hand-picked real-resume category — resume-extractor-v3's gold-seed
set (Stage 4, data/gold/). Every other category is the anonymized LiveCareer
set. JSONs/ in either category are LLM output: valid as Stage 10 training
data or as a scored baseline (like v2), NEVER as data/gold/ ground truth
(PROMPT.md §1.5/§4.1 — no hosted-LLM calls in the gold path).
"""

from pathlib import Path

RESUME_DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "resume-data"
GOLD_CATEGORY = "AAA"


def pdf_path(category: str, stem: str) -> Path:
    return RESUME_DATA_ROOT / "PDFs" / category / f"{stem}.pdf"


def text_path(category: str, stem: str) -> Path:
    return RESUME_DATA_ROOT / "TEXTs" / category / f"{stem}.txt"


def json_path(category: str, stem: str) -> Path:
    return RESUME_DATA_ROOT / "JSONs" / category / f"{stem}.json"


def extraction_details_path(category: str, stem: str) -> Path:
    return RESUME_DATA_ROOT / "Extraction-details" / category / f"{stem}.json"


def categories() -> list[str]:
    pdfs_dir = RESUME_DATA_ROOT / "PDFs"
    if not pdfs_dir.exists():
        return []
    return sorted(p.name for p in pdfs_dir.iterdir() if p.is_dir())


def stems_in_category(category: str) -> list[str]:
    """PDF stems present for a category (PDFs/ is the source of truth —
    JSONs/TEXTs/Extraction-details lag behind while the user's LLM pipeline
    is still running)."""
    cat_dir = RESUME_DATA_ROOT / "PDFs" / category
    if not cat_dir.exists():
        return []
    return sorted(p.stem for p in cat_dir.iterdir() if p.suffix.lower() == ".pdf")
