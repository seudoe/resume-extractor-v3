# Decisions

Each entry: the choice, the alternatives considered, and the eval numbers (if
any) that decided it. Append-only within a stage; superseding decisions should
reference the entry they replace rather than deleting it.

## Stage 1 — Scaffold

- **Package manager: uv.** Alternatives: pip+venv, poetry. uv is fast,
  lockfile-based, and specified by PROMPT.md §3. No eval numbers (tooling
  choice, not a modeling choice) — deferred detail to Stage 3.
- **Package name `rx3`** for `src/rx3/` to keep imports short (`from rx3.ingest import pdf`).
- Nothing else decided yet — Stage 1 is scaffolding only, no extraction code.

## Stage 2 — Types / schema

- **`types/` is not dot-imported as a package.** Bug found while building this
  stage: `from types.resume import X` silently resolves to the *stdlib*
  `types` module (not our directory) because `types` is already cached in
  `sys.modules` before any of our code runs — Python never re-checks
  `sys.path` for a name already in the module cache, and the stdlib `types`
  module has no `resume` attribute, so the import raises `ModuleNotFoundError`.
  Confirmed empirically (`tools/export_schema.py` failed exactly this way on
  first run). Fix: keep the on-disk folder named `types/` (per PROMPT.md §4),
  but never dot-import it as `types.X`. Instead `types/` itself is put on
  `sys.path` (via `conftest.py` for tests, inline in `tools/export_schema.py`
  for scripts) and its modules import each other flatly
  (`from generics import DateRange`, `from sections.work import WorkHistory`).
  Anything under `src/rx3/` that needs these schemas later should do the same
  — add `types/` to `sys.path`, then import flat names, never `import types`.
- **Empty-value policy:** required string fields default to `""`, fields typed
  `X | null` in `ifind/types/resume.ts` default to `None`, arrays default to
  `[]`. Decided by reading `ifind/lib/resumeParser.ts` (`normaliseHFOutput`,
  which already builds `metaDetails` with `?? ""` for required strings and
  `?? null` for nullable ones) and `ifind/components/dashboard/OverviewTab.tsx`
  (defensive `?? 0` / `|| []` on `workHistory`/`education`/`skills`), so v3's
  defaults match what the current glue code and UI already assume.
  `gender` defaults to `None` per PROMPT.md §1.7 (never infer it).
- **One Pydantic module per TS interface**, named sections placed under
  `types/sections/` as PROMPT.md §4 specifies; anonymous TS interfaces
  (`certifications[]`, `languages[]`, `interests[]`, `Address`, `ExtraLink`,
  `SkillTool`, `ProjectLinks`, `EducationField`) were given explicit names
  since Pydantic needs a class name even where TS left the shape inline.
- **Schema diff tool (`tools/export_schema.py`) is a naive, hand-rolled JSON
  Schema → `.ts` renderer**, not a full codegen library (no new dependency
  for a one-shot diffing aid). Known cosmetic limitation: every field renders
  as optional (`field?:`) in the generated `.ts` because every Pydantic field
  here has a default value (so none are JSON-Schema "required") — this is not
  a real mismatch with `ifind/types/resume.ts`, since v3's `extract()` always
  populates every key; it only affects the diff tool's rendering, not runtime
  output. Field names, nesting and enum values matched `ifind/types/resume.ts`
  exactly on inspection.

## Stage 3 — Environments

- **uv installed via `pip install --user uv`** rather than the official
  `irm .../install.ps1` script — same result (a user-local `uv.exe`, no admin
  rights), smaller surface (one trusted PyPI package vs. piping a remote
  script into PowerShell), and pip was already present.
- **Python 3.11.9 was already installed on this machine**
  (`AppData\Local\Python\pythoncore-3.11-64`); `uv venv --python 3.11` picked
  it up directly, no download needed.
- **`flashtext` over `pyahocorasick`** for the Aho-Corasick skill-dictionary
  matcher (Stage 11): `pyahocorasick` is a C extension that needs a compiler
  on Windows; `flashtext` is pure Python, same algorithm class, no build step.
  PROMPT.md §3 named both as acceptable alternatives.
- **`gliner2` deferred out of the default dependency group** into a new
  `gliner` extra (`uv sync --extra gliner`). It isn't used before Stage 10 and
  pulls in `torch`, a large download — no reason to carry that weight through
  Stages 3–9. The base `dependencies` list otherwise matches PROMPT.md §3's
  runtime list.
- **Checkpoint 3A, both items deferred by user request:**
  - Tesseract 5.x: not installed. RapidOCR loaded and ran with zero system
    install (`scripts/check_env.py` → "RapidOCR model load: OK"), so there's
    nothing blocking Stage 6 without it; Tesseract stays an option for the
    Stage 6 OCR benchmark if RapidOCR's accuracy on real scans doesn't hold up.
  - CUDA torch (~2.5 GB): not installed. `train` extras (`torch`, `gliner2[train]`,
    `transformers`, `datasets`, `peft`, `scikit-learn`, `lightgbm`) stay an
    opt-in group (`uv sync --extra train`), installed only when Stage 10
    actually starts fine-tuning.
- **`memray` dropped in favour of stdlib `tracemalloc`** for local memory
  profiling: memray doesn't support Windows, and this is a Windows dev
  machine (PROMPT.md §2). `eval/perf.py` (Stage 4) will use `tracemalloc` +
  `psutil` RSS sampling locally; memray can still be used later for the
  Stage 4.3 "constrained run inside Docker" check, since that runs on Linux.
- Default `uv sync --extra dev` installs ~638 MB total across ~50 small/medium
  packages (pymupdf, onnxruntime, opencv-python, scipy, pandas, playwright,
  reportlab, etc.) — no single package crossed the 500 MB threshold in
  PROMPT.md §1.3, so this wasn't treated as needing a checkpoint; flagged here
  for visibility since the sum is non-trivial.
