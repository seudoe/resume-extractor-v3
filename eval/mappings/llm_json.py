"""LLM-generated JSONs from the standardized resume-data layout
(resume-data/JSONs/<category>/<stem>.json), scored as just another baseline
against hand-drafted gold. Never used AS gold (PROMPT.md §1.5/§4.1).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))

from _resume_data_layout import GOLD_CATEGORY, RESUME_DATA_ROOT  # noqa: E402


def load_llm_baseline(category: str = GOLD_CATEGORY) -> dict[str, dict]:
    """Returns {stem: parsedData} for every JSON present in the category."""
    out = {}
    for path in (RESUME_DATA_ROOT / "JSONs" / category).glob("*.json"):
        out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return out
