# resume-extractor-v3 — final report (Stage 16)

Date: 2026-10-05. **Read this first:** every accuracy number below is measured on a 32-resume gold set (the real resumes in `resume-data/PDFs/AAA`)
that I drafted by hand from the resume text and that **nobody has verified yet** (Checkpoint 4B). Several rule sets were tuned on these same
resumes, so they are development numbers, not reported accuracy. The Space is not deployed, so latency / memory are from a local uvicorn run, not
from the real Space.

## 1. v2 vs v3 (and the LLM references) on the 32-resume gold

Candidates: **v2** = the old resume-extract Space output; **AI path** = ifind's OpenAI path (`mongo-runner/output.json`, only 3 of the 32 resumes
exist there); **LLM JSON** = the Gemini/Groq-labelled JSONs in `resume-data/JSONs/AAA` (a hosted LLM reading the PDF, i.e. the quality ceiling we are
trying to replace, *not* used anywhere in v3); **v3 rules** = LLM-free, no model; **v3 + GLiNER** = rules + the zero-shot model; **v3 + LoRA** = the shipped
configuration (rules + fine-tuned adapter, cut-off 0.7).

### Entity F1 (Hungarian matching, key fields must agree; PROMPT §4.2)

| section | v2 | AI path (3 files) | LLM JSON | v3 rules | v3 + GLiNER zero-shot | **v3 + LoRA (shipped)** | target |
|---|---|---|---|---|---|---|---|
| workHistory | 0.349 | 0.333 | 0.965 | 0.593 | 0.788 | **0.801** | 0.90 |
| education | 0.206 | 0.000 | 1.000 | 0.755 | 0.818 | **0.827** | 0.90 |
| projects | 0.426 | 0.000 | 0.964 | 0.755 | 0.755 | **0.755** | 0.90 |
| certifications | 0.452 | 0.667 | 0.984 | 0.677 | 0.677 | **0.677** | – |
| awards | 0.380 | 0.205 | 0.612 | 0.635 | 0.635 | **0.635** | – |

### Scalar fields (name / contacts / summary; accuracy)

| field | v2 | LLM JSON | v3 (all variants) | target |
|---|---|---|---|---|
| name | 76.2 % | 100 % | **100 %** | 97 % |
| email | 66.7 % | 100 % | **100 %** | 98 % |
| phone | 68.4 % | 100 % | **100 %** | 98 % |
| linkedin | 64.3 % | 38.1 % | 66.7 % in `run_eval` (95.2 % in the dedicated header eval, which normalises URLs) | 98 % |
| github | 75.0 % | 23.5 % | 76.5 % in `run_eval` (94.1 % in the header eval) | 98 % |
| summary | 60.0 % | 100 % | 71.4 % | – |

Header eval (`eval.header_eval`, 32 resumes): name 100, email 100, phone 100 (targets met); linkedin 95.2 and github 94.1 (missed by 3-4 points: one
icon-only template where the handle exists only as an image); city 91.3. Section assignment (`eval.section_eval`): headings P 98.0 / R 99.0, **line-level
assignment 96.3 % (target 95 % met)**, dev set.

### Skills, hallucination, validity, determinism

| | v2 | LLM JSON | v3 rules | v3 + LoRA |
|---|---|---|---|---|
| skills F1 (names) | 0.227 | 0.899 | 0.726 | 0.726 |
| hallucination (`run_eval` metric: strings not found in the gold file's text; it has no link-annotation URLs, so it overstates v3) | 52.1 % | 5.5 % | 3.2 % | 3.1 % |
| hallucination (independent PyMuPDF text + link annotations, 128 resumes) | – | – | 0.18 % | **0.15 %** (target 0.5 %) |
| schema validity | 100 % | 90.6 % | 100 % | 100 % |
| crash rate | 34 % (no candidate) | 0 % | 0 % | 0 % |
| deterministic (2 processes, different hash seeds) | – | – | yes | **yes** |

Honest reading: on this gold the hosted-LLM output **beats v3 on entity F1 for work, education and projects by 0.15-0.25** (and on skills), because an LLM
copes with any layout. v3 beats it on contacts, never invents text (0.15 % on the independent metric; 3.1 % vs 5.5 % on the metric both can be scored with), always returns a valid object, is
deterministic, runs on 2 CPU cores in about a second, and has no per-resume cost. v3 is far ahead of v2 and the AI path on every metric.

### Sub-field accuracy (proxy labels; PROMPT target 0.90)

LiveCareer weak labels (n=100, rules -> LoRA@0.7): work title recall 83.5 -> 80.5 %, work start / end dates 99.5 / 99.0 % (rules), education degree
83.6 -> 94.1 %, school 53.9 -> 90.0 %, graduation year 82 %; AAA agreement with the LLM JSON: company 57.6 -> 86.3 %, title 78.0 -> 89.0 %, location
8.3 -> 90.3 %. Held-out synthetic template families (1,899 blocks): F1 title 97.0, company 94.2, location 89.1, institution 97.0, degree 96.9, field of
study 95.4 (zero-shot GLiNER 71 / 83 / 52 / 78 / 67 / 89). Dates inside a matched entry are right about 99 % of the time; education dates are the
weak spot (82-85 %) because they depend on getting the entry boundary right.

## 2. Per-section strengths and weaknesses

- **Header / contacts**: strong (name, email, phone 100 %). Weak: handles that exist only as icon images; "Bay Area"-style locations.
- **Sections**: strong (96 % of lines). Weak: sidebar templates (Simple_Hipster: 55 % of lines), a LaTeX "Research" section, headings written as small caps.
- **Work history**: dates and titles are good; the weak part is company strings (tagline lines, "Company, City, Country", parentheticals, "Google | team").
- **Education**: institution and degree good after the fine-tune; GPA/percent parsing fine; entries glued into one plain line are split only when degree words repeat.
- **Projects**: plain-style titles (no bold, no glyph) and title lines with tech stack after a separator are the main misses; GLiNER is not applied here.
- **Certifications / awards**: keyword rules only; one-line "A; B; C" lists and `\faTrophy :` icon prefixes are not split or cleaned.
- **Skills**: names are good (recall 83 %), precision 66 %, most likely because tech-stack lines of projects are also counted as skills while the reference lists only the skills section (not investigated further).

## 3. The 10 worst remaining failures (mean entity F1, with causes)

1. `Simple_Hipster_CV` (0.20): two-column sidebar; "Short Resume" and "Curriculum" headings are not recognised, so work, projects and awards come back empty.
2. `entry_level_software_engineer_resume` (0.46): company printed with a long parenthetical ("RESUME WORDED & CO. (8 employee venture-backed ...)") and "Certifications"/"Awards" written as inline `;`-separated lists.
3. `jenil_shah_resume` (0.50): "SWE Intern, Google | YouTube Commerce Applied Data Team" - company/title split the wrong way round; awards lines carry "Achieved ..." tails.
4. `altacv_template` (0.52): LaTeX icon prefixes (`\faTrophy : Hackathon Winner`) stay in names; the certification sits in the "Most proud of" block.
5. `data_analyst_ats_compatible` (0.53): "SKILLS & OTHER" holds the personal project and the awards ("Awards: A, B" inside Education bullets); an extra "Singapore University" education entry from a bullet.
6. `resume_block` (0.53): sidebar template with the role printed before the organisation ("Technical Co-Committee Member INIT-AI, Mumbai") and project bullets glued to their title with a comma.
7. `aryanniravshah` (0.60): student-body roles ("Computer Society of India - SPIT | Marketing Subcommittee") plus plain project titles without a gap.
8. `mohd_asifshershahvadi_internshala` (0.60): "Senior Secondary (XII), Maharashtra State Board ..." taken as the institution; project title with a trailing arrow glyph; second project missed.
9. `vedant_patil` (0.60): project titles with " - " / "(Blockchain + MERN)" suffixes do not match the plain title; awards written as one sentence.
10. `entry_level_data_analyst2_template_17` (0.63): certifications under "OTHER" never recognised; "Boston, MA" taken as a second education entry.

## 4. Latency, memory, footprint (local run; the real Space is not deployed yet)

- Rules only: pipeline p50 about 0.1 s, p95 about 0.2 s (224 resumes, warm). With GLiNER + adapter (CPU, 2 threads): pipeline p50 1.0 s / p95 3.5 s
  (in-process, 128 resumes); over HTTP (`eval.api_perf`, 30 PDFs): p50 1.6 s, p95 2.9 s, no errors.
- Cold start 71 s locally (model load dominates; expected shorter in the image with weights baked in). Memory 1.5 GB RSS with the model.
- Footprint: base model 774 MB + adapter 7 MB; CPU torch from the PyTorch CPU index. Docker image size and the `--cpus=2 --memory=16g` run are **not measured**
  (Docker is not installed on the development machine).
- OCR for scanned PDFs: Tesseract about 2.2 s per page (not exercised in the image build).

## 5. What to do next (in this order)

1. **Verify the gold** (Checkpoint 4B): `data/gold/drafts/*.json`, `header_gold.json`, `section_gold.json`. Until then none of the above is a reported accuracy.
2. **Build the Docker image / push the Space** (14A, 14B) and re-measure latency, memory and image size on the real Space.
3. **Extend the model to projects, certifications and awards** (the largest remaining gap, F1 0.64-0.76 against a 0.90 target): add schemas, synthetic data for
   plain-style projects and list-style awards, retrain with `tools/train_gliner_lora.py` (the README has the exact commands).
4. **More real, varied gold and training resumes**: especially sidebar and tagline templates (the failures above); a bigger set makes the 0.90 targets measurable.
5. **Fix the cheap rule gaps found above**: icon prefixes (`\faTrophy :`), inline `;` lists of awards/certifications, headings "Short Resume"/"Curriculum", role-before-organisation rows.
6. Decide about the AI path in ifind (Stage 15 report) once the gold is verified and the targets are met.

## 6. Stage 15 report (ifind integration; nothing in `ifind/` was changed)

The owner declined edits in `ifind/` at Checkpoint 15A, so the change is delivered as `deploy/ifind_resumeParser.patch` (checked with `git apply --check`
against the current `lib/resumeParser.ts`; apply with `cd ifind && git apply ../resume-extractor-v3/deploy/ifind_resumeParser.patch`):
`HF_SPACE_URL` reads `RESUME_EXTRACTOR_URL` (default `https://seudoe-resume-extractor-v3.hf.space`, the planned Space; set the variable until it exists),
and `normaliseHFOutput` passes the response through when it already has `metaDetails` (and drops `_meta` / `_debug` / `_confidence`). The 60 s timeout is unchanged.

**Reported, not changed:** `parseWithOpenAI` sends the PDF as an `image_url` with `data:application/pdf;base64,...`. OpenAI's chat `image_url` accepts images, not
PDFs, so that path very likely always fails (the AI-path baseline here: schema validity 0 %, 3 of 32 resumes present, 86 % hallucination). The goal is no LLM for
extraction; the proposal is to make v3 the only path once the gold is verified and the entity targets are met, and to remove the OpenAI fallback then.
