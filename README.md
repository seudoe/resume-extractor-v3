---
title: resume-extractor-v3
sdk: docker
app_port: 7860
---

# resume-extractor-v3

LLM-free resume extraction pipeline. Turns a PDF/DOCX resume into JSON matching
iFind's `ParsedResumeData` schema, using layout-aware rules plus small local
encoder models (no hosted LLM calls at runtime). See `../PROMPT.md` for the
full spec and stage plan, and `../h.md` for why the old extractor
(`../resume-extract/`) was replaced.

## Status

Scaffold only (Stage 1). Nothing runs yet. See `PROGRESS.md` for current
stage and `DECISIONS.md` for design choices made so far.

## Project layout

See `PROMPT.md` §4 for the full intended layout. Summary:

- `types/` — Pydantic schemas (output schema + internal Document IR)
- `src/rx3/` — the pipeline package (ingest, ocr, layout, header, sections, fields, normalise, validate, api)
- `data/` — gold/eval/training data (git-ignored except manifests)
- `models/` — downloaded/fine-tuned weights (git-ignored)
- `eval/` — evaluation harness
- `tools/` — dataset builders, gold-labelling helpers
- `tests/` — pytest suite
- `reports/` — eval reports

## Running locally

    uv sync --extra gliner --extra dev               # CPU torch on Linux; on Windows see DECISIONS.md "Two torch environments"
    RX3_ENABLE_GLINER=1 uv run uvicorn rx3.api:app --port 7860      # GLiNER + the shipped LoRA adapter; omit the variable for rules only
    curl -X POST "http://127.0.0.1:7860/extract" -F "file=@resume.pdf"          # ?debug=true, ?confidence=true
    curl http://127.0.0.1:7860/health

Environment: `RX3_ENABLE_GLINER` (1 = model refinement), `RX3_GLINER_ADAPTER` (path, or `none` for zero-shot), `RX3_TORCH_THREADS`
(keep fixed; determinism holds per thread count), `RX3_MAX_BYTES` (10 MB), `RX3_MAX_PAGES` (5), `RX3_TIMEOUT_S` (25), `RX3_GIT_SHA`.
The response is the `ParsedResumeData` object plus a legacy `_meta` object (name, email, phone, github, linkedin, otherLinks) that ifind's
`normaliseHFOutput` still reads. Errors: 413 too large, 415 wrong type (including `.doc` when LibreOffice is absent), 422 corrupt /
password-protected / too many pages, 504 timeout.

## Running the eval

    python -m eval.run_eval --baseline v3                     # entity F1 / scalar fields / skills / hallucination on the gold (rules only)
    RX3_ENABLE_GLINER=1 python -m eval.run_eval --baseline v3 # with the shipped LoRA adapter; --baseline v2 | llm | ai for the references
    python -m eval.header_eval ; python -m eval.section_eval  # header fields, section assignment
    python -m eval.fields_eval --extractor rules+norm --n 100 # field-level proxies on LiveCareer labels + agreement with the LLM JSONs
    python -m eval.pipeline_eval --gliner --n 200             # schema validity, independent hallucination, determinism, per-stage latency
    python -m eval.api_perf                                   # cold start + request latency of the real HTTP service

Reports land in `reports/` (`reports/FINAL.md` is the stage-16 summary). `pytest -q` runs the unit tests.

## Adding a gold resume

1. Put the PDF in `../resume-data/PDFs/AAA/` and run `python tools/draft_gold.py` (writes `data/gold/raw/<id>.txt` and a scaffold in `data/gold/drafts/`).
2. Read the raw text and fill the scaffold by hand (no LLM output): write a small script with the helpers in `tools/gold_fill.py` (`W`, `E`, `P`, `C`, `A`, `SK`,
   `AFF`, `save`), e.g. `save("<id>", edu=[E("IIT Bombay", "Bachelor of Technology", "CSE", "2020-08-01", cur=True, out="CGPA: 9.1")], ...)`.
   The file becomes `status: "drafted"`; only the owner sets `verified_by` / `verified_at` after checking it against the PDF.
3. Add the header values to `data/gold/header/header_gold.json` and the headings to `data/gold/sections/section_gold.json` (see the existing entries).
4. Re-run `python -m eval.run_eval --baseline v3`. Gold is never used for training.

## Deploying

    docker build -t rx3 --build-arg GIT_SHA=$(git rev-parse --short HEAD) .      # bakes the pinned model, verifies checksums
    docker run --rm --cpus=2 --memory=16g -p 7860:7860 rx3
    uv run python -m eval.api_perf --url http://127.0.0.1:7860                    # cold start + p50/p95 against the container

Hugging Face Space (new Space, e.g. `seudoe/resume-extractor-v3`, SDK docker): push this repo's tracked files and use
`deploy/HF_SPACE_README.md` as the Space's `README.md`. Not pushed yet: Checkpoint 14A needs the owner's go-ahead.

## Rebuilding the Stage 10 data and the GLiNER adapter (re-run on a bigger dataset)

Everything below is deterministic and re-runnable; the paths are the only inputs. Run from this folder with the project venv
(`.venv\Scripts\python.exe`). Training needs a GPU build of torch (`models/_wheels/` holds the CUDA 12.4 wheel; CPU works but is ~10x slower). The venv is on the CPU
wheel by default; see DECISIONS.md "Two torch environments" for the exact swap (and the Windows DLL workaround) before training,
and swap back afterwards so inference timing and determinism are measured on the CPU wheel.

1. **More real resumes** (PDFs under `../resume-data/PDFs/<CATEGORY>/`, labelled LiveCareer HTML in `../FILES/Resume.csv`):
   `python tools/livecareer_align.py --n 1200 --seed 1 --exclude-from data/livecareer/aligned.jsonl --out data/livecareer/aligned_train.jsonl`
   (`aligned.jsonl` is the held-out eval pool; never train on it.) For *non-LiveCareer* resumes there are no HTML tags: add gold
   instead (`tools/draft_gold.py` scaffolds, `tools/gold_fill.py` helpers) and keep gold out of training.
2. **Synthetic PDFs** (12 template families, exact ground truth): `python -m tools.synth.render --n 1800 --seed 0`.
   More volume: raise `--n` or change `--seed`. New layouts: add a `Family` in `tools/synth/families.py` (hold whole families out).
3. **Training JSONL**: `python tools/build_gliner_data.py` -> `data/train/{train,dev,test_synth,dev_lc}.jsonl`.
4. **Fine-tune**: `python tools/train_gliner_lora.py --epochs 3 --batch 4 --accum 4 --max-eval 600` -> `models/gliner-lora/best`.
5. **Evaluate**: `python -m eval.blocks_eval --adapter models/gliner-lora/best --split test_synth --device cuda`,
   `python -m eval.fields_eval --extractor lora@0.5+norm --n 100`, `python -m eval.run_eval --baseline v3`
   (with `RX3_ENABLE_GLINER=1 RX3_GLINER_ADAPTER=models/gliner-lora/best`).
