# models/

Everything here is git-ignored except this file and `adapters/` (a 7 MB LoRA adapter is small enough to version; the shipped
pipeline needs it).

| path | what | size | source |
|---|---|---|---|
| `adapters/rx3-entry-lora/` | LoRA adapter (r=8, encoder + task heads) for `fastino/gliner2.5-base-v1` - fields of work / education entry blocks | 6.9 MB | `tools/train_gliner_lora.py`, see README "Rebuilding the Stage 10 data and the GLiNER adapter" |
| (HF cache) `fastino/gliner2.5-base-v1` | base GLiNER2.5 weights (~740 MB), downloaded on first use | - | Hugging Face |
| `slm/*.gguf` | Qwen3 0.6B / 1.7B Q4_K_M, Stage 13 experiment only (not used) | 0.4 / 1.1 GB | `unsloth/Qwen3-*-GGUF` |
| `_wheels/` | the CUDA torch wheel kept for local re-training | 2.4 GB | download.pytorch.org |
| `gliner-lora/` | raw training output (checkpoints, logs) | - | training run |

adapter_model.safetensors sha256: `104c9cd71ab89434abea4dfd92a24a54bba5f2413f37558b0ab8ea9bc077b486`
Training data: 7,964 entry blocks (5,3xx work / 2,6xx education) from 1,200 synthetic resumes (9 train template families) and LiveCareer
resumes disjoint from the eval pool; held out: 3 synthetic families, 2 dev families, the LiveCareer eval pool, all gold (AAA).
