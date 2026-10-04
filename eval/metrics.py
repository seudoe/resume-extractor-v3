"""PROMPT.md §4.2 metrics. Every function takes/returns plain dicts (not
Pydantic instances) so it can score any candidate JSON — the v2 baseline,
v3 at any stage, or a gold file scored against itself for a sanity check —
without needing the v3 pipeline to exist yet.
"""

import re
import unicodedata
from datetime import datetime

from rapidfuzz.distance import JaroWinkler
from rapidfuzz.fuzz import token_set_ratio

from matching import SECTION_KEYS, match_entities

CORRECT_KEY_SIMILARITY = 0.9  # PROMPT.md §4.2: Jaro-Winkler >= 0.9 for alignment correctness
HALLUCINATION_SIMILARITY = 0.9  # "fuzzy >= 0.9" for hallucination detection


def _norm(s) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).strip().lower()  # ligatures etc.; the pipeline's text is NFKC + ftfy
    s = re.sub(r"[.,;:!?'\"()\[\]‘’“”«»„]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _get(d: dict, path: str):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


# ---------------------------------------------------------------------------
# Scalar fields (name, email, phone, linkedin, github exact; summary fuzzy)
# ---------------------------------------------------------------------------


def _phones_match(a: str, b: str) -> bool:
    import phonenumbers

    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return _norm(a) == _norm(b)
    try:
        pa = phonenumbers.parse(a, "IN")
        pb = phonenumbers.parse(b, "IN")
        return phonenumbers.format_number(pa, phonenumbers.PhoneNumberFormat.E164) == phonenumbers.format_number(
            pb, phonenumbers.PhoneNumberFormat.E164
        )
    except phonenumbers.NumberParseException:
        return _norm(a) == _norm(b)


SCALAR_FIELDS = {
    "metaDetails.name": ("exact", _norm),
    "metaDetails.email": ("exact", _norm),
    "metaDetails.phone_no": ("phone", None),
    "metaDetails.linkedin": ("exact", _norm),
    "metaDetails.github_profile": ("exact", _norm),
    "summary": ("fuzzy", 0.9),
}


def score_scalar_fields(predicted: dict, gold: dict) -> dict:
    """Returns {field: {"applicable": bool, "correct": bool|None}}.

    `applicable=False` means gold has no value for this field, so it's
    excluded from the denominator rather than counted as a failure.
    """
    out = {}
    for field, (kind, param) in SCALAR_FIELDS.items():
        gold_val = _get(gold, field)
        pred_val = _get(predicted, field)
        applicable = bool(gold_val)
        if not applicable:
            out[field] = {"applicable": False, "correct": None}
            continue
        if kind == "exact":
            correct = param(pred_val) == param(gold_val)
        elif kind == "phone":
            correct = _phones_match(pred_val, gold_val)
        elif kind == "fuzzy":
            correct = JaroWinkler.similarity(_norm(pred_val), _norm(gold_val)) >= param
        else:
            raise ValueError(kind)
        out[field] = {"applicable": True, "correct": correct}
    return out


# ---------------------------------------------------------------------------
# Entity lists: P/R/F1 via Hungarian matching + per-subfield accuracy
# ---------------------------------------------------------------------------


def _date_ym(s: str) -> tuple[int, int] | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s)[:10])
        return (dt.year, dt.month)
    except ValueError:
        return None


# (subfield path, comparator kind, param)
SUBFIELD_SPECS: dict[str, list[tuple[str, str, float | None]]] = {
    "workHistory": [
        ("company", "fuzzy", 0.85),
        ("title", "fuzzy", 0.85),
        ("location", "exact", None),
        ("type", "exact", None),
        ("period.start", "date_ym", None),
        ("period.end", "date_ym", None),
        ("period.isCurrent", "exact", None),
    ],
    "education": [
        ("institution", "fuzzy", 0.85),
        ("field.type", "exact", None),
        ("field.course", "fuzzy", 0.75),
        ("period.start", "date_ym", None),
        ("period.end", "date_ym", None),
    ],
    "projects": [("title", "fuzzy", 0.85)],
    "certifications": [("name", "fuzzy", 0.85), ("issuer", "fuzzy", 0.75), ("type", "exact", None)],
    "awards": [("name", "fuzzy", 0.85), ("issuingBody", "fuzzy", 0.75)],
}


def _subfield_correct(pred: dict, gold: dict, path: str, kind: str, param) -> bool | None:
    gv = _get(gold, path)
    pv = _get(pred, path)
    if kind == "date_ym":
        gv_ym, pv_ym = _date_ym(gv), _date_ym(pv)
        if gv_ym is None:
            return None
        return gv_ym == pv_ym
    if gv in (None, "", False) and not isinstance(gv, bool):
        return None
    if kind == "exact":
        return _norm(pv) == _norm(gv)
    if kind == "fuzzy":
        return JaroWinkler.similarity(_norm(pv), _norm(gv)) >= param
    raise ValueError(kind)


def score_entity_section(predicted: list[dict], gold: list[dict], section: str) -> dict:
    key_fn = SECTION_KEYS[section]
    matched, unmatched_p, unmatched_g = match_entities(predicted, gold, key_fn)

    correct_pairs = [
        (i, j)
        for i, j in matched
        if JaroWinkler.similarity(_norm(key_fn(predicted[i])), _norm(key_fn(gold[j]))) >= CORRECT_KEY_SIMILARITY
    ]
    precision = len(correct_pairs) / len(predicted) if predicted else 1.0
    recall = len(correct_pairs) / len(gold) if gold else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    subfield_results: dict[str, list[bool]] = {}
    for i, j in matched:
        for path, kind, param in SUBFIELD_SPECS.get(section, []):
            ok = _subfield_correct(predicted[i], gold[j], path, kind, param)
            if ok is not None:
                subfield_results.setdefault(path, []).append(ok)

    subfield_accuracy = {
        path: sum(vals) / len(vals) for path, vals in subfield_results.items() if vals
    }

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "n_predicted": len(predicted),
        "n_gold": len(gold),
        "n_matched": len(matched),
        "n_correct": len(correct_pairs),
        "omission_rate": (len(gold) - len(correct_pairs)) / len(gold) if gold else 0.0,
        "subfield_accuracy": subfield_accuracy,
    }


# ---------------------------------------------------------------------------
# Text lists: token-F1 (responsibilities/achievements/description), bullet count
# ---------------------------------------------------------------------------


def _tokens(s: str) -> set[str]:
    return set(_norm(s).split())


def token_f1(predicted: list[str], gold: list[str]) -> float:
    pred_tokens: set[str] = set()
    for s in predicted:
        pred_tokens |= _tokens(s)
    gold_tokens: set[str] = set()
    for s in gold:
        gold_tokens |= _tokens(s)
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    overlap = len(pred_tokens & gold_tokens)
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def bullet_count_accuracy(predicted: list[str], gold: list[str]) -> bool:
    return len(predicted) == len(gold)


# ---------------------------------------------------------------------------
# Skills: set P/R/F1 on normalised names
# ---------------------------------------------------------------------------


def skills_prf1(predicted: dict, gold: dict) -> dict:
    def names(parsed: dict) -> set[str]:
        out = set()
        for skill in parsed.get("skills", []):
            for tool in skill.get("tools", []):
                if tool.get("name"):
                    out.add(_norm(tool["name"]))
        return out

    p, g = names(predicted), names(gold)
    if not p and not g:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not p or not g:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    overlap = len(p & g)
    precision, recall = overlap / len(p), overlap / len(g)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


# ---------------------------------------------------------------------------
# Hallucination: % output strings not found in source text (no gold needed)
# ---------------------------------------------------------------------------


def _all_output_strings(parsed: dict) -> list[str]:
    strings = []

    def walk(node):
        if isinstance(node, str):
            if node.strip():
                strings.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(parsed)
    return strings


_DERIVED = re.compile(r"^(?:\d{4}-\d{2}(?:-\d{2})?|\+\d{7,15}|present|job|internship|volunteer|co-op|paper|article|talk|"
                      r"(?:cgpa|gpa|percentage|marks)\s*:.*)$", re.I)


def _is_derived(s: str, source_norm: str) -> bool:
    """Normalised values (PROMPT.md Stage 12: dates, phones, enums, score labels, canonical degree / skill names,
    taxonomy group names) are not text copies; they are verified through the raw text they came from. Skill and degree
    names count when one of their raw aliases occurs in the source."""
    if _DERIVED.match(s.strip()):
        return True
    if re.match(r"^https?://", s.strip(), re.I):  # a URL the header rebuilt from a handle ("github: seudoe"): the handle must be there
        tail = _norm(s.strip().rstrip("/").rsplit("/", 1)[-1])
        if len(tail) >= 3 and tail in source_norm:
            return True
    try:
        from rx3.normalise._tech import TECH
        from rx3.normalise.education import _COMPILED
        from rx3.normalise.skills import _canon_map
    except ImportError:
        return False
    if s in TECH or s == "Other Skills":
        return True
    if any(name == s for name, _ in _COMPILED):
        return True  # canonical degree: its abbreviation (B.Tech, MBA...) was in the entry's text
    return any(c == s and re.search(rf"(?<![0-9a-z]){re.escape(_norm(a))}(?![0-9a-z])", source_norm) for a, (c, _) in _canon_map().items())


def hallucination_rate(predicted: dict, source_text: str) -> dict:
    source_norm = _norm(source_text)
    strings = [x for x in _all_output_strings(predicted) if not _is_derived(x, source_norm)]
    if not strings:
        return {"rate": 0.0, "n_checked": 0, "n_hallucinated": 0, "examples": []}

    hallucinated = []
    for s in strings:
        s_norm = _norm(s)
        if not s_norm:
            continue
        # Substring match covers most cases cheaply; fall back to a fuzzy
        # containment check (token_set_ratio) for reordered/paraphrased text.
        if s_norm in source_norm:
            continue
        if token_set_ratio(s_norm, source_norm) / 100.0 >= HALLUCINATION_SIMILARITY:
            continue
        hallucinated.append(s)

    return {
        "rate": len(hallucinated) / len(strings),
        "n_checked": len(strings),
        "n_hallucinated": len(hallucinated),
        "examples": hallucinated[:10],
    }


# ---------------------------------------------------------------------------
# Schema validity / determinism / crash rate
# ---------------------------------------------------------------------------


def is_schema_valid(predicted: dict) -> tuple[bool, str | None]:
    import sys
    from pathlib import Path

    types_dir = Path(__file__).resolve().parent.parent / "types"
    if str(types_dir) not in sys.path:
        sys.path.insert(0, str(types_dir))
    from resume import ParsedResumeData

    try:
        ParsedResumeData.model_validate(predicted)
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def is_deterministic(run_fn, *args, n: int = 2, **kwargs) -> bool:
    import json as _json

    outputs = [run_fn(*args, **kwargs) for _ in range(n)]
    serialized = [_json.dumps(o, sort_keys=True, default=str) for o in outputs]
    return len(set(serialized)) == 1
