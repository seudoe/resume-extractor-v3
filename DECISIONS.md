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

## Stage 8 — Header and contact (rules only)

- **Pipeline order for the header**: ingest -> (OCR) -> `analyze_layout` -> `extract_header`.
  Name scoring needs `Line.features`; links need the page `Link` boxes mapped
  back to the line they sit on (`_line_at`).
- **Header zone** (`header/zone.py`): page-1 lines from the top to the first
  section heading, any block under a CONTACT-style heading (sidebars are read
  after the main column, so "Edinburgh, United Kingdom" under CONTACT sits
  far from the top in reading order), and any page-1 line carrying contact
  data. A phone-like pattern must not be a date range ("2017 - 2021" was
  pulling education lines into the header and inventing a location).
- **Name**: best score over cells (tab-split) in the top 35 % of page 1:
  3 x relative size (capped), bold, 2-3 tokens preferred, earlier is better,
  + filename and email-local-part overlap. Excluded: digits/@/URLs, resume
  furniture words and job-title words. Small-caps gaps are fixed ("M OHD" ->
  "MOHD", "M ohd" -> "Mohd"); a second line at the same large size joins
  ("M ohd Asif" / "Shershahvadi"). Casing preserved.
- **Email: visible text first, `mailto:` only as fallback.** Two resumes in
  the gold set (Jenil, Pooja) carry a stale `mailto:` copied from a template
  while the visible address is the candidate's own. (Contrast with links,
  where the annotation wins — see below.)
- **Phone**: `phonenumbers` (IN, then no region) at VALID leniency, >= 10 raw
  digits, date ranges and digits inside emails removed first; E.164 out. Last
  resorts: POSSIBLE with an explicit "+CC", then a digits-only "+CC..."
  (template placeholders like "+1-234-456-789" that aren't valid numbers).
- **Links**: annotations first (they carry the real URL when the visible text
  is an icon or just "LinkedIn"), then URL regex over text, then explicit
  `github: handle` labels (handle kept as written — no URL invented).
  linkedin = `/in/` or `/pub/` profile only (a `/posts/` link is skipped);
  github profile = exactly one path segment (a `github.com/user/repo` is a
  project link). **Coding-platform profiles (Codeforces, CodeChef, LeetCode,
  Kaggle, HackerRank, ...) count from anywhere in the document** — they're
  always the candidate's own, and Sambhav's/Agneesh's sit under Awards — but
  linkedin/github/portfolio links must be in the header zone or on a contact
  line, or a project demo would become a "portfolio". Bare-domain regex
  requires a >= 3-char label and no `.tech`/`.site`/`.xyz` TLDs: `B.Tech`
  was matching as a domain.
- **Location** (`header/gazetteer.py`, hand-curated India-heavy list + common
  world cities/countries/US states, not GeoNames): only what the text says;
  city is never inferred from a state nor a country from a city. **Last city
  match wins** in a line ("Andheri, Mumbai, Maharashtra" -> Mumbai), US-style
  "City, ST" abbreviations kept as written, 6-digit PIN only on a line that
  already has a city/state. Candidate lines = header zone, so a college name
  under Education can't become the candidate's city. The Kerala city list
  (Ernakulam, Kollam, ...) was added *after* seeing a miss on a dev resume —
  generic data, but note it.
- **`gender`** is always `None` (PROMPT.md §1.7), covered by a test.
- **Header gold** (`data/gold/header/header_gold.json`, gitignored: PII) was
  labelled by me from raw page text + link annotations, deliberately not
  from extractor/LLM output, for all 32 AAA resumes. **Unverified.**
- **Measured** (`eval/header_eval.py`, reports/header_eval_2026-10-04.md),
  32 resumes: name 100 %, email 100 %, phone 100 % (26 with a number),
  state 100 %, country 100 %, postal 100 %, city 91.3 %, extra_links P/R
  100/100, **linkedin 95.2 % and github 94.1 % — below the 98 % target.**
  Reference LLM JSONs on the same gold: linkedin 52.4 %, github 41.2 %,
  extra_links P/R 50/19 (they emit "Linkedin", markdown-wrapped Google-search
  URLs, or invent a country on 17 resumes that don't state one).
- **Why the two target misses**: all three link misses + city misses are
  Simple_Hipster_CV (LinkedIn/GitHub shown as an icon + bare handle with *no*
  annotation and no readable platform text — recoverable only by recognising
  the icon image; skipped) and two cities outside the gazetteer ("Bay Area",
  "Grand Rapids"). One resume out of 21/17 is 95 %/94 %, so the targets can't
  be met on this set without icon recognition.
- **Caveat on every number above**: the rules were tuned while looking at
  these same 32 resumes (stale-mailto policy, platform-links-anywhere,
  contact-heading blocks, Kerala cities all came from failures here) and the
  gold is mine and unverified. These are development-set numbers; a held-out
  set (the 20-30 extra resumes from Checkpoint 4A) is the real test.
- **Bugs caught while building**: a heredoc turned `\b` into a literal
  backspace in two regexes (again); a mangled docstring; `urlparse` raising
  on malformed targets (guarded in both the extractor and the eval).

## Stage 9 — Section segmentation

- **Rules only; the learned heading classifier was NOT trained, and Checkpoint
  9A was therefore not needed.** PROMPT.md says models only where rules
  measurably fail. The rules meet the §4.7 target on the gold set and hold up
  on an independent held-out check (below); the failures that remain are
  template-specific naming ("Short Resumé", "Curriculum"), which a classifier
  trained on LiveCareer (one plain template family) would not fix. Revisit if
  the extra resumes from Checkpoint 4A show heading misses the rules can't
  explain. If it's ever built: train with scikit-learn (`train` extra), export
  coef/intercept as JSON and run inference in numpy so the runtime image stays
  free of sklearn.
- **Pipeline** (`src/rx3/sections/`): `synonyms.py` (table + rapidfuzz match +
  keyword fallback), `headings.py` (`detect_headings`), `segment.py`
  (`segment_sections` -> `Section(name, heading, line_ids, inline)`,
  `line_sections`). Every line gets exactly one canonical section; the block
  before the first heading is `header`; unknown headings become `other`, never
  glued onto the previous section.
- **Heading rules**: a short non-bullet line whose text reads as a known
  heading. Exact normalised match scores 100; fuzzy near-matches are capped at
  99 and must match the resume's own heading style (a near-match in another
  style is an entry subtitle: "Personal Project" under a project title). Layout
  support = bold / caps / larger / coloured / rule below, or <= 2 words.
  **Style propagation** finds unknown headings: a short line with a style
  signature that occurs >= 2 times among the known headings (sidebar tags and
  main-column headings are separate styles) plus a strong cue (caps / rule /
  bigger / coloured); an unstyled signature never counts as a "style". A
  keyword fallback ("University Project" -> projects, last keyword wins)
  classifies those style-found headings.
- **Inline headings** ("Languages<tab>English, Hindi", "Hobbies: ...") are
  one-line sections and the previous section carries on. They open a section
  only if the label is styled (first span bold / caps), written `Label:`, or the
  current block is a catch-all (header, or a *synonym* `other` such as
  ADDITIONAL). Otherwise they're sub-rows ("Soft Skills", AltaCV's plain
  "Leadership<tab>Problem Solving" tags). A programming-languages row inside
  Skills ("Languages: C, C++, Java") stays in Skills. A "SKILLS" heading
  immediately followed by "Hard Skills:" is one section.
- **Plain documents** (every LiveCareer PDF: headings have no styling at all):
  detected when none of the exact-match headings carries a cue. Then an exact
  synonym alone on a line is a heading at any length ("Education and
  Training"), title-case 2-5 word lines with a *strict* keyword (skills,
  education, awards...) are headings, but: colon-terminated lines ("Accomplishments:"
  is a sub-label inside a job) and ambiguous one-word synonyms (Leadership,
  Research, Volunteer, Activities, Training, ...) are not, since they are skill
  tags there.
- **Region reset**: a new column starting without its own heading doesn't
  inherit the previous column's last section (not applied to the header block
  or a headless `other`).
- **Two layout bugs found through this stage** (both fixed in Stage 7 code):
  a heading under a multi-cell row ("... | Score: 90.0%" then "PROJECTS") was
  glued onto it because the row-alignment alternative still matched the row's
  left edge; and a heading right after a long unpunctuated line ("Additional
  Information" after a comma-separated skills line) was wrap-merged into it
  (an exact heading match is now never a continuation; a short ALL-CAPS line
  after mixed case isn't either). Regression tests added.
- **Synonym table** is built from headings in the gold resumes + a 24-resume
  LiveCareer sample + general resume vocabulary. Dropped over-generic entries
  ("tools", "work", "details", "links" ...) and the template-specific "short
  resume", "overview", "specialization". Words added after seeing LiveCareer
  misses are general ("skill highlights", "activities and honors",
  "core accomplishments"); "strengths", "relevant coursework" and "most proud
  of" were added after seeing the gold set, so they are tuned.
- **Measured** (reports/section_eval_2026-10-04.md): gold set (32 resumes, my
  hand-labelled headings in layout order, **unverified; rules tuned on it ->
  development set**): heading P/R 98.0 / 99.0 %, canonical section on matched
  headings 98.5 %, **line-level section assignment 96.3 % (1450/1506) vs the
  95 % target**. Worst files: Simple_Hipster_CV 55 %, Entry_Level LaTeX 88 %
  (template-specific headings; "Research" as workHistory vs our publications
  mapping). **Held-out** (reports/section_livecareer_2026-10-04.md, 184
  LiveCareer resumes, HTML `sectiontitle` weak labels, not used for tuning
  except the vocabulary above): heading precision 95.1 %, recall 98.0 %,
  canonical 97.0 %. First held-out run was recall 78.6 %: plain-document
  handling and the merged-heading bug accounted for the difference.
- **Caveats**: LiveCareer is one template family with noisy titles (some
  "false positives" are real headings the HTML didn't mark, e.g. a repeated
  "Accomplishments"), so it says little about Canva/two-column layouts; the
  gold-set number is optimistic. `PROFILES` (a links block) is read as
  `summary` by the fuzzy singular/plural match.

## Side quest (between Stage 9 and 10) — layout-aware text for the LLM-labelled benchmark

- **Why now**: ~2,480 PDFs still need LLM JSON; Gemini reads the PDF but has few
  calls/day, Groq has many but takes text only, and plain `pypdf` text drops
  position/size/columns. The LLM JSONs are benchmarks/training data, so the
  text sent to Groq should carry layout. Done before Stage 10 because Stages
  10-12 consume the reading pipeline; they don't change how a PDF is read
  (any later edge-case fixes get a new `FORMAT_VERSION`, stored per JSON).
- **`resume-data/layout_text.py`** (user chose a **standalone** copy over
  importing from this repo, so `process_resumes.py` keeps its own env):
  vendored port of rx3 ingest + Tesseract OCR fallback (CLI, no pytesseract) +
  cells + XY-cut columns + wrapped bullets + features, needing only `pymupdf`
  (`ftfy` optional). Renders `L12 | x1.8 B CAPS RULE | text ⇥ cell` lines in
  reading order with `[region N]` markers, plus a LINKS list (link target + the
  words it covers + host line id). It adds **facts, not interpretations**: no
  section labels, no header guesses, so the benchmark isn't pre-shaped by our
  own extractor's opinions. A legend teaches the LLM the notation; "B" is
  dropped when >85 % of lines are bold (some fonts flag every span).
- **Drift guard**: `tests/test_layout_text_vendor.py` compares the vendored
  pipeline to rx3 line-for-line and feature-for-feature on 8 AAA resumes, checks
  the generated heading-phrase set equals `rx3.sections.synonyms`, and checks
  the renderer carries cells/links/headings. A one-off check over 92 PDFs (AAA +
  60 random LiveCareer) found 0 differences. The file lives outside this git
  repo (`resume-data/`), so it isn't versioned here.
- **`process_resumes.py` changes** (backup kept only in the session scratchpad):
  layout text replaces `pypdf` text (pypdf only as a fallback; `text_format` +
  `text_chars` go into `Extraction-details`); Groq model from `GROQ_MODEL`
  (default unchanged) with a token-budget warning; new flags `--only`,
  `--category`, `--out-root`, `--limit`, `--dry-run`. `--out-root` keeps a
  calibration run from touching the existing JSONs.
- **Size**: schema prompt ~0.8k tokens; layout text on AAA mean ~1.5k / max
  ~2.7k tokens, on a LiveCareer sample mean ~2.2k / max ~4.5k (x1.3-1.7 the
  chars of pypdf text). With a ~2.5k-token reply, the default 8k-window Groq
  model will fail on the longest few percent; a larger-context model is advised.
- **Known weak spot**: sidebar-heavy templates (e.g. Simple_Hipster) still read
  imperfectly (a heading in one region, its content in the next); Gemini on the
  real PDF handles those better, so stratify by `llm_used`/`input_type`.
- **Calibration plan (not run: needs the user's Groq keys)**:
  `process_resumes.py --only GROQ --category AAA --out-root calibration/groq-layout`,
  then `eval.llm_agreement` (Groq-layout vs Gemini-PDF agreement),
  `eval.header_eval` (new Groq column vs hand header gold) and
  `eval.run_eval --baseline llm-groq`. Only then the bulk run.

## Stage 10 (part 1) — aligner, rules baseline, field eval

- **LiveCareer HTML findings** (Stage 10.1 asked to inspect first): one
  `div.paragraph` = one entry; spans carry a 4-letter code in their id.
  Work: `JSTD` start, `EDDT` end, `JTIT` title, `COMP` company, `JCIT/JSTA`
  city/state, `JDES` bullets (`<li>`). Education: `GRYR` year, `DGRE` degree,
  `STUY` programline, `SCHO` school (`companyname_educ`), `FRFM` field.
  **Company names and cities are anonymised** ("Company Name", "City") in
  every sampled resume, so no company/location labels exist; titles, dates,
  degrees, programs and bullets are real. The aligner skips placeholder
  values. `field` often repeats `program` plus honours/GPA text (noisy).
- **Alignment**: each entry is aligned forward only, from the end of the
  previous entry (floor reset to the section's heading line, taken from our
  own Stage 9 segmentation). A first version searched the whole document and
  matched "Accountant" to the page-top headline; ordering fixed it. First
  hit with similarity >= 0.9 wins. Coverage (108 resumes, stratified):
  title 514/514, start 485/485, end 477/477, bullets 2917/2923, degree
  200/200, school 201/202, year 159/159.
- **Rules baseline design**: an entry = head (title/company/date lines) +
  body (bullets). New entry on a date range or a repeat of the first head's
  style once the body started; a second date range always opens a new entry;
  a lone year inside a sentence ("2004 Employee of the Year") does not; in
  plain documents the title line sits *above* its date line, so up to two
  title/company-like trailing lines of the previous body are pulled forward.
  Roles from head cells: title by head-noun lexicon (generated from LiveCareer
  `jobtitle`, 209 words, count >= 4, plus ~40 hand-added words), company by
  suffix words, location by "City, State". LiveCareer placeholders ("Company
  Name", "City , State") are stripped from head text. Education: degree word
  list, institution keyword runs ("X University", "University of X"), one row
  listing several degrees is split at each "Master/Bachelor/... of".
- **Measured** (reports/fields_rules_2026-10-04.md; weak labels, rules not
  fitted to gold): work title 82.9 %, dates ~99 %, education degree 81 %,
  school 43 %. Biggest failure class: plain rows where field-of-study and
  school run together ("Systems Support Tulane University"); needs a model
  (GLiNER) or an institution gazetteer. Not tuned further on purpose.
- **Caveats**: (1) AAA agreement uses LLM JSON as reference and the LLM wrote
  dates as "Aug 2024", so date columns there are not comparable (the
  3 hand-drafted gold files use ISO). (2) `run_eval --baseline rx3` shows
  hallucination 10 %: the metric counts normalised ISO dates as unseen
  strings; Stage 12 grounding keeps provenance of the raw text instead.
  (3) Simple_Hipster-style sidebars fail at section level (Stage 9), so
  entries are empty there. (4) Gold is still 3 drafted files; the weak-label
  and LLM-agreement numbers are proxies until gold grows (Checkpoint 4B).
- **Still open in Stage 10**: synthetic renderer (needed for fine-tune data),
  GLiNER2 zero-shot, LoRA fine-tune (Checkpoint 10A), combine-by-eval and
  the latency budget. GLiNER2 needs `torch` (large install), so it waits for
  the user's go-ahead.

## Stage 11 — normalisation and enrichment

- **Dates**: `parse_period` outputs `YYYY-MM-01` (bare year -> `-01-01`,
  season/quarter -> its first month). Empty policy: unknown start `""`, unknown
  end `None`, never today's date. A lone date is a *start* for work and an
  *end* for education; "Expected ..." is always an end. `isCurrent` is True for
  Present/Current, and for an education end in the future (student still
  enrolled; matches the gold drafts). Seasons: spring 3, summer 6, fall/autumn 9,
  winter 1 (approximation, documented). Property tests (`hypothesis`) guard
  never-raises, never-fabricates and ordered-range round-trip.
- **Degrees**: canonical full names (Bachelor of Technology, Master of Science,
  ...); HSC and SSC stay abbreviated (what Indian resumes and the LLM JSONs
  write); unknown text is kept as written. `B.Tech in IT` splits into type +
  course. **Score**: `CGPA: 9.875`, `Percentage: 92.80%`; a scale (`/10`) is
  only attached when the resume states one, never inferred.
- **Bullets**: achievement = rank/award wording, or a number plus an impact
  verb/%/currency; moved out of responsibilities. Project `metrics` are
  *copies* of description bullets that contain a figure (description stays
  complete).
- **Awards vs certifications**: reclassified by keywords over name+issuer
  regardless of source section (award: winner/rank/finalist/hackathon/prize/
  scholarship/medal/top-N/honours/contest...; certification: certified/course/
  specialization/Coursera/NPTEL/Udemy/edX/AWS/Google/Microsoft/Oracle...).
  Both or neither signals -> stays in its source section.
- **Work type**: internship/volunteer/co-op from title, company or the section
  heading it sat under; else job.
- **Skills**: names canonicalised through a curated table (alias -> name ->
  group; `js` -> JavaScript, `postgres` -> PostgreSQL, ...). The resume's own
  `Label:` grouping is kept; ungrouped items go to table groups (Programming
  Languages, Web Technologies, Databases, Cloud & DevOps, Data Science & ML,
  Tools & Platforms, Core Concepts) else "Other Skills". Extra skills come from
  projects'/work `techStack` lines and curated mentions in bullets. The 26.7k
  skill-DB names (Hard/Soft, no parentheses, <= 4 words) only validate and
  case-fix list items; they are **not** used to discover skills in free text
  (too noisy: "Sales", "Management"). Single-letter/common-word names (C, R, Go,
  Make...) are matched only inside explicit lists. Interests never feed skills.
  `yearsOfExperience` = union of work periods whose text mentions any tool of
  the group (no overlap double counting); `lastUsed` = "Present" or the latest
  `YYYY-MM` end; both stay `0` / `""` when nothing supports them.
- **Links**: project links are the PDF annotations whose centre lies inside the
  entry's line bbox (repo = github/gitlab/bitbucket, else live).
- **Measured**: see PROGRESS. Education year 85.4 % misses the 95 % target;
  inspected misses are wrong entry pairing/merged degree blocks from Stage 10,
  not date parsing. Skills F1 69.0 is against LLM output.
- **Not done / next**: nothing in `normalise` fixes entry boundaries; GLiNER
  (Stage 10) is expected to. `uv.lock` is stale after adding `hypothesis`.

## Stage 12 — grounding, validation, confidence

- **Grounding rule**: a string is kept if its normalised form (NFKC, lowercase,
  alphanumerics only) is in a source line, searched in the entry's own lines
  first; else fuzzy `partial_ratio` >= 0.9 (strings >= 6 chars); else all tokens
  in order with <= 2 foreign tokens between (a date cut out of "Dean's List 2012
  (Top 10%)"). Otherwise it is dropped and logged (`_debug.dropped_ungrounded`).
  A list element whose every text field is dropped goes with it (e.g. a skill).
- **Derived values** are not text copies and are not text-checked: ISO dates and
  `lastUsed`, canonical degree names (provenance = the entry's lines), enums
  (`type`), taxonomy group names, E.164 phones (last 8 digits must be in the
  source digits), score strings (the figures must be in the source), link labels
  of `extra_links`. Skill names pass when the name *or any curated alias* occurs
  as whole words; `techStack` entries use the same rule (e.g. "NodeJS" ->
  "Node.js"). URLs pass if they equal a link annotation or their handle (last
  path segment) is in the text (the header rebuilds `github.com/<handle>` from
  "github: handle").
- **Independent hallucination metric**: `eval/pipeline_eval.py` checks outputs
  against PyMuPDF plain text + link annotation URIs (not the pipeline's layout
  text; pypdf text in `resume-data/TEXTs` turned out to miss content for some
  PDFs, so it is only the fallback for scanned files). The metric exempts the
  same derived classes; header link labels like "Portfolio" and small-caps
  names are *not* exempt and make up most of the remaining 0.18 %.
- **Dedupe**: fuzzy key (Jaro-Winkler >= 0.95) per section; work entries only
  merge when the start date matches; merging fills empty scalars and appends
  unseen list items. Entries with no key field (no title/company/dates; no
  institution/degree; ...) are dropped. Order = first source line id.
- **Validation** never raises: pydantic errors drop the offending list entry (or
  reset the field) and retry; a pathological failure returns the empty object
  with a note.
- **Confidence**: measured, not guessed, where labels exist. Buckets per field
  (title: lexicon hit / <= 6 words / has date; institution: keyword / length;
  degree: canonical / has course; period: both ends / any) map to the observed
  accuracy on LiveCareer weak labels, Laplace-smoothed, fit on even resume ids,
  reported on odd ids, final table refit on all. The labels come from one
  template family, so the numbers are conditional on that; header scores reuse
  the Stage 8 component confidences; skills use table-hit priors; the rest are
  fixed priors (`UNCALIBRATED` list). Company, location and entity-level
  confidence have no labels (company/city are anonymised in LiveCareer).
- **Determinism**: no set-ordering or randomness is serialised; verified across
  processes with `PYTHONHASHSEED` 0 vs 1 on 12 files (byte-identical JSON incl.
  `_confidence`).
- **Not done**: the ifind compatibility `_meta` object (decide in Stage 14),
  size/page limits and timeouts (Stage 14 API), `.doc` conversion (Stage 14).
