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
