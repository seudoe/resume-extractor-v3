"""Print the facts PROMPT.md §3 asks for, so PROGRESS.md can record a real
environment snapshot instead of a claim.

Usage: uv run python scripts/check_env.py
"""

import importlib.metadata
import platform
import shutil
import subprocess
import sys

PACKAGES = [
    "pymupdf",
    "python-docx",
    "rapidocr-onnxruntime",
    "onnxruntime",
    "pytesseract",
    "pydantic",
    "fastapi",
    "uvicorn",
    "python-multipart",
    "dateparser",
    "rapidfuzz",
    "phonenumbers",
    "ftfy",
    "flashtext",
    "numpy",
    "pytest",
    "scipy",
    "psutil",
    "jiwer",
    "pandas",
    "jinja2",
    "reportlab",
    "playwright",
    "ruff",
]


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def main() -> None:
    section("Python")
    print(f"version: {sys.version.split()[0]}")
    print(f"executable: {sys.executable}")

    section("Package versions")
    for name in PACKAGES:
        try:
            print(f"{name}: {importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            print(f"{name}: NOT INSTALLED")

    section("Tesseract")
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        out = subprocess.run([tesseract_path, "--version"], capture_output=True, text=True)
        print(out.stdout.splitlines()[0] if out.stdout else out.stderr.splitlines()[0])
    else:
        print("not installed (not on PATH)")

    section("RapidOCR model load")
    try:
        from rapidocr_onnxruntime import RapidOCR

        RapidOCR()
        print("OK")
    except Exception as e:  # noqa: BLE001 - this is a diagnostic script
        print(f"FAILED: {e}")

    section("CUDA / GPU")
    try:
        import torch

        available = torch.cuda.is_available()
        print(f"torch: {torch.__version__}")
        print(f"cuda available: {available}")
        if available:
            props = torch.cuda.get_device_properties(0)
            print(f"device: {props.name}, VRAM: {props.total_memory / 1e9:.1f} GB")
    except ImportError:
        print("torch not installed (expected until `uv sync --extra train`)")

    section("CPU / RAM")
    try:
        import psutil

        print(f"logical CPUs: {psutil.cpu_count(logical=True)}")
        print(f"physical CPUs: {psutil.cpu_count(logical=False)}")
        print(f"total RAM: {psutil.virtual_memory().total / 1e9:.1f} GB")
    except ImportError:
        import os

        print(f"logical CPUs: {os.cpu_count()}")

    section("Platform")
    print(platform.platform())


if __name__ == "__main__":
    main()
