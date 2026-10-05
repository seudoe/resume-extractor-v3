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
