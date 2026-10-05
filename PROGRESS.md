# Progress

## Current stage

**Stage 9 — Section segmentation.** Rules only, no classifier trained (target met; see DECISIONS). Stage 8: header & contact rules. Done; dev-set numbers in DECISIONS (linkedin/github 95/94 % vs 98 % target, one icon-only resume). Stage 7: layout Code + tests done; reading-order accuracy awaits Checkpoint 7A (user verifies overlays). Stage 6: OCR works, latency target missed (see below). Stage 5 notes: complete for PDF+DOCX; two exit-check
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

### Stage 6 — OCR fallback

- `src/rx3/ocr/rapid.py` (RapidOCR → IR lines, `source="ocr"`, font size from
  box height, bold unknown→False), `ocr/select.py` (`apply_ocr_fallback`: OCR
  only pages `page_quality` flags, renumber line ids). Default 150 DPI.
- `eval/ocr_bench.py` + `reports/ocr_bench_2026-10-04.{md,json}`: CER/WER/
  latency/RSS (numbers in DECISIONS.md). **RapidOCR ≈ 24 s/page at 2 threads
  vs the 6 s target — missed.** Tesseract not installed so no A/B.
- `tests/test_ingest.py`: end-to-end image-only PDF → OCR → readable text
  (replaces the missing FlowCV fixture). `pytest -q` → 23/23.
- Data layout standardization applied: `tools/_resume_data_layout.py`,
  `draft_gold.py` reuses `TEXTs/`, new `--baseline llm`
  (`reports/eval_2026-10-04_baseline-llm.md`).

### Stage 7 — Layout analysis and reading order

- `src/rx3/layout/{columns,lines,bullets,fonts,reading_order}.py`;
  `analyze_layout(doc)` reorders lines, merges baselines/wrapped bullets,
  reassigns ids L0..Ln, fills `Line.features`. IR gained `LineFeatures`.
- `tools/review_reading_order.py` → numbered, region-coloured page overlays
  in `data/gold/reading_order/` (+ `index.html`) for all 32 AAA PDFs.
- `eval/layout_eval.py`: bullet accuracy 41/41 on drafted gold (tiny sample).
- `tests/test_layout.py` (8 tests: columns, header-first, dates not split,
  left date column, wrapped+dehyphenated bullet, stacked contacts, features,
  text rules). `pytest -q` → 31/31.
- **🛑 Checkpoint 7A (answered with problems → fixed, awaiting re-check):** user found fields mixing (education rows, skills rows, contact items). Fixed via explicit `	` cells + no row-merging (see DECISIONS "Stage 6/7 revision"). Overlays regenerated.
- **Tesseract installed → now the default OCR engine** (2.2 s/page vs RapidOCR 24 s; lower WER). OCR latency open question closed.

### Stage 8 — Header and contact (rules only)

- `src/rx3/header/{zone,name,contact,links,location,gazetteer}.py`;
  `extract_header(doc, filename)` -> `HeaderResult(meta, provenance)`; gender
  always None.
- `eval/header_eval.py` + `data/gold/header/header_gold.json` (32 resumes,
  hand-labelled, **unverified**, gitignored). rx3: name/email/phone/state/
  country/postal 100 %, city 91 %, extras 100/100, linkedin 95.2 %,
  github 94.1 % (below 98 % target — one icon-only resume). LLM reference:
  linkedin 52 %, github 41 %.
- `tests/test_header.py` (10 tests). `pytest -q` -> 44/44.
- **Dev-set caveat:** rules were tuned on these same 32 resumes; held-out
  numbers need the extra resumes from Checkpoint 4A.

### Stage 9 — Section segmentation

- `src/rx3/sections/{synonyms,headings,segment}.py`: synonym table + fuzzy
  match, layout-supported heading detection, style propagation, inline
  headings, plain-document mode; `segment_sections(doc)` assigns every line
  one canonical section (`header` before the first heading).
- Found/fixed two Stage 7 layout bugs (heading glued under a multi-cell row;
  heading wrap-merged after a long unpunctuated line).
- `eval/section_eval.py` + `data/gold/sections/section_gold.json` (32
  resumes, hand-labelled, unverified): heading P/R 98.0/99.0, line accuracy
  **96.3 %** (target 95 %, dev set). `eval/section_livecareer.py`: held-out,
  184 LiveCareer resumes, precision 95.1 / recall 98.0 / canonical 97.0
  (weak labels, one template family).
- `tests/test_sections.py` (9) + layout regression test; `pytest -q` -> 54/54.
- **Learned classifier not trained** (rules met the target) -> Checkpoint 9A
  not triggered.

### Side quest — layout-aware text for LLM labelling

- `resume-data/layout_text.py` (standalone vendored copy of the rx3 reading
  pipeline + renderer) and `resume-data/process_resumes.py` integration (layout
  text, `--only/--category/--out-root/--limit/--dry-run`, `GROQ_MODEL`).
  Vendored port verified identical to rx3 on 92 PDFs; `pytest -q` -> 64/64
  (10 new in `tests/test_layout_text_vendor.py`).
- New eval hooks: `eval.llm_agreement`, `--baseline llm-groq`, Groq column in
  `eval.header_eval`. **Calibration not run yet** (needs Groq keys in
  `resume-data/.env`): see DECISIONS "Side quest".

### Stage 10 (part 1 of 3) — aligner, rules baseline, field eval

- `tools/livecareer_align.py`: HTML `div.paragraph` entries -> IR line ids.
  108-resume sample: alignment 99.5-100 % on every tagged field
  (`data/livecareer/aligned.jsonl`, gitignored). Tag findings in DECISIONS.
- `src/rx3/fields/rules/` (`dates.py`, `entries.py`, `lex.py`, `build.py`,
  generated `_title_words.py` via `tools/build_title_lexicon.py`):
  entry segmentation + field roles for work/education/projects/awards/
  certifications/affiliations/publications/languages/interests/skills/summary.
- `eval/fields_eval.py` (`uv run python -m eval.fields_eval`) + `run_eval
  --baseline rx3`. Rules, LiveCareer weak labels (108 resumes): work title
  recall 82.9 %, start 99.5 %, end 99.0 %; education degree 81.2 %, year
  85.6 %, **school 43.4 %** (plain rows glue degree+field+school into one
  cell). AAA agreement with LLM JSONs: work F1 56.6, education 75.1,
  projects 73.5, certifications 67.7, awards 41.5 (reference = LLM output).
- `tests/test_fields_rules.py` (3); `pytest -q` -> 67/67.
- **Not done yet:** synthetic template renderer (10.1), GLiNER2 zero-shot
  (needs `torch` + `gliner2`, a multi-GB install -> asked first), LoRA
  fine-tune (Checkpoint 10A), combine-by-eval + latency check.

### Stage 11 — Normalisation and enrichment

- `src/rx3/normalise/`: `periods.py` (`parse_period`, `finish_period`),
  `education.py` (canonical degrees, course split, CGPA/percentage),
  `bullets.py` (achievements vs responsibilities), `skills.py` + `_tech.py`
  (curated tech table, `_skill_names.txt` generated from
  `skill_db_relax_20.json` by `tools/build_skill_names.py`), `enrich.py`
  (work type, award/certification reclassification, project metrics/stack/links),
  `__init__.py` (`normalise(parsed, doc)`).
- Rules stage now attaches `_lines` (line ids) and `_heading` to each entry so
  Stage 12 grounding has provenance; `normalise` strips them from the output.
- `eval/fields_eval.py --extractor rules+norm`; `run_eval --baseline rx3`
  now runs rules + normalisation.
- Results (reports/fields_rules+norm_2026-10-04.md): work start/end **99.5 /
  99.0 %** (LiveCareer labels), education year **85.4 %** (below the 95 %
  target; misses are entry-boundary errors in messy plain-text education
  blocks, not parser errors), degree 80.3 %. Skills names vs LLM JSONs on AAA:
  P 63.2 / R 80.2 / **F1 69.0** (gold-3: F1 0.58); bullet-mention discovery
  changed nothing on AAA.
- Tests: `tests/test_normalise.py` (8, incl. 2 `hypothesis` property tests for
  `parse_period`: never raises/never fabricates a date, ordered-range
  round-trip); `pytest -q` -> 75/75.
- `hypothesis` installed into `.venv` (small) and added to dev deps in
  `pyproject.toml`; `uv.lock` not regenerated.
- Open: education date accuracy needs better entry segmentation (Stage 10
  GLiNER, still waiting on the torch install go-ahead); skills F1 is measured
  against LLM output, not gold.

### Stage 12 — Grounding, validation, confidence, pipeline

- `src/rx3/pipeline.py`: `extract(bytes, filename, debug=False, with_confidence=False)`
  runs ingest (+OCR fallback) -> layout -> sections -> header -> rule entries
  -> normalise -> ground -> dedupe/order -> confidence -> validate, with
  per-stage timings in `_debug.timings_ms`. `UnsupportedFormat` (-> 415) and
  `UnreadableDocument` (-> 422) for the API stage.
- `src/rx3/validate/`: `grounding.py` (every string must be found in a source
  line, exact or fuzzy >= 0.9 or ordered tokens; else dropped + logged; derived
  values — ISO dates, canonical degree/skill names, phones, enums, group names —
  inherit the entry's provenance), `clean.py` (drop empty entries, fuzzy dedupe
  >= 0.95, document order by line id, pydantic validate with per-entry
  fallback, never raises), `confidence.py` (+ `_calibration.json`).
- Provenance: `_debug.provenance` maps each grounded field path to source line ids.
- Confidence: calibrated on LiveCareer weak labels (455 resumes, fit on even
  ids, reported on odd): work title ECE 0.015 (mean conf .940 vs acc .952),
  period 0.012, education degree 0.085, institution 0.114 (weak). Everything
  else is a fixed prior, listed in `_debug.uncalibrated_confidence`.
- Exit check (`uv run python -m eval.pipeline_eval`, 224 resumes: all AAA +
  stratified LiveCareer): schema validity **100 %**; hallucination **0.18 %**
  (26 / 14,658 strings, independent PyMuPDF text + link annotations as source;
  target <= 0.5 %); determinism **byte-identical** across two processes with
  different `PYTHONHASHSEED`; 0 crashes.
- Latency (warm, this machine, single process): total p50 **99 ms**, p95 205 ms
  (ingest 26, layout 13, header 9, normalise 38 p50). OCR scans are extra
  (Tesseract ~2 s/page).
- `run_eval --baseline v3` (alias `rx3`) now runs the full pipeline on AAA. On the
  3 draft-gold files entity F1 is unchanged from the rules baseline (workHistory
  .67, education .67, projects .33...): the gap is entry segmentation, not
  grounding.
- Tests: `tests/test_pipeline.py` (5); `pytest -q` -> 80/80.
- Metric fixes found while measuring: `eval/metrics._norm` now NFKC-folds and
  strips curly quotes (the pipeline's text is NFKC + ftfy); hallucination
  exempts normalised values (documented in DECISIONS).
- Open: GLiNER stage (Stage 10) still not started — waiting on the torch
  install go-ahead; the 26 flagged strings are mostly header-link labels
  ("Portfolio"), small-caps names, and a few template rows.

### Stage 10 (part 2) — GLiNER2 zero-shot, combined per field

- Installed in `.venv` (user approved both experiments): CPU `torch 2.14.1`,
  `gliner2[local]` (+ transformers, peft), model `fastino/gliner2.5-base-v1`
  (downloaded on first load, HF cache). `pyproject.toml`: `gliner` / `slm` extras.
- `src/rx3/fields/gliner/`: per entry block (head lines, cells joined with ` | `)
  `batch_extract_json` with a per-section schema, `include_spans=True`; spans are
  mapped back to line ids (`_gliner` debug metadata keeps lines + confidence).
  `rules/build.py` got a `refiner` hook; `extract_rules(refiner=...)`.
- **Chosen configuration** (`COMBINE`, one joint cut-off): GLiNER overrides the
  rules value for company/title/location/institution/degree/course when its
  confidence >= 0.9. `eval/combine_search.py` (n=100 LiveCareer + AAA vs LLM
  JSONs): company 57.6 -> **84.3**, LiveCareer school 53.9 -> **77.0**, AAA
  institution 82.8 -> **89.8**, course 52.1 -> 61.5, AAA entity F1 work 56.6 ->
  **76.0**, education 75.1 -> **81.5**; costs: LiveCareer title recall 83.5 ->
  82.7, degree 83.6 -> 81.1. Pure GLiNER (no cut-off) is worse on title/degree.
- Pipeline: `extract(..., gliner=None)` / env `RX3_ENABLE_GLINER=1` (**off by
  default**). With it on (224 resumes): schema validity 100 %, hallucination
  **0.18 %**, byte-identical across processes, 0 crashes.
- **Latency miss**: GLiNER adds p50 **1.87 s** / p95 3.3 s per resume (2 threads;
  ~0.33 s per entry block); whole pipeline p50 1.97 s vs 99 ms rules-only. The
  PROMPT budget (~600 ms for the stage) is **not met**. Tried: dynamic int8
  (1.6x faster, but only 72.5 % field agreement with fp32 -> rejected); shorter
  schema text (22 % faster, 92 % agreement -> not adopted).
- Not done (Stage 10): synthetic template renderer, LoRA fine-tune (Checkpoint
  10A: not proposed/approved yet), token classifier (10B). The zero-shot gain
  suggests a fine-tune would help most on title/degree and could replace the
  0.9 cut-off.

### Stage 10 (part 3) — synthetic renderer, LoRA fine-tune, gold-32 (Stage 10 closed)

- **Gold**: all 32 current AAA PDFs now have a hand-drafted gold entry (`data/gold/drafts/*.json`, `status: drafted`, **unverified**,
  drafted by me from the raw text, not from LLM JSONs; helpers `tools/gold_fill.py`). Entries whose source PDF is gone from
  `resume-data/PDFs/AAA` (compressed/docx/renamed copies) are `archived` (kept, not scored); `flowcv` stays a scaffold (no PDF).
- **Synthetic renderer** (`tools/synth/`): 12 template families (single / two-column sidebars / banner / table / LaTeX-like /
  Indian-student / timeline / stacked plain / boxed ...), 1,800 resumes rendered through Chromium with exact ground truth,
  randomised fonts, date formats, section order, headings, degree names. Splits by family: 3 test families (jake, table_docx,
  banner) and 2 dev families never train. Two extra tagline-style families exist but are excluded by default (see below).
- **Training data** (`tools/build_gliner_data.py`): the rules stage's entry blocks (same text inference sees) labelled from the
  printed truth (synthetic) or the HTML tags (LiveCareer resumes disjoint from the eval pool, `aligned_train.jsonl`): 7,965
  train blocks (5,323 work / 2,642 education), 1,101 dev, 1,899 test (held-out families), 255 LiveCareer dev.
- **Fine-tune**: LoRA r=8 on encoder + task heads, local RTX 2050 (4 GB), CUDA torch 2.4.0+cu124. Hit and fixed: GPU OOM from one
  5,000-char outlier block (blocks capped at 600 chars), non-finite losses (bf16 made nearly every micro-batch non-finite;
  fp16 + skipping the ~1% non-finite micro-batches works). 3 epochs, 1,494 steps, 33 min; eval loss 155.8 -> 145.4 -> 142.4.
  Adapter (6.9 MB) shipped at `models/adapters/rx3-entry-lora/` (versioned, checksum in `models/MANIFEST.md`).
- **Results** (shipped adapter v1, cut-off 0.7):
  - Held-out template families (1,899 blocks), F1 zero-shot -> LoRA: title 71.4 -> **97.0**, company 83.3 -> **94.2**, location
    52.2 -> **89.1**, institution 78.0 -> **97.0**, degree 67.3 -> **96.9**, field of study 88.7 -> **95.4**.
  - LiveCareer dev blocks: institution F1 73.3 -> **90.3**, degree 69.7 -> 85.1, field 51.8 -> 83.3 (title recall stays low, 43 %
    at 83 % precision, because LiveCareer titles often sit outside the head block; the rules title is kept unless the model is >= 0.7).
  - Fields vs rules (LiveCareer n=100 + AAA vs LLM JSON): company 57.6 -> **86.3**, AAA title 78.0 -> **89.0**, location 8.3 -> **90.3**,
    LiveCareer school 53.9 -> **90.0**, degree 83.6 -> **94.1**; cost: LiveCareer work-title recall 83.5 -> 80.5 (-3 points, proxy labels).
  - **Gold-32 entity F1** (rules -> zero-shot GLiNER -> LoRA): work 0.593 -> 0.788 -> **0.801**, education 0.755 -> 0.818 -> **0.827**,
    projects 0.755 (rules tweak: plain-style titles + Courier "o" bullets, was 0.723), certifications 0.677, awards 0.635; skills F1 0.726.
- **Targets (entity F1 >= 0.90) are NOT met on gold-32** (dev numbers on unverified gold). Gap by section: work 0.80, education 0.83,
  projects 0.76 (entry boundaries of plain-style resumes; GLiNER is not applied to projects), certifications 0.68 and awards 0.64
  (no model; keyword rules only). Remaining work errors: stacked "company / tagline / title / dates" templates, company strings with
  a parenthetical, "Google | team" style rows. Next options: apply GLiNER/LoRA to projects, certifications and awards; verify the gold
  (Checkpoint 4B) so the gap is measured against truth; train on a larger and more varied real-resume set.
- **Production check** (CPU torch 2.14.1, 2 threads, 128 resumes: all AAA + LiveCareer sample, adapter merged into the base weights):
  0 crashes, schema validity 100 %, hallucination **0.15 %** (13 / 8,394 strings; header link labels and a small-caps name),
  byte-identical output across two processes, latency **total p50 1.02 s / p95 3.5 s** (GLiNER stage p50 0.96 s / p95 3.2 s; rules-only
  p50 0.1 s). The earlier "p50 +1.87 s" was measured while a stray background process was burning a core; the PROMPT's ~600 ms
  stage budget is still exceeded (about 1.6x), so GLiNER stays opt-in (`RX3_ENABLE_GLINER=1`).
- Robustness fixes found on the way: some blocks ("SSC | ... | 92.2%") gave NaN scores on CPU, which raised "cost_matrix contains NaN"
  inside GLiNER2 and crashed the extraction (17 of 224 resumes). `GlinerRefiner` now retries a failing batch block by block and
  leaves the rules value for a block that still fails. Unmerged PEFT adapters also ran ~3x slower; the adapter is merged at load.
- **A second adapter (v2) with two extra tagline-style families scored worse** (gold work F1 0.776, held-out location F1 66 vs 89)
  and was dropped; those families are excluded by default (`--include-extra`).
- **Redo with more data**: README section "Rebuilding the Stage 10 data and the GLiNER adapter" (about 45 min end to end on this GPU).

### Stage 13 — Small-LM experiment (done at the user's request; NOT shipped)

- `src/rx3/fields/slm/`: Qwen3-0.6B / 1.7B (`unsloth/*-GGUF` Q4_K_M, ~0.4 / 1.1
  GB in `models/slm/`, gitignored) through `llama-cpp-python 0.3.36` (prebuilt CPU
  wheel). Per entry block: numbered lines in, JSON out (`{line, text}` per field)
  enforced by a JSON-schema grammar, thinking off (`/no_think`), each answer
  grounded in the pointed line else dropped. Flag `RX3_ENABLE_SLM=1` (off).
- Result (same metrics, subsets noted; weak references):
  - Latency: median **5.0 s per entry block** on 2 threads (0.6B ~1-4 s, 1.7B
    4-6.5 s), i.e. ~25 s per resume vs 600 ms budget.
  - Qwen3-0.6B (n=15 LiveCareer + 32 AAA): work title recall 47.9 % (rules 87.3,
    GLiNER 84.5 on the same subset), school 37.5 %, degree-type 23 %.
  - Qwen3-1.7B (10 AAA + 6 LiveCareer, tiny): work recall 71.4 % (rules 89.3,
    GLiNER 85.7), company 90.3 % (GLiNER 91.7), title 90.3 % (rules 100), school
    50 % (GLiNER 75), degree/course 31 / 38 %.
- Verdict: loses to the encoder path on accuracy **and** fails latency by ~40x.
  Do not ship; revisit only with a fine-tuned small model on a GPU (Checkpoint
  13B, not requested). Failure modes: tiny model copies whole lines, picks null
  when allowed, mislabels institution vs degree.
- Tests: `tests/test_gliner_slm.py` (2, offline fakes); `pytest -q` -> 82/82.

## Next (superseded list below kept for history)

- Stage 6: OCR fallback (RapidOCR + optional Tesseract benchmark). Real
  regression test for the zero-text-layer case still wants a FlowCV-like
  fixture back if one resurfaces.
- Keep drafting gold for the remaining real resumes under `PDFs/AAA/`
  (`data/gold/drafts/*.json`, `status: "scaffold"`), then Checkpoint 4B.

## Open questions

- **Section gold verification (4B):** `data/gold/sections/section_gold.json`
  is my draft (heading text + canonical section per resume). Judgement calls
  worth a look: "Certificates & Awards" -> certifications, "Research"
  (LaTeX template, holds a job-like entry) -> workHistory, Simple_Hipster's
  "Short Resumé" -> workHistory / "Curriculum" -> projects, "SKILLS & OTHER" ->
  skills, "Awards & Certifications" -> certifications.

- **Header gold verification (4B):** `data/gold/header/header_gold.json` is
  my draft; please spot-check (name/email/phone/links/city per resume) — the
  header numbers can't be reported until then. Edge calls worth a look:
  Aagam (`https://linkedin.com/` root link -> linkedin null), Sambhav/Agneesh/
  Asif (Codeforces/CodeChef links under Awards counted as extra_links),
  Simple_Hipster (bare handles), Jenil (visible email vs stale mailto).

- **Checkpoint 7A:** open `data/gold/reading_order/index.html`; for ~10 pages say yes/no per page (is the numbering = how a human reads it?). Suggested: AltaCV p1+p2, Simple_Hipster_CV, Entry_Level_LaTeX, chief-information-officer-cio3, SambhavMirajgaonkar p1, Resume_Asif p1, AryanNiravShah, Jenil_Shah, sh_resu. Stage 7's "≥95 % on two-column files" target can't be claimed until then.

- ~~OCR latency~~ RESOLVED 2026-10-04: Tesseract installed, default engine, 2.2 s/page. (old note:) RapidOCR ≈ 24 s/page vs ≤ 6 s target. Options: (a) install Tesseract (revisit Checkpoint 3A, admin install) and benchmark it, (b) try other onnxruntime versions/models, (c) accept OCR as a rare slow path. Re-measure when your LLM job isn't running.

- Real DOCX and FlowCV-equivalent fixtures are missing; Stage 5's exit check
  is satisfied with synthetic substitutes only. Revisit if those files come
  back or new DOCX gold is added.
- Checkpoint 4B (gold verification) is open — nothing in `reports/eval_*`
  should be treated as a reported number until the user has reviewed the
  drafted gold JSON against the source resumes.
- Asif's resume(s) aren't gold-drafted yet, so the AI-path baseline currently
  only covers 2/3 available matches (Vedant, Sambhav).
