"""GLiNER2 zero-shot field extraction per entry block (PROMPT.md §5 Stage 10.2 #2).

For each rules-segmented entry the head lines are sent to `fastino/gliner2.5-base-v1` with a per-section schema
(`include_spans=True`). Returned character spans are mapped back to line ids (pointer principle), so every value is
an exact substring of the source and grounds by construction. `GlinerRefiner` plugs into `extract_rules(refiner=...)`
and merges with the rules output per field according to `strategy`:

    rules    - ignore GLiNER (the Stage 10 baseline)
    combined - per-field choice from eval/combine_search.py (COMBINE below): the shipped configuration
    gliner  - GLiNER value wherever it returned one
    hybrid  - GLiNER value when its confidence >= `min_conf[field]`, else the rules value
"""

import hashlib
import json
import os
import time
import warnings
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parents[4] / "data" / "cache" / "gliner_cache.json"
MODEL_ID = "fastino/gliner2.5-base-v1"
THRESHOLD = 0.3  # low on purpose: the merge step applies the real per-field cut-off using the returned confidence

SCHEMAS = {
    "workHistory": {"work": ["company::str::employer organisation name", "title::str::job title or role",
                             "location::str::city, region or remote"]},
    "education": {"edu": ["institution::str::school, college or university name",
                          "degree::str::degree or qualification name such as Bachelor of Technology or HSC",
                          "field_of_study::str::subject or major"]},
}
# (rules-dict path, gliner field) per section
FIELD_MAP = {
    "workHistory": [("company", "company"), ("title", "title"), ("location", "location")],
    "education": [("institution", "institution"), ("field.type", "degree"), ("field.course", "field_of_study")],
}


# Chosen from eval/combine_search.py (LiveCareer weak labels n=100 + AAA vs LLM JSONs, 2026-10-04). One joint cut-off:
# GLiNER overrides a rules value only at confidence >= 0.9 (hybrid@0.9 vs rules: company 57.6 -> 84.3, LiveCareer school
# 53.9 -> 77.0, AAA institution 82.8 -> 89.8, course 52.1 -> 61.5; title/degree within ~1-3 points either way, so they
# are not special-cased). value = minimum confidence to override; None = keep the rules value.
COMBINE: dict[str, float | None] = {
    "workHistory.company": 0.9,
    "workHistory.title": 0.9,
    "workHistory.location": 0.9,
    "education.institution": 0.9,
    "education.field.type": 0.9,
    "education.field.course": 0.9,
}


def block_text(entry) -> tuple[str, list[tuple[int, str]]]:
    """Head lines as one text (cells joined with ' | ') and the (start offset, line id) of every line."""
    parts, starts, pos = [], [], 0
    for l in entry.head:
        t = l.text.replace("\t", " | ")
        starts.append((pos, l.id))
        parts.append(t)
        pos += len(t) + 1
    return "\n".join(parts), starts


def _line_ids(starts: list[tuple[int, str]], a: int, b: int) -> list[str]:
    ids = [lid for i, (s, lid) in enumerate(starts) if s <= max(a, b - 1) and (i + 1 == len(starts) or starts[i + 1][0] > a)]
    return ids or [starts[0][1]]


def _set(d: dict, path: str, value: str) -> None:
    head, _, tail = path.partition(".")
    if tail:
        d[head][tail] = value
    else:
        d[head] = value


def _get(d: dict, path: str) -> str:
    head, _, tail = path.partition(".")
    return d[head][tail] if tail else d[head]


class GlinerRefiner:
    def __init__(self, strategy: str = "hybrid", min_conf: dict[str, float] | None = None, use_cache: bool = True,
                 default_conf: float = 0.5):
        self.strategy = strategy
        self.min_conf = min_conf or {}
        self.default_conf = default_conf
        self.model = None
        self.use_cache = use_cache
        self.cache: dict = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if use_cache and CACHE_PATH.exists() else {}
        self._dirty = False

    def _load(self):
        if self.model is None:
            warnings.filterwarnings("ignore")
            from gliner2 import AutoExtractor  # imported lazily: torch is heavy and only needed here

            import torch

            torch.set_num_threads(int(os.environ.get("RX3_TORCH_THREADS", "2")))
            self.model = AutoExtractor.from_pretrained(MODEL_ID)
        return self.model

    def save_cache(self) -> None:
        if self.use_cache and self._dirty:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
            self._dirty = False

    def predict(self, section: str, texts: list[str]) -> list[dict]:
        keys = [hashlib.sha1(f"{section}\n{t}".encode()).hexdigest() for t in texts]
        todo = [(k, t) for k, t in dict(zip(keys, texts)).items() if k not in self.cache]
        if todo:
            res = self._load().batch_extract_json([t for _, t in todo], SCHEMAS[section], batch_size=8, threshold=THRESHOLD,
                                                  include_confidence=True, include_spans=True)
            for (k, _), r in zip(todo, res):
                self.cache[k] = r
                self._dirty = True
        return [self.cache[k] for k in keys]

    last_ms = 0.0  # time spent in model inference during the latest extraction (reset by the caller)

    def __call__(self, section: str, entries: list, dicts: list[dict]) -> list[dict]:
        t0 = time.perf_counter()
        try:
            return self._refine(section, entries, dicts)
        finally:
            self.last_ms += (time.perf_counter() - t0) * 1000

    def _refine(self, section: str, entries: list, dicts: list[dict]) -> list[dict]:
        if section not in SCHEMAS or self.strategy == "rules" or not entries:
            return dicts
        blocks = [block_text(e) for e in entries]
        results = self.predict(section, [b[0] for b in blocks])
        key = next(iter(SCHEMAS[section]))
        for d, (text, starts), r in zip(dicts, blocks, results):
            recs = r.get(key) or []
            rec = recs[0] if recs else {}
            found = {}
            for path, gf in FIELD_MAP[section]:
                v = rec.get(gf)
                if isinstance(v, list):
                    v = v[0] if v else None
                if isinstance(v, dict) and v.get("text"):
                    found[path] = (v["text"].strip(), float(v.get("confidence", 0.0)), _line_ids(starts, v.get("start", 0), v.get("end", 0)))
            d["_gliner"] = {p: {"conf": round(c, 3), "lines": ids, "text": t} for p, (t, c, ids) in found.items()}
            for path, (t, c, _) in found.items():
                fkey = f"{section}.{path}"
                if self.strategy == "combined":
                    cut = COMBINE.get(fkey)
                    use = cut is not None and c >= cut
                else:
                    use = self.strategy == "gliner" or (self.strategy == "hybrid" and c >= self.min_conf.get(fkey, self.default_conf))
                if use:
                    _set(d, path, t)
        self.save_cache()
        return dicts


_SHARED: GlinerRefiner | None = None


def shared_refiner() -> GlinerRefiner:
    """Process-wide refiner (model loaded once) for the pipeline: `combined` strategy, no disk cache."""
    global _SHARED
    if _SHARED is None:
        _SHARED = GlinerRefiner("combined", use_cache=False)
    return _SHARED
