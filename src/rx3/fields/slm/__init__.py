"""Small-LM experiment (PROMPT.md §5 Stage 13). OFF by default (`RX3_ENABLE_SLM=0`); nothing imports this unless asked.

Pointer approach: per rules-segmented entry block the model sees numbered lines and must answer, for every field,
the *line number* and the text copied from that line, in JSON enforced by llama.cpp's JSON-schema grammar (so it
cannot ramble or open a thinking block). Each answer is grounded: the copied text must occur in the claimed line,
otherwise it is dropped. Qwen3 thinking is disabled with `/no_think` (and the grammar forbids anything but JSON).
Same refiner interface as the GLiNER one, so `extract_rules(refiner=SlmRefiner(...))` and the eval harness work as-is."""

import hashlib
import json
import os
import re
import time
from pathlib import Path

from rx3.fields.gliner import FIELD_MAP, _get, _set  # noqa: F401  (same field map as GLiNER)

ROOT = Path(__file__).resolve().parents[4]
CACHE_PATH = ROOT / "data" / "cache" / "slm_cache.json"
MODELS = {"slm06": ROOT / "models" / "slm" / "Qwen3-0.6B-Q4_K_M.gguf", "slm17": ROOT / "models" / "slm" / "Qwen3-1.7B-Q4_K_M.gguf"}

FIELDS = {
    "workHistory": {"company": "employer organisation name", "title": "job title or role", "location": "city or region"},
    "education": {"institution": "school, college or university name", "degree": "degree or qualification (e.g. Bachelor of Technology, HSC)",
                  "field_of_study": "subject or major"},
}
TASK = {"workHistory": "a work-experience entry", "education": "an education entry"}


def _schema(section: str) -> dict:
    item = {"type": "object", "properties": {"line": {"type": "integer"}, "text": {"type": "string"}}, "required": ["line", "text"]}
    f = {k: item for k in FIELDS[section]}  # no null branch: tiny models always pick it. Absent = line -1, text ""
    return {"type": "object", "properties": f, "required": list(f)}


def _prompt(section: str, lines: list[tuple[str, str]]) -> list[dict]:
    body = "\n".join(f"[{i}] {t}" for i, (_, t) in enumerate(lines))
    fields = "\n".join(f'- {k}: {d}' for k, d in FIELDS[section].items())
    user = (f"Below are the lines of {TASK[section]} from a resume. For each field give the line number and the exact text "
            f"copied from that line. If the field is absent use line -1 and an empty text. Never invent or reword text.\n\nFields:\n{fields}\n\n"
            f"Lines:\n{body}\n\n/no_think")
    return [{"role": "user", "content": user}]


class SlmRefiner:
    def __init__(self, model: str = "slm06", use_cache: bool = True):
        self.name = model
        self.llm = None
        self.use_cache = use_cache
        self.cache: dict = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if use_cache and CACHE_PATH.exists() else {}
        self._dirty = False
        self.last_ms = 0.0

    def _load(self):
        if self.llm is None:
            from llama_cpp import Llama

            self.llm = Llama(model_path=str(MODELS[self.name]), n_ctx=1024, n_threads=int(os.environ.get("RX3_TORCH_THREADS", "2")), verbose=False)
        return self.llm

    def _ask(self, section: str, lines: list[tuple[str, str]]) -> dict:
        blob = "\n".join([self.name, section, *[t for _, t in lines]])
        key = hashlib.sha1(blob.encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        t0 = time.perf_counter()
        out = self._load().create_chat_completion(messages=_prompt(section, lines), temperature=0.0, max_tokens=160,
                                                  response_format={"type": "json_object", "schema": _schema(section)})
        try:
            res = json.loads(out["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError, IndexError):
            res = {}
        res["_ms"] = round((time.perf_counter() - t0) * 1000)
        self.cache[key] = res
        self._dirty = True
        return res

    def save_cache(self) -> None:
        if self.use_cache and self._dirty:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
            self._dirty = False

    def __call__(self, section: str, entries: list, dicts: list[dict]) -> list[dict]:
        if section not in FIELDS:
            return dicts
        t0 = time.perf_counter()
        for e, d in zip(entries, dicts):
            lines = [(l.id, l.text.replace("\t", " | ")) for l in e.head]
            res = self._ask(section, lines)
            for path, gf in FIELD_MAP[section]:
                v = res.get(gf)
                if not isinstance(v, dict) or not isinstance(v.get("line"), int) or not (0 <= v["line"] < len(lines)):
                    continue
                text = str(v.get("text", "")).strip()
                src = lines[v["line"]][1]
                if text and re.sub(r"\W+", "", text.lower()) in re.sub(r"\W+", "", src.lower()):  # grounded in the pointed line
                    _set(d, path, text)
        self.last_ms += (time.perf_counter() - t0) * 1000
        self.save_cache()
        return dicts
