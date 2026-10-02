# Progress

## Current stage

**Stage 1 — Scaffold.** Complete, pending user commit.

## Done

- Created `resume-extractor-v3/` folder tree per PROMPT.md §4 (`types/`, `src/rx3/`,
  `data/`, `models/`, `eval/`, `tools/`, `tests/`, `reports/`), each Python
  package with an empty `__init__.py`.
- `.gitignore` (venv, `__pycache__`, `.env`, bulky `data/`/`models/` content,
  large report JSON), `.dockerignore`, `.env.example`, `.python-version` (3.11).
- `README.md` with HF Spaces YAML front-matter (`sdk: docker`, `app_port: 7860`).
- Minimal `pyproject.toml` (no deps yet — Stage 3 pins them with uv).
- Placeholder `Dockerfile` (filled in properly at Stage 14).

## Next

- Stage 2: Pydantic v2 schema (`types/resume.py`) mirroring `ifind/types/resume.ts`
  + `generics.ts`, internal Document IR (`types/ir.py`), JSON schema export,
  diff against the TS source of truth.

## Open questions

- None yet — first checkpoint questions will surface in Stage 3 (Tesseract/torch
  install) and Stage 4 (gold set size, acceptance targets).
