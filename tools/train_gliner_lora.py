"""LoRA fine-tune of GLiNER2.5 on entry blocks (PROMPT.md §5 Stage 10.2 #3, Checkpoint 10A approved by the user).

    uv run python tools/train_gliner_lora.py [--epochs 3] [--batch 8] [--out models/gliner-lora]

Local RTX 2050 (4 GB) when CUDA torch is installed, else CPU: LoRA r=8 on the encoder + task heads, fp16 on GPU, small batch with gradient accumulation. Reads
data/train/{train,dev,dev_lc}.jsonl (tools/build_gliner_data.py); writes the adapter to <out>/best (gitignored).
Re-runnable on a bigger dataset: rebuild the data, rerun this, then `python -m eval.fields_eval --extractor lora+norm`."""

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

TRAIN = ROOT / "data" / "train"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--accum", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4, help="encoder (LoRA) learning rate")
    ap.add_argument("--task-lr", type=float, default=2e-4, help="task-head learning rate (5e-4 gave non-finite losses in fp16)")
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--max-train", type=int, default=-1)
    ap.add_argument("--max-eval", type=int, default=-1, help="cap validation examples (CPU runs)")
    ap.add_argument("--out", default=str(ROOT / "models" / "gliner-lora"))
    args = ap.parse_args()

    import torch
    from gliner2 import AutoExtractor
    from gliner2.training.trainer import ExtractorTrainer, TrainingConfig

    gpu = torch.cuda.is_available()
    print("device:", torch.cuda.get_device_name(0) if gpu else f"CPU ({torch.get_num_threads()} threads; slow, see PROGRESS)", flush=True)
    bf16 = False  # bf16 made ~every micro-batch loss non-finite with this model; fp16 loses ~1% of them (skipped below)
    val = TRAIN / "val.jsonl"
    val.write_text((TRAIN / "dev.jsonl").read_text(encoding="utf-8") + (TRAIN / "dev_lc.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    n_train = sum(1 for _ in open(TRAIN / "train.jsonl", encoding="utf-8"))
    n_val = sum(1 for _ in open(val, encoding="utf-8"))
    print(f"train {n_train} / val {n_val} examples, epochs {args.epochs}, batch {args.batch}x{args.accum}", flush=True)

    model = AutoExtractor.from_pretrained("fastino/gliner2.5-base-v1")
    cfg = TrainingConfig(
        output_dir=args.out, experiment_name="rx3-entry-fields", num_epochs=args.epochs, batch_size=args.batch,
        gradient_accumulation_steps=args.accum, encoder_lr=args.lr, task_lr=args.task_lr, warmup_ratio=0.1, scheduler_type="cosine",
        fp16=gpu and not bf16, bf16=bf16, eval_strategy="epoch", save_best=True, early_stopping=True, early_stopping_patience=2,
        use_lora=True, lora_r=args.rank, lora_alpha=2.0 * args.rank, lora_dropout=0.05, lora_target_modules=["encoder", "all_task_heads"],
        save_adapter_only=True, ignore_nonfinite_losses=True, num_workers=0, pin_memory=False, logging_steps=50, max_train_samples=args.max_train, max_eval_samples=args.max_eval,
    )
    t0 = time.time()
    trainer = ExtractorTrainer(model, cfg)
    result = trainer.train(train_data=str(TRAIN / "train.jsonl"), eval_data=str(val))
    print("done in", round((time.time() - t0) / 60, 1), "min;", json.dumps(result, default=str)[:600], flush=True)


if __name__ == "__main__":
    main()
