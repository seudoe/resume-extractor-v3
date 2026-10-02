# Progress

## Current stage

**Stage 4 — Evaluation harness + gold set.** Harness built and running end-to-end;
gold-labelling is partial (3/31 hand-drafted) and ongoing. Pending user commit.

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

### Stage 4 — Evaluation harness + gold set

- **Checkpoints asked up front:** 4A (more real resumes) — user will collect
  them on their own timeline, proceed with the current 31 meanwhile. 4C (AI-path
  export) — user already has `../mongo-runner/output.json` from a Mongo export;
  3 of its 20 records match our gold resumes by name (Vedant Patil, Sambhav
  Mirajgaonkar, Asif Shershah — the rest are demo/seed accounts, not real test
  resumes). 4D (acceptance targets) — PROMPT.md §4.7 confirmed as-is.
- **`tools/draft_gold.py` + `tools/_docio.py`**: scaffolds `data/gold/{raw,drafts}/`
  from all 31 real resumes in `../resume-data/`, dumping plain text (PyMuPDF/
  python-docx) plus hyperlink annotations (critical: several resumes' github/
  linkedin icons have no readable text without the actual href — confirmed on
  Sambhav's resume, where the icon order visually suggested the opposite
  platform from what the link annotation actually proved). Tags 6 near-duplicate
  files (4 Vicky, 2 Asif-ish, DemoGOAL pdf/docx) via `near_duplicate_of`.
  Found and fixed a real id-collision bug: `DemoGOAL.pdf`/`DemoGOAL.docx` both
  slugified to `demogoal`, silently overwriting each other — slug now includes
  the extension.
- **Gold drafted and validated against the Stage 2 schema (3/31):**
  `sambhavmirajgaonkarresume_pdf`, `vedant_patil_pdf`, `simple_hipster_cv_pdf`
  — hand-transcribed by reading the extracted text (and, for one ambiguous
  icon-link case, the actual rendered PDF page) and link annotations. The other
  28 are `status: "scaffold"` (empty placeholders, not scoreable) pending
  further drafting. **None are verified yet — Checkpoint 4B (user review) is
  still open; no number in this stage's reports is a reported accuracy claim.**
- **`eval/matching.py`**: Hungarian assignment (`scipy.optimize.linear_sum_assignment`)
  on Jaro-Winkler key-field similarity, per PROMPT.md §4.2.
- **`eval/metrics.py`**: scalar exact/fuzzy fields, entity P/R/F1 + per-subfield
  accuracy (dates compared as (year, month)), token-F1 for text lists, skills
  set F1, hallucination rate, schema validity. Sanity-checked against real v2
  output — correctly caught genuine v2 defects (mojibake text, raw processing
  timestamps leaking into output fields, a fabricated "Intermediate" skill
  proficiency the source resume never states).
- **`eval/perf.py`**: generic timing (p50/p95 via manual percentile, no new dep)
  + `tracemalloc`/`psutil` memory helpers, ready to wrap `rx3.pipeline.extract`
  once it exists. `memray` deliberately not used — doesn't support Windows.
- **`eval/mappings/v2.py`**: reuses the pre-computed baseline outputs already in
  `../resume-data/resume-extract-tested-jsons/` (25/31 files) rather than
  reviving the old extractor's broken venv (confirmed `ModuleNotFoundError:
  spacy` — ponytail: not worth fixing a deprecated path for a reference-only
  baseline). Maps v2's `_meta` → `metaDetails` the same way
  `ifind/lib/resumeParser.ts`'s `normaliseHFOutput` does.
- **`eval/mappings/ai_path.py`**: loads `../mongo-runner/output.json`, matches
  by name.
- **`eval/mappings/resumeextractbench.py`**: stub only — downloading needs a
  dependency not yet installed and there's no extractor to benchmark against
  yet; deferred to Stage 6 (OCR) with a clear `NotImplementedError` rather than
  a guessed field mapping.
- **`eval/report.py` + `eval/run_eval.py`**: `uv run python -m eval.run_eval
  --set gold --baseline v2|ai` runs end-to-end and writes
  `reports/eval_<date>_baseline-<name>.{md,json}`, with a compare-to-last delta
  section. First reports generated: `reports/eval_2026-10-02_baseline-v2.md`
  (3/3 drafted gold scored) and `..._baseline-ai.md` (2/3 scored — Asif isn't
  drafted yet).
- **Real bug caught and fixed before it corrupted every metric:** the first
  harness run silently scored all 31 gold files, including the 28 untouched
  empty scaffolds, which made every entity-recall number look artificially
  perfect (empty gold ⇒ trivial 100% recall) and every precision number look
  artificially terrible. Added `status: "scaffold" | "drafted" | "verified"`
  to gold JSON and excluded scaffolds from scoring entirely. Reports now say
  how many files were actually scored vs. skipped.
- **`tests/test_eval_metrics.py`**: 9 tests on matching/metrics (alignment,
  not-applicable scalar fields, perfect/empty entity sections, token-F1,
  skills F1, hallucination true/false positive). `pytest -q` → 12/12 passed.
- **robustness suite (§4.4) deliberately deferred**: it exercises ingest + OCR
  + the pipeline together, none of which exist before Stage 5 — building it now
  would be untestable scaffolding. Will be built alongside Stage 5's ingester.
- **Unplanned fix mid-stage:** user had independently edited `types/resume.py`
  to remove `bert_vector`/`tfidf__vector` from `ParsedResumeData` (and
  `tests/test_types.py` to match) between sessions. I flagged the unexplained
  diff rather than assuming it was mine or reverting it; user confirmed it was
  deliberate — see DECISIONS.md for why (those vectors live on `Resume`,
  sibling to `parsedData`, computed by `ifind/lib/vectorizer.ts` after parsing,
  never by the extractor). Regenerated `types/generated/resume.schema.json`/`.ts`
  to match; `pytest -q` still 12/12 after the change.

## Next

- Keep drafting gold for the remaining 28 real resumes (`data/gold/drafts/*.json`,
  `status: "scaffold"`), then Checkpoint 4B (user verifies all of it).
- Stage 5: Ingestion → Document IR (PyMuPDF + DOCX), the first real pipeline
  code. The robustness-suite generator (§4.4) gets built alongside it.

## Open questions

- Checkpoint 4B (gold verification) is open — nothing in `reports/eval_*`
  should be treated as a reported number until the user has reviewed the
  drafted gold JSON against the source resumes.
- Asif's resume(s) aren't gold-drafted yet, so the AI-path baseline currently
  only covers 2/3 available matches (Vedant, Sambhav).
