# Progress

## Current stage

**Stage 2 — Types / schema.** Complete, pending user commit.

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

## Next

- Stage 3: uv + Python 3.11 `.venv`, pinned runtime/dev/train deps in
  `pyproject.toml`, `scripts/check_env.py`. Checkpoint needed before
  installing Tesseract or CUDA torch.

## Open questions

- None yet — first checkpoint questions will surface in Stage 3 (Tesseract/torch
  install) and Stage 4 (gold set size, acceptance targets).
