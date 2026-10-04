"""Stage 4.1: seed data/gold/ from the real resumes in ../resume-data/.

For each source resume: dump its raw text to data/gold/raw/<id>.txt (so the
agent/user has something to read) and write an empty gold-JSON scaffold to
data/gold/drafts/<id>.json if one doesn't exist yet. Also writes
data/gold/manifest.json (tracked in git — no PII, just filenames/tags/status).

Actually filling in each scaffold's fields is manual (PROMPT.md §4.1: the
agent may draft gold by reading the resume, offline, no hosted LLM calls).
This script only sets up the scaffolding so that work has somewhere to go.

Usage: uv run python tools/draft_gold.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = ROOT / "data" / "gold"

sys.path.insert(0, str(ROOT / "types"))
sys.path.insert(0, str(ROOT))

from _docio import extract_links, extract_text  # noqa: E402
from _resume_data_layout import GOLD_CATEGORY, RESUME_DATA_ROOT, text_path  # noqa: E402

RESUME_DATA = RESUME_DATA_ROOT / "PDFs" / GOLD_CATEGORY

# Groups PROMPT.md §4.1 calls out as near-duplicates: real resumes with
# several nearly-identical uploaded versions. Keep them all (don't dedupe by
# deleting files) but tag them so the eval report can treat them as weaker
# independent evidence than N fully distinct resumes.
NEAR_DUPLICATE_GROUPS = [
    ["VickyResume (1).pdf", "VickyResume.pdf", "VickyResume-apr26.pdf", "VickyResume-(intern)-apr26.pdf"],
    ["Resume_Asif_4.0_compressed.pdf", "Resume_Asif_GOAL.docx", "Resume_Asif_GOAL-compressed.pdf"],
    ["DemoGOAL.pdf", "DemoGOAL.docx"],
]

EMPTY_PARSED_RESUME = {
    "summary": "",
    "workHistory": [],
    "education": [],
    "skills": [],
    "projects": [],
    "certifications": [],
    "languages": [],
    "publications": [],
    "affiliations": [],
    "awards": [],
    "interests": [],
    "metaDetails": {
        "name": "",
        "phone_no": "",
        "gender": None,
        "email": "",
        "github_profile": None,
        "linkedin": None,
        "address": {"city": "", "state": None, "country": "", "postal_code": None},
        "extra_links": [],
    },
    "bert_vector": None,
    "tfidf__vector": None,
}


def slugify(filename: str) -> str:
    # Keep the extension in the slug: DemoGOAL.pdf and DemoGOAL.docx must not
    # collide onto the same id (bug caught when both raw-dumped to
    # "demogoal.txt", silently overwriting one another).
    path = Path(filename)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", path.stem).strip("_").lower()
    ext = path.suffix.lstrip(".").lower()
    return f"{slug}_{ext}"


def near_dup_of(filename: str) -> str | None:
    for group in NEAR_DUPLICATE_GROUPS:
        if filename in group and filename != group[0]:
            return slugify(group[0])
    return None


def main() -> None:
    (GOLD_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (GOLD_DIR / "drafts").mkdir(parents=True, exist_ok=True)

    sources = sorted(
        p for p in RESUME_DATA.iterdir() if p.suffix.lower() in (".pdf", ".docx") and p.is_file()
    )

    manifest = []
    for path in sources:
        gid = slugify(path.name)
        raw_path = GOLD_DIR / "raw" / f"{gid}.txt"
        draft_path = GOLD_DIR / "drafts" / f"{gid}.json"

        # Reuse the user's standardized TEXTs/<cat>/<stem>.txt when present
        # instead of re-extracting; fall back to our own extraction.
        shared_text = text_path(GOLD_CATEGORY, path.stem)
        try:
            text = shared_text.read_text(encoding="utf-8") if shared_text.exists() else extract_text(path)
        except Exception as e:  # noqa: BLE001
            text = f"<<extraction failed: {e}>>"
        try:
            links = extract_links(path)
        except Exception as e:  # noqa: BLE001
            links = [f"<<link extraction failed: {e}>>"]
        if links:
            text += "\n\n--- LINKS (from annotations/relationships) ---\n" + "\n".join(links)
        raw_path.write_text(text, encoding="utf-8")

        if not draft_path.exists():
            scaffold = {
                "id": gid,
                "source_file": path.name,
                "near_duplicate_of": near_dup_of(path.name),
                # "scaffold": nothing hand-labelled yet, must NOT be scored
                # (every field is empty by construction, not because the
                # resume has no content — eval/run_eval.py skips these).
                # "drafted": hand-filled, pending Checkpoint 4B verification.
                # "verified": user has checked it against the source resume.
                "status": "scaffold",
                "verified_by": None,
                "verified_at": None,
                "parsed": EMPTY_PARSED_RESUME,
            }
            draft_path.write_text(json.dumps(scaffold, indent=2), encoding="utf-8")

        manifest.append(
            {
                "id": gid,
                "source_file": path.name,
                "format": path.suffix.lower().lstrip("."),
                "near_duplicate_of": near_dup_of(path.name),
                "drafted": draft_path.exists(),
                "verified": False,  # filled from the draft JSON at report time
            }
        )

    (GOLD_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{len(manifest)} source resumes scaffolded under {GOLD_DIR}")
    print(f"near-duplicates tagged: {sum(1 for m in manifest if m['near_duplicate_of'])}")


if __name__ == "__main__":
    main()
