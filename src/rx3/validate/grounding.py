"""Grounding (PROMPT.md §5 Stage 12): every output string must be traceable to source lines.

A string is grounded when its normalised form occurs in a source line (exact, searched in the entry's own lines
first) or fuzzily (>= 0.9, partial alignment) anywhere in the document. Anything else is dropped and logged as a
hallucination candidate. Values the pipeline *normalises* (ISO dates, canonical degree names, E.164 phones,
canonical skill names, taxonomy group names, enums) are not text copies; they inherit the provenance of the raw
text they came from (the entry's lines) and are checked through that raw text where possible."""

import bisect
import re
import unicodedata
from dataclasses import dataclass, field

from ir import Document
from rapidfuzz import fuzz

from rx3.normalise._tech import TECH
from rx3.normalise.skills import _canon_map

FUZZY_MIN = 0.9
MIN_FUZZY_LEN = 6  # shorter strings must match exactly (partial_ratio on 3 chars matches anything)
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
TAXONOMY_GROUPS = set(TECH) | {"Other Skills"}
ENUM_PATHS = {("workHistory", "type"), ("publications", "type")}
ENUMS = {"job", "internship", "volunteer", "co-op", "paper", "article", "talk"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return _NON_ALNUM.sub(" ", s).strip()


@dataclass
class Dropped:
    path: str
    value: str
    score: float


@dataclass
class Grounded:
    data: dict
    dropped: list[Dropped] = field(default_factory=list)
    provenance: dict[str, list[str]] = field(default_factory=dict)  # field path -> source line ids
    n_checked: int = 0


class SourceIndex:
    def __init__(self, doc: Document):
        self.ids: list[str] = []
        self.texts: list[str] = []
        for p in doc.pages:
            for l in p.lines:
                t = norm(l.text)
                if t:
                    self.ids.append(l.id)
                    self.texts.append(t)
        self.concat = " ".join(self.texts)
        self.starts, pos = [], 0
        for t in self.texts:
            self.starts.append(pos)
            pos += len(t) + 1
        self.index = {i: k for k, i in enumerate(self.ids)}
        self.links = {l.uri for p in doc.pages for l in p.links}
        self.digits = re.sub(r"\D", "", " ".join(l.text for p in doc.pages for l in p.lines))

    def _lines_at(self, start: int, end: int) -> list[str]:
        a = bisect.bisect_right(self.starts, start) - 1
        b = bisect.bisect_right(self.starts, max(start, end - 1)) - 1
        return self.ids[a : b + 1]

    def find(self, s: str, prefer: list[str] | None = None) -> tuple[list[str], float] | None:
        """(line ids, score) for the normalised string, or None."""
        n = norm(s)
        if not n:
            return [], 1.0
        if prefer:
            keep = [self.index[i] for i in prefer if i in self.index]
            if keep:
                local = " ".join(self.texts[k] for k in keep)
                if n in local:
                    own = [self.ids[k] for k in keep if n in self.texts[k]]
                    return (own or [self.ids[k] for k in keep]), 1.0
        pos = self.concat.find(n)
        if pos >= 0:
            return self._lines_at(pos, pos + len(n)), 1.0
        if len(n) >= MIN_FUZZY_LEN:
            al = fuzz.partial_ratio_alignment(n, self.concat)
            if al and al.score / 100 >= FUZZY_MIN:
                return self._lines_at(al.dest_start, al.dest_end), al.score / 100
            sub = self._ordered_tokens(n)
            if sub:
                return sub, 0.9
        return None

    def _ordered_tokens(self, n: str) -> list[str] | None:
        """Every token of `n` appears in order with at most 2 foreign tokens between neighbours: covers a value
        whose date was cut out of the middle ("Dean's List 2012 (Top 10%)" -> "Dean's List (Top 10%")."""
        toks = n.split()
        if len(toks) < 2:
            return None
        if not hasattr(self, "_tok"):
            self._tok = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\S+", self.concat)]
        words = [t[0] for t in self._tok]
        for i, w in enumerate(words):
            if w != toks[0]:
                continue
            j, last = 1, i
            for k in range(i + 1, min(len(words), i + 1 + len(toks) * 3)):
                if j < len(toks) and words[k] == toks[j] and k - last <= 3:
                    j, last = j + 1, k
            if j == len(toks):
                return self._lines_at(self._tok[i][1], self._tok[last][2])
        return None

    def alias_present(self, canonical: str) -> bool:
        """A canonical skill name is grounded when the name or any of its aliases occurs as whole words."""
        names = [a for a, (c, _) in _canon_map().items() if c == canonical] + [canonical.lower()]
        return any(re.search(rf"(?<![0-9a-z]){re.escape(norm(a))}(?![0-9a-z])", self.concat) for a in names if norm(a))


def _has_text(d: dict) -> bool:
    return any(isinstance(v, str) and v.strip() for k, v in d.items() if not k.startswith("_"))


_had_text = _has_text


def ground(data: dict, doc: Document) -> Grounded:
    """Return a copy of `data` with ungrounded strings removed. Entry dicts must still carry `_lines`."""
    idx = SourceIndex(doc)
    res = Grounded(data={})

    def check(value: str, path: str, prefer: list[str] | None, kind: str = "text") -> bool:
        res.n_checked += 1
        if kind == "enum" and value in ENUMS:
            return True
        if kind == "group":
            return value in TAXONOMY_GROUPS or idx.find(value, prefer) is not None
        if kind == "skill":
            hit = idx.find(value, prefer)
            if hit or idx.alias_present(value):
                res.provenance[path] = hit[0] if hit else (prefer or [])
                return True
            res.dropped.append(Dropped(path, value, 0.0))
            return False
        if kind == "phone":
            d = re.sub(r"\D", "", value)
            return bool(d) and d[-8:] in idx.digits
        if kind == "link":
            bare = re.sub(r"^https?://(?:www\.)?|/+$", "", value, flags=re.I)  # a header may rebuild a URL from "github: handle"
            tail = bare.rstrip("/").rsplit("/", 1)[-1]
            if value in idx.links or idx.find(bare, prefer) or (len(tail) >= 3 and idx.find(tail, prefer)):
                return True
            res.dropped.append(Dropped(path, value, 0.0))
            return False
        if kind == "score":  # "CGPA: 9.875": the label is capitalised, the figure must be in the source
            nums = re.findall(r"\d+(?:\.\d+)?", value)
            return all(idx.find(x, prefer) for x in nums) if nums else True
        hit = idx.find(value, prefer)
        if hit:
            if hit[0]:
                res.provenance[path] = hit[0]
            return True
        res.dropped.append(Dropped(path, value, 0.0))
        return False

    def walk(node, path: str, prefer, section: str, key: str = ""):
        if isinstance(node, str):
            if not node.strip():
                return node
            kind = "text"
            if (section, key) in ENUM_PATHS:
                kind = "enum"
            elif (section == "skills" and key == "name") or key == "techStack":
                kind = "skill"
            elif section == "skills" and key == "field":
                kind = "group"
            elif section == "education" and key == "output":
                kind = "score"
            elif section == "education" and path.endswith("field.type"):
                return node  # canonical degree name: derived from the entry's raw degree text
            elif key == "phone_no":
                kind = "phone"
            elif key in ("github_profile", "linkedin", "link", "repo", "live", "demo"):
                kind = "link"
            elif "extra_links" in path and key == "name":
                return node  # link label named after its host (e.g. "LeetCode"), not copied text
            elif key in ("lastUsed", "start", "end"):
                return node  # derived dates / "Present"
            return node if check(node, path, prefer, kind) else ""
        if isinstance(node, dict):
            local = node.get("_lines", prefer)
            out = {}
            for k, v in node.items():
                if k in ("_lines", "_heading"):
                    out[k] = v
                elif k == "period":
                    out[k] = v  # derived from the entry's raw date text
                else:
                    out[k] = walk(v, f"{path}.{k}" if path else k, local, section, k)
            return out
        if isinstance(node, list):
            kept = []
            for i, v in enumerate(node):
                w = walk(v, f"{path}[{i}]", prefer, section, key)
                if isinstance(w, str) and not w and isinstance(v, str) and v.strip():
                    continue  # ungrounded list element: dropped
                if isinstance(w, dict) and _had_text(v) and not _has_text(w):
                    continue  # every text field of the element failed grounding (e.g. a skill tool)
                kept.append(w)
            return kept
        return node

    for k, v in data.items():
        res.data[k] = walk(v, k, None, k)
    return res
