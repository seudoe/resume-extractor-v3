"""PROMPT.md §4.3 performance harness. Generic — wraps any callable, so it
works today against the v2 baseline (or a stub) and against the v3 pipeline
once Stage 5+ exists, without changes.

Uses `tracemalloc` + `psutil` RSS rather than `memray`: memray doesn't
support Windows, which is the dev machine (see DECISIONS.md Stage 3).
memray is still an option for the Stage 4.3 "run inside Docker" check,
since that runs on Linux.
"""

import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingResult:
    wall_times_s: list[float] = field(default_factory=list)

    @property
    def p50(self) -> float:
        return _percentile(self.wall_times_s, 50)

    @property
    def p95(self) -> float:
        return _percentile(self.wall_times_s, 95)

    @property
    def max(self) -> float:
        return max(self.wall_times_s) if self.wall_times_s else 0.0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def time_calls(fn: Callable[..., Any], inputs: list[tuple], repeats: int = 1) -> TimingResult:
    """Time `fn(*args)` for each item in `inputs`, `repeats` times each."""
    result = TimingResult()
    for args in inputs:
        for _ in range(repeats):
            start = time.perf_counter()
            fn(*args)
            result.wall_times_s.append(time.perf_counter() - start)
    return result


def peak_memory_mb(fn: Callable[..., Any], *args, **kwargs) -> tuple[Any, float]:
    """Returns (fn's return value, peak traced-memory in MB during the call)."""
    tracemalloc.start()
    try:
        out = fn(*args, **kwargs)
        _, peak = tracemalloc.get_traced_memory()
        return out, peak / 1e6
    finally:
        tracemalloc.stop()


def process_rss_mb() -> float:
    import psutil

    return psutil.Process().memory_info().rss / 1e6


def cold_start_s(import_and_warmup_fn: Callable[[], Any]) -> float:
    """Caller passes a zero-arg function that imports the pipeline module(s)
    and runs one warm-up parse — this measures everything from a fresh
    process's perspective. Run this in a subprocess for a true cold-start
    number; called in-process it only measures model load + warm-up time."""
    start = time.perf_counter()
    import_and_warmup_fn()
    return time.perf_counter() - start
