"""Local server: POST /extract (multipart `file`: PDF/DOCX) -> JSON, using the rx3 pipeline + GLiNER2 LoRA adapter.

    uv run python scripts/serve.py [--port 8000] [--adapter models/adapters-candidate/rx3-entry-lora-20-10]

Docs: http://localhost:8000/docs. Adapter defaults to the 20-10 Kaggle run; `--adapter shipped` uses models/adapters/rx3-entry-lora."""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8000)
ap.add_argument("--adapter", default="models/adapters-candidate/rx3-entry-lora-20-10")
args = ap.parse_args()

adapter = ROOT / "models/adapters/rx3-entry-lora" if args.adapter == "shipped" else (ROOT / args.adapter)
os.environ.setdefault("RX3_ENABLE_GLINER", "1")
os.environ["RX3_GLINER_ADAPTER"] = str(adapter)
os.environ.setdefault("RX3_TIMEOUT_S", "60")  # first requests on a laptop CPU are slower than the 25 s Space limit

import uvicorn  # noqa: E402

print(f"adapter: {adapter}")
uvicorn.run("rx3.api:app", host="127.0.0.1", port=args.port, app_dir=str(ROOT / "src"))
