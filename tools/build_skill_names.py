"""Generate src/rx3/normalise/_skill_names.txt from resume-data/skill_db_relax_20.json (Hard/Soft skills only;
no parentheses, 3-40 chars, <= 4 words). Used to validate and case-fix items in skill lists.

    uv run python tools/build_skill_names.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from _resume_data_layout import RESUME_DATA_ROOT  # noqa: E402

db = json.loads((RESUME_DATA_ROOT / "skill_db_relax_20.json").read_text(encoding="utf-8"))
names = sorted({v["skill_name"].strip() for v in db.values()
                if v["skill_type"] in ("Hard Skill", "Soft Skill") and "(" not in v["skill_name"]
                and 3 <= len(v["skill_name"].strip()) <= 40 and len(v["skill_name"].split()) <= 4})
(ROOT / "src/rx3/normalise/_skill_names.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
print(len(names), "names")
