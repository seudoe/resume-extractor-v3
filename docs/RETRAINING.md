# Retraining the model on the PDFs and JSONs in `resume-data`

## 1. First: are those PDFs and JSONs right to train on?

**Short answer: the PDFs are useful, the JSONs are not good labels for this model, and "all of them" would mostly repeat what the model already has.**
Facts measured on the actual files (2026-10-06):

| question | finding |
|---|---|
| How many are there? | 2,484 LiveCareer PDFs in 24 profession folders (+ 32 real resumes in `AAA`). **LLM JSONs exist for only 289 of the 2,484 so far** (your Groq/Gemini run is still going). |
| Is the layout really the same? | Yes. In a random sample of 150 PDFs **all 150 use the same font (Times New Roman)** and 123 of 150 (82 %) are a single column; they all come from one resume builder. |
| Is the content different? | Yes: 24 professions (accountant, chef, teacher, HR, engineer, ...) with different section mixes (231 different heading orders). That is *useful vocabulary*: our synthetic data comes from a CSV that is mostly IT roles. |
| Can the JSONs supply the labels? | Poorly. **91 % of the work entries in the existing JSONs have no company or the literal "Company Name"** (the source resumes are anonymised: company and city are replaced by placeholders). The model learns exact text spans, so it would learn to output placeholders or nothing. |
| Are the JSON values exact text? | Often not: LLMs normalise (dates, degree names, merged fields), so many values cannot be found verbatim in the resume line, which is what span training needs. They are also LLM output: on my gold the LLM JSONs have 5.5 % invented strings, 90.6 % schema validity and a weak awards section. |
| Is there a better label source for the same PDFs? | **Yes: the LiveCareer HTML tags** (`jobtitle`, `jobdates`, `degree`, `programline`, school ...). They are exact, free, and already aligned to the PDF lines at 99.9 %. The HTML titles are found in the LLM JSON 92.5 % of the time (789 of 853), so the JSON adds nothing the tags do not already give for titles. |

So what would training on all of them change?
- **Layout robustness** (the model's real weak spot on real resumes: sidebars, taglines, icons): **no**. 2,484 more resumes of one layout add almost no new layouts; about 1,000 of them are already in the training data. What improved real-resume results was the *diversity of synthetic templates*, not volume.
- **Profession vocabulary** (titles and schools outside tech): **yes, a modest gain**, if the share of LiveCareer data is capped so it cannot dominate the mix.
- **Accuracy of labels**: use the **HTML tags**, not the JSONs.

## 2. Recommended plan

1. **Use all LiveCareer resumes through the HTML tags** (not the JSONs), capped at about a third of the training blocks.
2. **Keep a held-out slice**: the existing evaluation pool (`data/livecareer/aligned.jsonl`, 455 resumes) must stay out of training; the 32 gold resumes and the 3 test template families too.
3. **Add layout diversity instead of more of the same**: new synthetic families (`tools/synth/families.py`) or real resumes from other builders. This is where the remaining errors come from.
4. **Accept the new adapter only if it does not regress**: gold work/education F1 (currently 0.80 / 0.83), held-out-family block F1, and the LiveCareer dev blocks.
5. *(Optional)* use the LLM JSONs only where they **agree with the HTML tags** (consensus labels) to add the lists the HTML does not tag (certifications, awards, affiliations): needs a small converter (`tools/llm_json_to_gliner.py`, not written yet; say the word and I will write it).

## 3. Exact commands (from `resume-extractor-v3/`, PowerShell)

Training needs the CUDA build of torch; the venv is currently on the CPU build (used for inference/timing).

```powershell
# 0) swap to the GPU torch (wheel is kept in models\_wheels); needs the Windows DLL workaround
python -m uv pip install --python .venv\Scripts\python.exe "models\_wheels\torch-2.4.0+cu124-cp311-cp311-win_amd64.whl"
Copy-Item .venv\Lib\site-packages\torch\lib\libiomp5md.dll .venv\Lib\site-packages\torch\lib\libomp140.x86_64.dll
$env:KMP_DUPLICATE_LIB_OK = "TRUE"

# 1) label every LiveCareer resume that is not in the eval pool, from the HTML tags (3000 = "take all remaining", per-category cap 125)
.venv\Scripts\python.exe tools\livecareer_align.py --n 3000 --seed 2 --exclude-from data\livecareer\aligned.jsonl --out data\livecareer\aligned_train.jsonl

# 2) build the training blocks: all synthetic train families + at most 4000 LiveCareer blocks (about a third)
.venv\Scripts\python.exe tools\build_gliner_data.py --max-synth 8000 --max-lc 4000

# 3) fine-tune (about 40-60 min on the RTX 2050; keep the laptop plugged in and awake)
.venv\Scripts\python.exe -W ignore tools\train_gliner_lora.py --epochs 3 --batch 4 --accum 4 --max-eval 600 --out models\gliner-lora-new

# 4) compare with the shipped adapter (held-out families, LiveCareer dev blocks, then the 32-resume gold)
.venv\Scripts\python.exe -m eval.blocks_eval --adapter models\gliner-lora-new\best --split test_synth --device cuda
.venv\Scripts\python.exe -m eval.blocks_eval --adapter models\gliner-lora-new\best --split dev_lc --device cuda
$env:RX3_ENABLE_GLINER = "1"; $env:RX3_GLINER_ADAPTER = "models\gliner-lora-new\best"; $env:RX3_GLINER_DEVICE = "cuda"
.venv\Scripts\python.exe -m eval.run_eval --baseline v3     # compare entity F1 with reports\eval_2026-10-05_gold32_gliner_lora.md

# 5) if it is better: ship it
Copy-Item models\gliner-lora-new\best\* models\adapters\rx3-entry-lora\ -Force
#    then update the sha256 of adapter_model.safetensors in models\MODEL_CHECKSUMS.txt and models\MANIFEST.md, rebuild the image

# 6) swap back to CPU torch for inference, timing and determinism checks
Remove-Item .venv\Lib\site-packages\torch\lib\libomp140.x86_64.dll
python -m uv pip install --python .venv\Scripts\python.exe torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu --reinstall-package torch
```

Notes: `--max-lc` is the cap on LiveCareer blocks (raise it only if the gold does not regress); training data and models are git-ignored; every step is deterministic for a given
seed. If the loss turns non-finite the trainer skips those micro-batches (about 1 %); if the GPU runs out of memory lower `--batch` to 2 and raise `--accum` to 8.

## 4. What I would expect

A small gain on non-tech titles and schools in the LiveCareer-style resumes, roughly no change on the 32 real resumes' layout-driven errors (tagline templates, sidebars), and
a risk of drifting toward the LiveCareer look if the cap is removed. The biggest improvement would come from step 3 of the plan (new layouts) plus extending the model to
projects, certifications and awards, not from more of the same resumes.
