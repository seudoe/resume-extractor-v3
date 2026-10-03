"""rx3: the resume-extractor-v3 pipeline package."""

import sys
from pathlib import Path

# types/ is never dot-imported (collides with stdlib `types` — see
# DECISIONS.md Stage 2). Put it on sys.path here, once, so every rx3
# submodule can do `from ir import Document, Line, ...` directly.
_types_dir = Path(__file__).resolve().parent.parent.parent / "types"
if str(_types_dir) not in sys.path:
    sys.path.insert(0, str(_types_dir))
