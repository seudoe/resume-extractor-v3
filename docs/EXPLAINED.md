# resume-extractor-v3, explained

A plain-language tour of everything in `resume-extractor-v3`: what it does, how each step works, which tools and libraries it uses, and what the
model we trained actually is. Numbers are from the 32-resume development gold (hand-drafted, **not yet verified by a human**), see `reports/FINAL.md`.

## 1. What it is, in one paragraph

You give it a resume (PDF or DOCX). It gives you back a JSON object in iFind's `ParsedResumeData` shape: name and contacts, work history, education,
skills, projects, certifications, awards, languages and so on. It does this **without asking a large language model to write the answer**. It reads the
page like a human would (layout, columns, bold headings), splits it into sections and entries with rules, uses one small trained model only to *pick
out spans of text* (company, job title, school ...), cleans and normalises the values, and finally **throws away any string that cannot be found in the
original resume**. Everything returned is therefore a piece of the resume (or a normalised form of it, such as an ISO date), never an invention.

## 2. The pipeline at a glance

```
bytes (PDF / DOCX)
  1 ingest         PyMuPDF / python-docx -> lines with fonts, sizes, positions, links          src/rx3/ingest
  2 OCR fallback   Tesseract (or RapidOCR) only for pages with no text layer                    src/rx3/ocr
  3 layout         columns (XY-cut), rows -> cells, wrapped lines joined, per-line features     src/rx3/layout
  4 sections       headings found by synonyms + fuzzy match + layout; every line gets a section src/rx3/sections
  5 header         name, email, phone, links, city from the top of the document                 src/rx3/header
  6 entries        rules split each section into entries (jobs, schools, projects ...)         src/rx3/fields/rules
  7 model          GLiNER + our LoRA adapter picks company/title/location, school/degree/field src/rx3/fields/gliner   (optional)
  8 normalise      dates, degree names, achievements, skills, award vs certification, links     src/rx3/normalise
  9 ground         every output string must be found in the resume text, else it is dropped     src/rx3/validate/grounding.py
 10 clean+score    de-duplicate, keep document order, per-field confidence, schema validation   src/rx3/validate
  -> ParsedResumeData JSON (+ legacy `_meta`, optional `_debug`, `_confidence`)               src/rx3/pipeline.py, api.py
```

The principle running through it is the **pointer principle**: later stages refer to text by line id (`L0`, `L1`, ...) instead of retyping it, so the
output can always be traced back to the source line.

## 3. Stage by stage

### 3.1 Ingest (`ingest/`)
- **PyMuPDF** reads every text span with its font, size, bold flag, colour and bounding box, plus hyperlink annotations and drawn lines (rules under headings).
- **python-docx** reads DOCX paragraphs, list styles and table cells.
- Text is cleaned with **Unicode NFKC** and **ftfy** (mojibake, curly quotes); private-use icon glyphs (the little phone/mail icons) are stripped but remembered
  (`icon_before`), because an icon before a number usually means "phone".
- A per-page quality check (almost no characters, or many `(cid:123)` artefacts) decides which pages need OCR.

### 3.2 OCR fallback (`ocr/`)
Scanned pages are rendered at 300 DPI and read by **Tesseract** (about 2 s per page, chosen by a benchmark: lower word-error-rate and 10x faster than the
alternative); **RapidOCR** (ONNX) is the fallback when no Tesseract binary exists.

### 3.3 Layout analysis (`layout/`) - the part that makes "reads like a human" work
- **Reading order**: a slab-first **XY-cut** splits the page into columns/regions, so a two-column resume is read column by column.
- **Rows and cells**: spans on the same baseline are merged into one line; gaps become explicit cell separators (a tab) so "Degree | Institution | Dates"
  stays three fields instead of one glued sentence (this fixed the biggest early complaint: information mixing across fields).
- **Wrapped lines** are joined and hyphenated words repaired, with guards (a heading is never a continuation).
- **Line features**: relative font size, bold, ALL-CAPS, colour, rule below, gap above, indent, bullet, region. These are the signals every later stage uses.

### 3.4 Sections (`sections/`)
A synonym table (a few hundred phrases: "Work Experience", "Positions of Responsibility", "Academic Projects" ...) is matched with **rapidfuzz**; a candidate
heading must also look like one (bigger/bold/caps/rule/short). Style learned from confident headings is propagated to ambiguous ones; inline rows such as
"Languages: English, Hindi" become one-line sections; documents with no styling use a stricter plain mode. Every line ends up in exactly one section, and unknown
headings become `other` (never silently glued onto the previous section, which was a v2 bug). Held-out check: heading precision 98 %, recall 99 %, line-level
assignment 96 %.

### 3.5 Header (`header/`)
Name by size/bold/position (with email and filename tie-breaks, small-caps and two-line names); email (visible text first, because mailto links can be stale);
phone parsed and formatted to E.164 with **phonenumbers**; LinkedIn/GitHub from link annotations first, coding-platform profiles anywhere, other links only in the
header zone; city from a curated gazetteer (nothing is guessed; gender is never inferred and is always null).

### 3.6 Entry rules (`fields/rules/`)
An entry is a *head* (title / company / dates lines) followed by a *body* (bullets). A small state machine opens a new entry on a date range or on a repeat of the
head style, with fixes for the awkward layouts seen in real resumes (title above its date line, several degrees in one plain row, plain-style project titles).
Field roles come from lexicons: a job-title head-noun list generated from LiveCareer's `jobtitle` tags, company-suffix words, degree and institution patterns, a
date finder (ranges, `Aug '22`, `2022-23`, `08/2023`, seasons, quarters, "Expected May 2027").

### 3.7 The model (`fields/gliner/`) - see section 4
For every work/education entry the head lines are sent to GLiNER with a small schema; it returns spans with confidence, mapped back to line ids. Where its confidence
is at least 0.7 it overrides the rule-based value, otherwise the rules stay. Optional (`RX3_ENABLE_GLINER=1`).

### 3.8 Normalisation (`normalise/`)
- `parse_period`: any date text to `YYYY-MM-01`; never fills in today's date; a lone date is a start for jobs and an end for education; a future end date for a
  student means "still enrolled".
- Degrees to canonical names (B.Tech -> Bachelor of Technology, HSC/SSC kept), course split ("B.Tech in IT"), `CGPA: 9.1` / `Percentage: 92%` (a scale is only added if printed).
- Bullets split into responsibilities vs achievements (a number plus an impact verb, a rank, an award word); project metrics.
- **Skills**: a curated technology table (aliases such as `js` -> JavaScript, `postgres` -> PostgreSQL, grouped into Programming Languages / Web / Databases / Cloud /
  Data & ML / Tools / Core Concepts) plus 26.7k skill names from `skill_db_relax_20.json` used to validate and case-fix items; years and last-used come from the work
  periods where the skill is mentioned (empty if there is no evidence); interests never become skills.
- Awards vs certifications decided by wording (winner/rank/hackathon vs certified/course/Coursera ...), wherever they sat in the resume.
- Project links from the PDF link annotations that fall inside the project's block (github/gitlab = repo, others = live).

### 3.9 Grounding, validation, confidence (`validate/`)
- **Grounding**: each output string is normalised (lower-case, letters and digits only) and searched in the resume lines: exact, then fuzzy (>= 0.9), then "all words in
  order". Not found = dropped and logged. Normalised values (ISO dates, canonical degree/skill names, E.164 phones) are checked through the raw text they came from.
  Measured: 0.15 % of output strings not found in the source on an independent check (they are mostly link labels like "Portfolio").
- **Clean-up**: empty entries dropped, near-duplicates merged (fuzzy key >= 0.95), entries kept in document order, then **pydantic** validation that never raises (a bad entry
  is dropped and the rest returned).
- **Confidence** per field (0-1): buckets (for example "title looks like a job title + short + has a date") mapped to the accuracy actually measured on held-out labels
  (calibrated; the gap between predicted and observed accuracy is 1-2 points for titles and dates). Fields without labels use fixed priors and are listed as uncalibrated.

### 3.10 Service (`api.py`, `Dockerfile`)
FastAPI + uvicorn: `POST /extract` (multipart `file`), `/health`, `/version`; limits 10 MB, 5 pages, 25 s; password-protected or corrupt files give 422, wrong types
415. The Docker image (python 3.11-slim, uv, CPU torch, Tesseract) bakes in the pinned model and checks its checksum; it is meant for a Hugging Face Docker Space.

## 4. The model we trained: what it really is

**It is not a chatbot and it does not write text.** It is a *schema-conditioned span tagger*.

### 4.1 The base model: GLiNER2.5 (`fastino/gliner2.5-base-v1`)
- Inside is **DeBERTa-v3-base** (Microsoft's encoder: 12 transformer layers, 768-dimensional, 128k-word vocabulary) - the same family of model as BERT, about 184 M of the
  195 M parameters. An encoder reads text and produces a vector per token; it cannot generate sentences.
- GLiNER's trick: you pass the text **together with a description of what to find** (a schema such as `company: employer organisation name`, `title: job title or role`).
  The encoder reads schema and text jointly. Small heads on top then score, for every position, "does a span of this field start here?" and "does it end here?" and pair
  the starts with ends (the "boundary" architecture, so spans can be any length). Output: the selected spans, their character offsets and a confidence.
- "Zero-shot" means it can do this for fields it was never trained on, simply from the field names/descriptions. Used like that, it was already good at company names
  and weak at job titles and degrees in resume rows.

### 4.2 What we added: a LoRA adapter (7 MB)
- **LoRA** (low-rank adaptation) freezes the original weights and learns small add-on matrices (rank 8, scale 16, dropout 0.05) inside the attention layers of the
  encoder and in all of GLiNER's task heads. Only **1.7 M of 195 M parameters (0.87 %)** are trained; the result is a 6.9 MB file, `models/adapters/rx3-entry-lora/`.
- At load time the adapter is **merged** into the base weights (no extra cost at inference).
- **What we taught it**: "given the few lines at the top of a resume entry, point at the company / job title / location (work) or the institution / degree / field of
  study (education)". The input text is exactly what the pipeline sends at inference (the rules stage's entry blocks), so training and serving see the same thing.

### 4.3 The training data (no LLM involved)
| source | what | how labelled |
|---|---|---|
| **synthetic resumes** | 1,800 PDFs rendered through Chromium from 12 template families (single column, two-column sidebars, banner, table, LaTeX-like, Indian-student CGPA style, timeline, plain stacked, boxed ...) using job/education text from the Kaggle `resume_data.csv`, with random fonts, date formats, section order, heading synonyms | exact, because we printed it |
| **LiveCareer resumes** | about 1,000 real-looking resumes whose HTML source tags every field | the HTML tags, aligned to PDF lines at >= 90 % similarity (99.9 % aligned) |

Splits by template family: 3 synthetic families (jake, table_docx, banner) and 2 dev families never appear in training; the LiveCareer evaluation pool and all gold resumes are
never trained on. In total 7,965 training blocks (5,323 work, 2,642 education).

### 4.4 How it was trained
LoRA fine-tuning with the GLiNER2 trainer on a laptop RTX 2050 (4 GB): fp16, effective batch 16 (4 x 4), 3 epochs (1,494 steps, about 33 minutes), cosine schedule,
encoder learning rate 1e-4 and head learning rate 2e-4. Along the way: a 5,000-character outlier block caused an out-of-memory error (blocks are now capped at 600 characters);
bf16 produced non-finite losses, so fp16 with the roughly 1 % bad micro-batches skipped was used.

### 4.5 What it achieves
Block-level F1 on template families it never saw (1,899 blocks), zero-shot -> fine-tuned: title 71 -> **97**, company 83 -> **94**, location 52 -> **89**, institution 78 -> **97**,
degree 67 -> **97**, field of study 89 -> **95**. In the full pipeline on the 32-resume gold: work entry F1 0.59 (rules) -> 0.79 (zero-shot) -> **0.80** (fine-tuned), education
0.76 -> 0.82 -> **0.83**.

### 4.6 What it does not do
It does not split a resume into entries or sections (rules do), does not handle projects, certifications or awards yet, never produces text that is not in its input,
and costs about 1 s per resume on 2 CPU cores. If it is unsure (confidence < 0.7) or fails on a block (it occasionally gives NaN scores), the rule-based value is kept.

## 5. Tools we built (`tools/`, `eval/`, `scripts/`)

| file | purpose |
|---|---|
| `tools/draft_gold.py`, `tools/gold_fill.py` | scaffold and fill gold resumes by hand (never from an LLM) |
| `tools/livecareer_align.py` | align LiveCareer HTML tags to PDF lines (labels for training/eval) |
| `tools/synth/` (`families.py`, `data.py`, `render.py`) | the synthetic resume renderer (HTML -> PDF via Playwright/Chromium) |
| `tools/build_gliner_data.py` | blocks + labels -> GLiNER training JSONL, split by template family |
| `tools/train_gliner_lora.py` | the LoRA fine-tune |
| `tools/build_title_lexicon.py`, `tools/build_skill_names.py` | generate the job-title and skill lexicons |
| `eval/run_eval.py` | entity F1 / scalar fields / skills / hallucination vs gold, for v2, AI path, LLM JSON and v3 |
| `eval/header_eval.py`, `section_eval.py`, `fields_eval.py`, `blocks_eval.py`, `pipeline_eval.py`, `api_perf.py` | header, sections, field-level proxies, model block accuracy, end-to-end validity/determinism/latency, HTTP performance |
| `eval/calibrate_confidence.py`, `combine_search.py` | fit confidence tables; choose rules vs model per field |
| `scripts/fetch_models.py` | download the pinned model and verify checksums (used in the Docker build) |

## 6. Libraries and frameworks

| area | libraries | used for |
|---|---|---|
| documents | **PyMuPDF**, **python-docx**, **ftfy**, unicodedata | reading PDFs/DOCX, text repair |
| OCR | **Tesseract** (pytesseract), RapidOCR (onnxruntime) | scanned pages |
| text matching | **rapidfuzz**, regex, **phonenumbers**, a hand-made gazetteer | headings, fuzzy grounding, dedupe, phones, cities |
| schema/validation | **pydantic v2** | the output contract (mirror of ifind's TypeScript types) |
| model | **PyTorch**, **gliner2**, **transformers** (DeBERTa-v3), **peft** (LoRA), safetensors, huggingface-hub | the span tagger and its fine-tune |
| service | **FastAPI**, uvicorn, python-multipart, **Docker**, uv | the API and image |
| data/eval | numpy, scipy (Hungarian matching), pandas, jiwer, psutil, **Playwright/Chromium**, Jinja2/ReportLab (installed), pytest, **hypothesis**, httpx | evaluation, synthetic data, tests |
| experiments (not shipped) | llama-cpp-python + Qwen3 0.6B/1.7B | the small-language-model experiment (slower and worse than the encoder path) |

Declared but unused by the shipped code: `dateparser`, `flashtext` (our own date and skill matching replaced them).

## 7. Algorithms worth naming
XY-cut page segmentation; baseline clustering into rows/cells; synonym + Jaro-Winkler / token-set fuzzy matching; entry-boundary state machine; Hungarian assignment
(scipy) for scoring predicted vs gold entities; Jaro-Winkler de-duplication; interval merging for "years of experience"; bucketed (histogram) confidence calibration with
Laplace smoothing; LoRA fine-tuning of a boundary-pair span extractor; span-to-line mapping by character offsets; greedy ordered-token and partial-ratio alignment for grounding.

## 8. Evaluation honesty
- Gold = 32 real resumes drafted by me from the text; unverified; some rules were tuned on them (development numbers).
- Targets (entity F1 >= 0.90) are **not** met yet: work 0.80, education 0.83, projects 0.76, certifications 0.68, awards 0.64.
- A hosted LLM reading the same PDFs still scores higher on entity F1 (0.96-1.00 on work/education/projects); v3's advantages are zero runtime cost, no invented text,
  guaranteed-valid output, determinism and about 1 s on 2 CPU cores.
- Latency/memory were measured on a local server; the Space is not deployed yet.

## 9. Where things live
`src/rx3/` code (about 2.8 k lines) - `tests/` 87 tests - `eval/` harness - `tools/` data builders - `data/gold/` hand-drafted gold (git-ignored, contains personal data) -
`models/adapters/` the shipped adapter - `reports/` every evaluation (start with `FINAL.md`) - `PROGRESS.md` / `DECISIONS.md` the build log and the reasons for each choice -
`README.md` how to run, evaluate, add gold, retrain, deploy.
