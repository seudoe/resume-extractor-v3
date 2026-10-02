# Progress

## Current stage

**Stage 3 — Environments.** Complete, pending user commit.

## Done

### Stage 1 — Scaffold

- Created `resume-extractor-v3/` folder tree per PROMPT.md §4 (`types/`, `src/rx3/`,
  `data/`, `models/`, `eval/`, `tools/`, `tests/`, `reports/`), each Python
  package with an empty `__init__.py`.
- `.gitignore` (venv, `__pycache__`, `.env`, bulky `data/`/`models/` content,
  large report JSON), `.dockerignore`, `.env.example`, `.python-version` (3.11).
- `README.md` with HF Spaces YAML front-matter (`sdk: docker`, `app_port: 7860`).
- Minimal `pyproject.toml` (no deps yet — Stage 3 pins them with uv).
- Placeholder `Dockerfile` (filled in properly at Stage 14).

### Stage 2 — Types / schema

- `types/resume.py` + `types/sections/*.py`: Pydantic v2 models mirroring
  `ifind/types/resume.ts` and `generics.ts` field-for-field (checked against
  the live files, including the still-active interfaces above the commented
  "OLD" block). `types/ir.py`: internal Document IR (`Span`, `Line`, `Block`,
  `Page`, `Document`, `Provenance`, plus a `BBox` helper).
- Found and fixed a real import bug: dot-importing `types/` as a package
  (`from types.resume import ...`) silently hits the stdlib `types` module
  instead (see DECISIONS.md). Fix: `types/` stays on disk as specced, but is
  never dot-imported — it's added to `sys.path` directly (`conftest.py` for
  tests) and its modules import each other flatly.
- `tools/export_schema.py`: exports `types/generated/resume.schema.json` and
  a generated `types/generated/resume.ts`, diffed by eye against
  `ifind/types/resume.ts` — field names/nesting/enums match; the only
  difference is cosmetic (see DECISIONS.md).
- Empty-value policy decided by reading `ifind/lib/resumeParser.ts`
  (`normaliseHFOutput`) and `OverviewTab.tsx`: `""` for required strings,
  `None` for nullable fields, `[]` for arrays. `gender` defaults to `None`.
- `tests/test_types.py`: empty-default validation, a hand-built sample
  round-trip (`model_validate` → `model_dump` → `model_validate`, equal), and
  an invalid-enum rejection test. `python -m pytest tests/test_types.py -q`
  → 3 passed (run with system Python 3.14 + pydantic 2.13.5 for now; the
  pinned 3.11 `.venv` lands in Stage 3).

### Stage 3 — Environments

- Installed `uv` (0.12.22, via `pip install --user uv`) and created `.venv`
  with Python 3.11.9 (already present on this machine, no download).
- `pyproject.toml`: pinned runtime deps (pymupdf, python-docx,
  rapidocr-onnxruntime, pytesseract, pydantic, fastapi, uvicorn, dateparser,
  rapidfuzz, phonenumbers, ftfy, flashtext, numpy), a `dev` extra (pytest,
  scipy, psutil, jiwer, pandas, jinja2, reportlab, playwright, ruff), a
  `gliner` extra (deferred — needed in Stage 10, not before), and a `train`
  extra (torch, gliner2[train], transformers, datasets, peft, scikit-learn,
  lightgbm — opt-in, not installed). `uv.lock` committed for reproducibility.
- `uv sync --extra dev` succeeded; `pytest -q` → 3 passed under the real 3.11 venv.
- `scripts/check_env.py` written and run — output below.
- **Checkpoint 3A — asked the user:** install Tesseract now? Install CUDA
  torch now? User said defer both. Neither is installed; RapidOCR already
  loads with zero system install, so Stage 5–9 are unblocked either way.

**`uv run python scripts/check_env.py` output (2026-10-02):**

```
--- Python ---
version: 3.11.9
executable: C:\Users\4dmin\Downloads\iFind30\resume-extractor-v3\.venv\Scripts\python.exe

--- Package versions ---
pymupdf: 1.28.2
python-docx: 1.2.0
rapidocr-onnxruntime: 1.4.4
onnxruntime: 1.30.0
pytesseract: 0.3.13
pydantic: 2.13.5
fastapi: 0.142.2
uvicorn: 0.54.0
python-multipart: 0.0.32
dateparser: 1.4.3
rapidfuzz: 3.14.6
phonenumbers: 9.0.40
ftfy: 6.3.1
flashtext: 2.7
numpy: 2.4.6
pytest: 9.1.1
scipy: 1.17.1
psutil: 7.2.2
jiwer: 4.0.0
pandas: 3.0.6
jinja2: 3.1.6
reportlab: 5.0.1
playwright: 1.63.0
ruff: 0.16.10

--- Tesseract ---
not installed (not on PATH)

--- RapidOCR model load ---
OK

--- CUDA / GPU ---
torch not installed (expected until `uv sync --extra train`)

--- CPU / RAM ---
logical CPUs: 16
physical CPUs: 12
total RAM: 16.8 GB

--- Platform ---
Windows-10-10.0.26200-SP0
```

## Next

- Stage 4: evaluation harness + gold set — the biggest stage before any
  extraction code is written. Will need the user's help collecting more real
  resumes (Checkpoint 4A) and verifying gold labels (Checkpoint 4B), plus
  confirmation of the §4.7 acceptance targets (Checkpoint 4D).

## Open questions

- None yet — Stage 4's checkpoints (more real resumes, gold verification,
  acceptance targets, optional AI-path export) come next.
