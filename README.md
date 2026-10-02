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

Not yet available — environment setup is Stage 3.

## Running the eval

Not yet available — harness is built in Stage 4.
Command once available: `python -m eval.run_eval --set gold --compare last`

## Deploying

Not yet available — Docker/HF Space wiring is Stage 14.
