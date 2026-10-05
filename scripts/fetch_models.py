"""Download the pinned GLiNER2.5 base weights into the Hugging Face cache and verify every checksum in models/MODEL_CHECKSUMS.txt.

Used by the Dockerfile at build time (and handy locally): fails the build if the model or the adapter does not match.

    python scripts/fetch_models.py
"""

import hashlib
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent.parent
REPO, REV = "fastino/gliner2.5-base-v1", "ca906247640776a07753514055be9726f9080ead"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = {f: Path(hf_hub_download(REPO, f, revision=REV)) for f in ("model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json", "encoder_config/config.json")}
    expected = {}
    for line in (ROOT / "models" / "MODEL_CHECKSUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, _, label = line.partition("  ")
        expected[label.split()[-1]] = digest
    bad = []
    if sha256(files["model.safetensors"]) != expected["model.safetensors"]:
        bad.append("model.safetensors")
    adapter = ROOT / "models" / "adapters" / "rx3-entry-lora" / "adapter_model.safetensors"
    if sha256(adapter) != expected["models/adapters/rx3-entry-lora/adapter_model.safetensors"]:
        bad.append(str(adapter))
    if bad:
        sys.exit(f"checksum mismatch: {bad}")
    print("models ok:", REPO, REV[:8], "+ adapter")


if __name__ == "__main__":
    main()
