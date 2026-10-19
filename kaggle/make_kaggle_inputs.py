"""Pack everything the Kaggle notebook needs into kaggle/rx3-kaggle-inputs.zip (mirrors the IPD folder layout).

    python kaggle/make_kaggle_inputs.py [--no-pdfs]

--no-pdfs: ship only the prebuilt data/train/*.jsonl (tiny); the notebook then cannot rebuild the data (REBUILD_DATA must be False).
"""
import argparse
import zipfile
from pathlib import Path

RX3 = Path(__file__).resolve().parent.parent
IPD = RX3.parent
OUT = Path(__file__).resolve().parent / "rx3-kaggle-inputs.zip"

ap = argparse.ArgumentParser()
ap.add_argument("--no-pdfs", action="store_true")
args = ap.parse_args()

parts = [RX3 / "src", RX3 / "tools", RX3 / "eval", RX3 / "pyproject.toml", RX3 / "data" / "train",
         RX3 / "models" / "adapters" / "rx3-entry-lora"]
if not args.no_pdfs:
    parts += [RX3 / "data" / "synthetic", RX3 / "data" / "livecareer" / "aligned_train.jsonl",
              RX3 / "data" / "livecareer" / "aligned.jsonl", IPD / "resume-data" / "PDFs", IPD / "resume-data" / "JSONs"]

skip = {"__pycache__", ".venv"}
n = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for p in parts:
        for f in ([p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())):
            if "resume-data" in f.parts and "AAA" in f.parts:
                continue  # gold category: never trained on (and its file names break Kaggle's upload rules)
            if skip & set(f.parts) or f.suffix == ".pyc" or f.name.endswith((".lengths.json", ".lengths.npy")):
                continue
            z.write(f, Path("IPD") / f.relative_to(IPD))
            n += 1
print(f"{n} files -> {OUT} ({OUT.stat().st_size / 1e6:.0f} MB)")
