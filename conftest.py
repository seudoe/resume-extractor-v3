"""Put types/ on sys.path so its modules import each other flatly.

Not `types.resume` — dot-importing `types` as a package collides with the
stdlib `types` module, which is already cached in sys.modules by the time
any script runs (see DECISIONS.md Stage 2).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "types"))
