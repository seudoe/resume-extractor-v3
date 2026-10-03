"""Per-page text-quality score (PROMPT.md §5 Stage 5): decides which pages
need the Stage 6 OCR fallback.

ponytail: skips the "% dictionary words" signal PROMPT.md mentions — that
needs a wordlist dependency we don't have, and the two cheap signals below
(near-zero extractable text, and `(cid:NN)` artefacts from a broken font
encoding) already catch the real failure mode this exists for: a PDF whose
text is drawn as vector shapes (h.md's FlowCV example, 0 extractable chars).
Add a dictionary check if a real resume slips through with garbled-but-dense
text that these two don't catch.
"""

import re

from ir import Page

_CID_ARTIFACT = re.compile(r"\(cid:\d+\)")

# A real resume page has way more than this many characters; near-zero means
# the page's "text" is actually drawn as vector shapes/images (h.md's FlowCV
# case: 0 extractable chars) and needs OCR.
MIN_CHARS_FOR_TEXT_LAYER = 20
# Above this fraction of `(cid:NN)` artefacts among words, the font's
# encoding is broken badly enough that OCR will do better than the garbage
# text layer.
MAX_CID_ARTIFACT_RATIO = 0.05


def page_quality(page: Page) -> dict:
    """Returns {"char_count", "cid_artifact_ratio", "needs_ocr"}."""
    text = " ".join(line.text for line in page.lines)
    char_count = len(text.strip())

    words = text.split()
    cid_hits = len(_CID_ARTIFACT.findall(text))
    cid_ratio = cid_hits / len(words) if words else 0.0

    needs_ocr = char_count < MIN_CHARS_FOR_TEXT_LAYER or cid_ratio > MAX_CID_ARTIFACT_RATIO

    return {
        "char_count": char_count,
        "cid_artifact_ratio": cid_ratio,
        "needs_ocr": needs_ocr,
    }
