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
