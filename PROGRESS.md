# Progress

## Current stage

**Stage 5 — Ingestion → Document IR.** Complete for PDF+DOCX; two exit-check
fixtures (DOCX gold, FlowCV) are missing from disk and substituted with
synthetic equivalents. Pending user commit. Gold-labelling (Stage 4, 3/31
hand-drafted) continues separately/in parallel.

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

### Stage 5 — Ingestion → Document IR

- **`src/rx3/ingest/pdf.py`**: `page.get_text("dict")` → `Document` IR, keeping
  per-span size/bold (flag bit 16 OR font-name hints like "Bold"/"Black")/
  italic (bit 2)/font/color/bbox; `page.get_links()` → `Link`s (real hrefs,
  not visible text); `page.get_drawings()` → `Drawing`s (rule detection for
  Stage 9). Text cleanup: NFKC, `ftfy`, PUA-glyph/U+FFFD stripping with
  `icon_before` flagging. No reading-order sorting (Stage 7) or cross-line
  dehyphenation (also Stage 7 — needs reading order first).
- **`src/rx3/ingest/docx.py`**: paragraphs/runs → `Line`s with pseudo-bbox
  (sequential y, x from indent); heading styles forced bold; list styles get
  a bullet glyph prepended; tables flattened to `"cell | cell"` lines;
  hyperlinks collected from `part.rels` (document-level, not per-run).
- **`src/rx3/ingest/quality.py`**: per-page OCR-need flag from char-count and
  `(cid:NN)`-artifact ratio (no dictionary-word check — no wordlist dep, and
  these two already catch the real failure mode).
- **`src/rx3/__init__.py`**: bootstraps `types/` onto `sys.path` on import
  (same pattern as `conftest.py`), so `rx3` submodules can `from ir import ...`
  without dot-importing `types` as a package.
- Added `Span.icon_before: bool` to `types/ir.py` — PROMPT.md §5 needed it,
  Stage 2 hadn't anticipated it.
- Tested against 6 real resumes in `resume-data/PDFs/AAA/` (no crashes,
  sensible bold/size/links/drawings) and a synthetic DOCX + synthetic
  zero-text PDF (real DOCX/FlowCV fixtures are gone — see below).
  `tests/test_ingest.py`: 10 tests, including a real link-annotation
  assertion (confirms github/linkedin hrefs extracted correctly) and an
  OCR-flag assertion. `pytest -q` → 22/22 passed project-wide.
- **`resume-data/` got reorganized by the user mid-session** (their parallel
  LLM-JSON-generation work): all 31 gold-seed PDFs moved to
  `resume-data/PDFs/AAA/` (some renamed, a few new ones added). Fixed
  `tools/draft_gold.py`'s path. **Both DOCX gold files and
  `FlowCV_Resume_2026-08-02.pdf` no longer exist anywhere** — user confirmed
  deleted on purpose. Stage 5's exit check wanted real snapshot/regression
  tests against these; substituted synthetic equivalents (see DECISIONS.md)
  — this is a real gap, not fully equivalent to testing the original files.
- **Real icon-glyph limitation found** (not a bug, a documented gap): one
  resume's icon font subset maps icons to ordinary Latin-1 codepoints, not
  the PUA range, so they aren't stripped. Confirmed harmless — Stage 8 will
  resolve github/linkedin from link annotations, never from icon text. See
  DECISIONS.md for why widening the heuristic would be worse (false
  positives on real accented names).
- **LLM-generated PDF→JSON pairs** (user is producing these in parallel,
  outside `resume-extractor-v3/`): valid for Stage 10 **training** data only.
  PROMPT.md §1.5/§4.1 bar hosted-LLM output from ever being `data/gold/`
  (eval-only, hand-verified) — flagged to the user when asked.

## Next

- Stage 6: OCR fallback (RapidOCR + optional Tesseract benchmark). Real
  regression test for the zero-text-layer case still wants a FlowCV-like
  fixture back if one resurfaces.
- Keep drafting gold for the remaining real resumes under `PDFs/AAA/`
  (`data/gold/drafts/*.json`, `status: "scaffold"`), then Checkpoint 4B.

## Open questions

- Real DOCX and FlowCV-equivalent fixtures are missing; Stage 5's exit check
  is satisfied with synthetic substitutes only. Revisit if those files come
  back or new DOCX gold is added.
- Checkpoint 4B (gold verification) is open — nothing in `reports/eval_*`
  should be treated as a reported number until the user has reviewed the
  drafted gold JSON against the source resumes.
- Asif's resume(s) aren't gold-drafted yet, so the AI-path baseline currently
  only covers 2/3 available matches (Vedant, Sambhav).
