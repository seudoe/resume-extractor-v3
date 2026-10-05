"""Cold-start and request latency of the real HTTP service (uvicorn, GLiNER + adapter on, CPU, N torch threads).

    uv run python -m eval.api_perf [--n 24] [--threads 2] [--url http://127.0.0.1:7860]

Without --url it starts `uvicorn rx3.api:app` as a subprocess and measures start -> /health ok (cold start), then POSTs resumes
(all AAA first, then LiveCareer) one after another and reports p50 / p95 wall time per request and the peak RSS of the server.
Point --url at a running container / Space to measure that instead (then there is no RSS)."""

import argparse
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "eval"))
from _resume_data_layout import GOLD_CATEGORY, categories, pdf_path, stems_in_category  # noqa: E402
from perf import _percentile  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--url")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args()

    proc, url = None, args.url or f"http://127.0.0.1:{args.port}"
    t0 = time.perf_counter()
    if not args.url:
        env = {**os.environ, "RX3_ENABLE_GLINER": "1", "RX3_TORCH_THREADS": str(args.threads), "OMP_NUM_THREADS": str(args.threads),
               "TOKENIZERS_PARALLELISM": "false", "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.Popen([sys.executable, "-W", "ignore", "-m", "uvicorn", "rx3.api:app", "--app-dir", str(ROOT / "src"), "--port", str(args.port), "--log-level", "warning"],
                                env=env, cwd=ROOT)
    client = httpx.Client(base_url=url, timeout=120)
    health = None
    while health is None:
        try:
            h = client.get("/health").json()
            health = h if h["status"] == "ok" else None
        except Exception:  # noqa: BLE001
            pass
        if health is None:
            time.sleep(0.5)
            if proc and proc.poll() is not None:
                raise SystemExit("server exited during startup")
    cold_s = time.perf_counter() - t0

    files = [pdf_path(GOLD_CATEGORY, s) for s in stems_in_category(GOLD_CATEGORY)]
    for c in categories():
        if c != GOLD_CATEGORY:
            files += [pdf_path(c, s) for s in stems_in_category(c)[:2]]
    files = files[: args.n]
    times, bad = [], []
    for f in files:
        t = time.perf_counter()
        r = client.post("/extract", files={"file": (f.name, f.read_bytes(), "application/pdf")})
        times.append(time.perf_counter() - t)
        if r.status_code != 200:
            bad.append((f.name, r.status_code, r.text[:80]))
    rss = ""
    if proc:
        p = psutil.Process(proc.pid)
        rss = f"{sum(c.memory_info().rss for c in [p, *p.children(recursive=True)]) / 2**20:.0f} MB RSS (server tree, end of run)"
        proc.terminate()
    md = [f"# API performance — {date.today().isoformat()}", "",
          f"- Server: `{'subprocess uvicorn' if proc else url}`, GLiNER+adapter on, torch threads {args.threads}, version {health['version']}, models {health['models_loaded']}",
          f"- Cold start (process launch -> /health ok): **{cold_s:.1f} s** (server-side startup {health['startup_ms']} ms incl. warm-up {health['warmup_ms']} ms)",
          f"- {len(files)} requests: p50 **{_percentile(times, 50) * 1000:.0f} ms**, p95 **{_percentile(times, 95) * 1000:.0f} ms**, max {max(times) * 1000:.0f} ms; non-200: {len(bad)}",
          f"- Memory: {rss or 'n/a'}"]
    if bad:
        md += ["", "### Non-200"] + [f"- {n}: {c} {t}" for n, c, t in bad[:10]]
    path = ROOT / "reports" / f"api_perf_{date.today().isoformat()}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
