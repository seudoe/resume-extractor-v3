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

## Stage 2 (superseding edit) — `bert_vector`/`tfidf__vector` removed from `ParsedResumeData`

- User edited `types/resume.py` directly (outside my tool calls) to drop
  `bert_vector`/`tfidf__vector` from `ParsedResumeData`, and confirmed it was
  deliberate when I flagged the unexplained diff. Reasoning, confirmed against
  the live code: `ifind/lib/vectorizer.ts::encodeAndSaveUserResume` writes
  `"resume.bert_vector"` / `"resume.tfidf_vector"` — i.e. these vectors live
  as siblings of `parsedData` on the `Resume` document, computed by ifind's
  own vectoriser *after* parsing, never by the extractor. `ifind/types/resume.ts`
  nesting them inside `ParsedResumeData` doesn't match where the running code
  actually stores them.
  - v3's output contract is just `ParsedResumeData` as the extractor produces
    it; it has no business returning recommendation-system embeddings it
    never computes. **Decision: leave them out of `types/resume.py`
    entirely** (not relocated elsewhere in this schema) unless a concrete
    in-scope need for them shows up later. This is a deliberate, acknowledged
    divergence from `ifind/types/resume.ts` §Stage-2's "mirror exactly" goal,
    overridden by the user because the TS source of truth is itself
    structurally inconsistent with the runtime on this one point.
  - `tests/test_types.py`'s matching assertions were removed in the same edit;
    confirmed `pytest -q` still passes (12/12) after accepting the change.

## Stage 4 — Evaluation harness + gold set

- **`status` field added to gold JSON** (`scaffold`/`drafted`/`verified`),
  not in the original PROMPT.md §4.1 spec. Necessary: the first harness run
  scored all 31 gold files including 28 untouched empty scaffolds, which
  silently produced nonsense aggregate metrics (trivial 100% recall against
  empty gold, near-zero precision). `eval/run_eval.py::load_gold` now excludes
  `status == "scaffold"` by default.
- **v2 baseline reuses `resume-data/resume-extract-tested-jsons/` (25/31
  files)** instead of running `resume-extract` live in its own venv. Its venv
  exists but has nothing installed (`ModuleNotFoundError: spacy`), and
  reviving spaCy + SkillNer + sklearn-crfsuite for a reference-only baseline
  on a path we're retiring isn't worth the setup cost or risk (that venv is
  Python 3.14, and spaCy's 3.14 support is unverified). The 6 files with no
  pre-computed output (both DOCX variants, DemoGOAL.pdf, the 2 extra Asif
  variants, Internshala) are reported as "no candidate" rather than silently
  skipped or faked.
- **Gold id slugs include the file extension** (`demogoal_pdf` vs
  `demogoal_docx`), not just the stem — caught a real collision where
  `DemoGOAL.pdf` and `DemoGOAL.docx` both slugified to `demogoal` and
  overwrote each other's raw-text dump and draft scaffold.
- **Hallucination detection: substring match, falling back to
  `rapidfuzz.fuzz.token_set_ratio` at 0.9** for reordered/paraphrased text,
  rather than a stricter whole-string Jaro-Winkler compare. Chosen because
  grounding needs to tolerate re-formatting (e.g. a normalized date) without
  calling it a hallucination, while still catching genuinely invented text —
  validated on real v2 output (caught injected processing timestamps, mojibake,
  and a fabricated "Intermediate" skill-proficiency label with no basis in the
  source resume).
- **Link annotations matter more than visible icon text for gold labelling.**
  On Sambhav Mirajgaonkar's resume, the visible order next to the LinkedIn/GitHub
  glyphs ("sambhavm" then "sam-wlh-ds") suggested the opposite of the truth —
  the actual `https://www.linkedin.com/in/...` / `https://github.com/...` hrefs
  (pulled via `tools/_docio.py::extract_links`, PyMuPDF `get_links()`) showed
  "sam-wlh-ds" is the GitHub handle and the LinkedIn slug is "sambhav-m", not
  "sambhavm". This is exactly why PROMPT.md §8 says to resolve header links from
  annotations first — confirmed here even for a human doing the labelling, not
  just for the eventual rule-based extractor.
- **`eval/mappings/resumeextractbench.py` left as a stub (`NotImplementedError`)**
  rather than a guessed field mapping — downloading the dataset needs a dep not
  yet installed, and there's no extractor yet to benchmark. Per PROMPT.md's
  "measure, don't claim" rule, a guessed mapping risks silently wrong scores
  later; deferred to Stage 6 with the real schema inspected first.
- **Robustness suite (§4.4) deferred to Stage 5**, not built now: it tests
  ingest/OCR/pipeline behavior under corruption, rotation, rasterisation, etc.,
  none of which exist yet. Building the generator now would be untestable
  scaffolding (ponytail: "no scaffolding for later, later can scaffold for
  itself").

## Stage 5 — Ingestion → Document IR

- **`resume-data/` was reorganized by the user mid-project** (parallel LLM
  JSON-generation work): the 31 gold-seed PDFs moved from `resume-data/` to
  `resume-data/PDFs/AAA/` (some renamed: the Asif variants are now
  `Resume_Asif.pdf`/`Resume_Asif_4.0.pdf`/`Resume_Asif_GOAL-2.pdf`/
  `Resume_Asif_GOAL-intGoog-mar26.pdf`; new files appeared too —
  `26-9-30-csiHead.pdf`, `resume-block.pdf`, `sh_resu.pdf`, `Vedant_Resume (2).pdf`).
  Updated `tools/draft_gold.py::RESUME_DATA` to the new path. Both `.docx`
  gold files (`DemoGOAL.docx`, `Resume_Asif_GOAL.docx`) and
  `FlowCV_Resume_2026-08-02.pdf` no longer exist anywhere under `resume-data/`
  — user confirmed deleted on purpose. **Open gap:** Stage 5's exit check
  wants a DOCX ingest snapshot test and a FlowCV OCR-flag regression test
  against the real file; neither fixture exists right now. Substituted a
  synthetic DOCX (built in-test with `python-docx`) and a synthetic
  zero-text-layer PDF (a vector-drawn rectangle, no text) for the OCR-flag
  test — same failure modes, not the original files. Revisit if/when those
  files come back (e.g. the user's PDFs/AAA additions, or new DOCX gold).
- **`Span` gained an `icon_before: bool` field**, missing from the original
  Stage 2 IR. PROMPT.md §5 asks for it (icon-before-a-number signals
  phone/email/location) but Stage 2 didn't anticipate it when drafting the
  schema from spec text alone. Added once Stage 5 actually needed it, rather
  than guessing ahead of time in Stage 2.
- **Icon-glyph stripping (PUA range U+E000–F8FF + U+FFFD) doesn't catch every
  icon font.** Found on Sambhav's real resume: its embedded/subsetted font
  maps the LinkedIn/GitHub icon glyphs to ordinary Latin-1 codepoints (`ï`
  U+00EF, `§` U+00A7), not the PUA range, so they pass through as stray
  characters in `Line.text` (e.g. `"ï sambhavm | § sam-wlh-ds"`) instead of
  being stripped. **Decision: leave this uncaught, not worth widening the
  heuristic.** Widening it to "any lone non-ASCII character near a link"
  would false-positive on real accented names (é, ñ, etc.) — a worse bug
  than a cosmetic stray glyph. It's harmless in practice: Stage 8's header
  rules already resolve github/linkedin from `page.get_links()` (the actual
  href), never from visible icon text, exactly per PROMPT.md §8's own
  reasoning — confirmed on this file, where the link annotations gave the
  correct URLs while the visible icon order was actually misleading (see
  Stage 4's DECISIONS.md entry on the same resume).
- **No reading-order sorting in `ingest_pdf`.** Lines are emitted in
  PyMuPDF's native block/line order. Correct for single-column resumes,
  wrong for multi-column/sidebar ones — deliberately deferred to Stage 7
  (XY-cut + reading order), not duplicated here.
- **Dehyphenation deferred to Stage 7**, not implemented in Stage 5's text
  cleanup despite being listed under PROMPT.md §5's "Text cleanup" bullet.
  Merging a word broken across two physical lines requires knowing which
  line follows which in *reading order*, which doesn't exist until Stage 7.
  Doing it in Stage 5 (PyMuPDF's raw emission order) would misjoin lines in
  any multi-column layout.
- **Skipped the "% dictionary words" page-quality signal** (no wordlist
  dependency in the project) — kept just char-count-near-zero and
  `(cid:NN)`-artifact-ratio, which already cover the real failure mode this
  exists for (h.md's FlowCV: 0 extractable chars). Add a dictionary check
  only if a real resume slips through with dense-but-garbled text that these
  two miss.
- **DOCX hyperlinks collected at document level** (`part.rels`), not
  per-paragraph/run — python-docx doesn't expose per-run hyperlink targets
  without hand-parsing the raw `w:hyperlink` XML, and nothing downstream
  needs per-line precision yet (Stage 8 searches all of a page's links, not
  one line's).

## Stage 6 — OCR fallback

- **Data layout standardized by the user** (2026-10-03):
  `resume-data/{PDFs,JSONs,TEXTs,Extraction-details}/<CATEGORY>/<stem>.*`.
  `AAA` = the hand-picked real-resume gold-seed category; every other
  category = anonymized LiveCareer. Encoded once in
  `tools/_resume_data_layout.py` (path helpers + `GOLD_CATEGORY`);
  `tools/draft_gold.py` now reuses `TEXTs/AAA/<stem>.txt` when present
  (falls back to its own extraction) and takes PDFs from `PDFs/AAA/`.
  Stage 10's data builders should import the same module. `JSONs/` is
  LLM output: Stage 10 training data, or a scored baseline — never gold.
- **New eval baseline `--baseline llm`** (`eval/mappings/llm_json.py`) scores
  `JSONs/AAA/*` against hand-drafted gold like v2/ai. On the 3 drafted gold
  files the LLM gets name/email/phone 100% but linkedin/github 50%: it
  picked "sambhavm" (visible text beside the icon) as LinkedIn — the same
  icon-order trap found while hand-labelling, independent confirmation that
  link annotations must win over visible text (Stage 8).
- **OCR engine: RapidOCR only, no default declared "winner".** Tesseract
  isn't installed (Checkpoint 3A, deferred), so there's no A/B — PROMPT.md
  asks the benchmark to pick between them. `ocr/tesseract.py` not written
  (untestable without the binary; ponytail).
- **Benchmark (`eval/ocr_bench.py`, reports/ocr_bench_2026-10-04.md)**, 6
  text resumes, page 1, 2 ORT threads (HF free-tier budget), CER/WER vs the
  embedded text layer:

  | DPI | mean s/page | mean CER | mean WER |
  |---|---|---|---|
  | 150 | 24.4 | 0.154 | 0.317 |
  | 200 | 25.4 | 0.159 | 0.300 |
  | 300 | 23.9 | 0.169 | 0.267 |

  DPI doesn't move latency (recognition dominates: ~18 s of ~21 s at 2
  threads; 4–8 threads ≈ 10 s) and accuracy differences are within noise →
  **default 150 DPI** (cheapest render). CER is bimodal: clean resumes
  1.5–6 %, but Vedant Patil/LaTeX template ~35–42 % — mostly right-aligned
  dates/columns on the same visual line being emitted in a different order
  than the text layer (reading-order, Stage 7), plus OCR dropping inter-word
  spaces ("VEDANTPATIL"), not pure character errors.
- **Target miss, not accepted:** PROMPT.md §4.7 wants OCR p95 ≤ 6 s/page;
  measured ~24 s (and ~10 s with 4+ threads) on this machine, while the
  user's LLM pipeline was also running (noisy). Needs a decision: install
  Tesseract and benchmark it, try a different ORT version, or accept OCR
  as rare-path slow (text PDFs never hit it).
- `RX3_OCR_THREADS` env var (default 2) sets ORT intra-op threads.

## Stage 7 — Layout analysis and reading order

- **Algorithm (`layout/columns.py`)**: slab-first XY-cut. (1) Cut at every
  full-width horizontal gap (peels headers/footers); (2) adjacent slabs whose
  gutters overlap by ≥10 pt are re-joined and cut vertically *once*, so a
  two-column body reads column-by-column, not slab-by-slab; one-sided slabs
  join an open group; a row of column headings joins the group below it;
  (3) gutter-less slabs coalesce into one region. A vertical cut where one
  side starts far lower than the other (banner name over only the main
  column) reads the higher side first. First attempt (vertical-cut-first)
  put a banner header *after* the sidebar and fragmented sections — fixed
  after looking at rendered overlays, not by theory.
- **"Aligned cells" rejection** (`_is_aligned_cells`): a candidate gutter is
  *not* a column if the smaller side is mostly date-like text (left date
  column, right-aligned dates) or ≥75 % of its lines share a baseline with
  the other side (tables, right-aligned dates). Without it, "Acme Corp …
  2020–2022" rows split into a text column and a dates column.
- **Baseline merge** (`lines.py`): same-row segments merge left-to-right,
  tolerance 0.5 × the smaller line height.
- **Wrapped lines** (`bullets.py`): continuation = same size/bold, small gap,
  aligned to the bullet's text start (estimated by character proportion when
  glyph and text share a span) or hanging-indent, previous line ≥3 words,
  not ending in terminal punctuation or a date, and (reached the right
  margin or next starts lowercase); hyphen-ended lines always join and the
  hyphen is dropped when the next fragment is lowercase (ponytail: real
  compounds broken at the hyphen become one word). Single-token lines
  (stacked emails/URLs/handles) never merge.
- **Text-drawn rules** (lines of `____`/`----`) are dropped and set
  `rule_below` on the line above (seen in the Canva-style CIO templates).
- **`LineFeatures`** added to the IR (`rel_size`, `bold`, `all_caps`,
  `color_differs`, `rule_below`, `indent`, `gap_above` in body line-heights,
  `is_bullet`, `region`); body font = char-weighted mode of sizes (0.5 pt).
- **Bug found by tests**: a literal backspace char (heredoc `\b` escape) had
  silently broken a regex; scanned all sources for control characters.
- **Measured**: bullet accuracy `eval/layout_eval.py` = 41/41 gold bullets
  (3 drafted gold files) come out as exactly one line — tiny sample, and the
  gold bullets are mostly project descriptions. **Reading-order accuracy is
  NOT measured yet**: it needs the user's page-level yes/no (Checkpoint 7A)
  on `data/gold/reading_order/*.png`.
- **Known limits**: sidebar-vs-main order is heuristic (main first when the
  sidebar starts lower); icon-image placeholder text ("company.png") becomes
  junk lines; a lone date-ish right cell on a line with no baseline partner
  can still be read as a column; multi-line date cells ("Jan 2022 -" /
  "Present") leave "Present" as its own line (Stage 11's date parser must
  join them).

## Stage 6/7 revision — user review feedback + Tesseract (2026-10-04)

- **User's 7A review found one root problem: information from different
  fields got mixed into single lines.** Cases: education table rows
  (degree | institution | dates | CGPA) glued into one box and then glued
  *to each other*; skills rows ("Technical Tools / Soft Skills / Languages")
  merged; contact items (email | phone | linkedin | github) and AltaCV's
  contact grid merged. Root causes, all in Stage 7: (1) wrapped-line merge
  treated consecutive table rows as one wrapped paragraph; (2) baseline merge
  flattened cells into plain space-joined text, so "where one field ends and
  the next begins" was lost; (3) AltaCV's column-heading row was absorbed into
  the contact-row group.
- **Fixes:** cells are now explicit — gaps ≥ 1.0 × font size between spans or
  same-row segments are joined with `\t` (`CELL_SEP`) in `Line.text`
  (`layout/lines.py::cell_text`; DOCX table cells use the same separator).
  A line containing a tab is a row, never a wrapped line; the only continuation
  allowed is its *last cell* wrapping (aligned to that cell's start,
  `cell_starts`). First-line-indented paragraphs now merge (the Vicky
  "Career Objective" paragraph was split into 3 lines). A no-cut slab joins an
  open column group only if it sits entirely on one side. Stage 10 should
  split entries by `\t` cells instead of regex-guessing field boundaries.
- **Tesseract 5.5.3 is installed** (`C:\Program Files\Tesseract-OCR`, user
  note) — **resolves the Stage 6 open question and Checkpoint 3A's deferral.**
  Same 6 resumes, 2 threads (`OMP_THREAD_LIMIT=2`):

  | engine | DPI | s/page | mean CER | mean WER |
  |---|---|---|---|---|
  | RapidOCR | 150 | 24.4 | 0.154 | 0.317 |
  | RapidOCR | 300 | 23.9 | 0.169 | 0.267 |
  | Tesseract psm 3 | 150 | 1.4 | 0.140 | 0.218 |
  | Tesseract psm 3 | 300 | 2.2 | 0.130 | 0.205 |
  | Tesseract psm 4 | 300 | 2.1 | 0.134 | 0.215 |
  | Tesseract psm 6 | 300 | 2.0 | 0.136 | 0.218 |

  **Decision: Tesseract, psm 3, 300 DPI is the default OCR engine** (meets the
  §4.7 target of ≤ 6 s/page with ~3x margin; lowest WER). RapidOCR stays as an
  automatic fallback when no Tesseract binary exists (`RX3_OCR_ENGINE`
  overrides; `ocr/select.py::get_engine`). PSM choice is noise-level, so the
  default auto-segmentation stays. High-CER files (Vedant, LaTeX template,
  ~0.32–0.40 for both engines) are reading-order differences against the raw
  text-layer reference, not recognition errors.
- **OCR → layout works end to end**: an image-only Vicky resume yields the
  same education rows/cells as the text-layer version. Known OCR noise: bullet
  glyphs misread as a stray letter ("e", "9"); not normalised yet.
- Tesseract spans are per word with one size per line (tallest word × 0.9):
  per-word size made x-height-only words look tiny and ordinary word gaps look
  like cell gaps.
