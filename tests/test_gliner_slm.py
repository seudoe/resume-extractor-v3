"""Offline tests for the model-backed refiners: the models are replaced by canned outputs, so no torch/GGUF is loaded."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir import BBox, Document, Line, Page, Span  # noqa: E402
from rx3.fields.gliner import GlinerRefiner  # noqa: E402
from rx3.fields.rules import extract_rules  # noqa: E402
from rx3.fields.slm import SlmRefiner  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402


def mk(text, y, size=10.0, bold=False):
    bb = BBox(x0=40, y0=y, x1=420, y1=y + size * 1.2)
    return Line(id="X", page=0, bbox=bb, text=text, spans=[Span(text=text, bbox=bb, size=size, bold=bold)])


def doc():
    rows = [("Jane Doe", True, 22), ("EXPERIENCE", True, 13), ("Strategy Lead at Globex Holdings   Jan 2021 - Present", True, 10),
            ("• Ran quarterly planning.", False, 10)]
    lines = [mk(t, 40 + 16 * i, size=s, bold=b) for i, (t, b, s) in enumerate(rows)]
    return analyze_layout(Document(pages=[Page(number=0, width=600, height=800, lines=lines)]))


class FakeGliner(GlinerRefiner):
    def __init__(self, result, **kw):
        super().__init__(use_cache=False, **kw)
        self.result = result

    def predict(self, section, texts):
        return [self.result for _ in texts]


def rec(company, conf, start):
    return {"work": [{"company": {"text": company, "confidence": conf, "start": start, "end": start + len(company)},
                      "title": {"text": "Strategy Lead", "confidence": 0.95, "start": 0, "end": 13}}]}


def test_gliner_overrides_only_above_confidence_and_keeps_line_pointers():
    d = doc()
    base = extract_rules(d)["workHistory"][0]
    start = "Strategy Lead at Globex Holdings   Jan 2021 - Present".index("Globex")
    hi = extract_rules(d, refiner=FakeGliner(rec("Globex Holdings", 0.97, start), strategy="combined"))["workHistory"][0]
    lo = extract_rules(d, refiner=FakeGliner(rec("Globex Holdings", 0.40, start), strategy="combined"))["workHistory"][0]
    off = extract_rules(d, refiner=FakeGliner(rec("Globex Holdings", 0.99, start), strategy="rules"))["workHistory"][0]
    assert hi["company"] == "Globex Holdings"
    assert lo["company"] == base["company"] and off["company"] == base["company"]  # below the 0.9 cut-off / rules strategy: untouched
    assert hi["_gliner"]["company"]["lines"] and hi["_gliner"]["company"]["conf"] == 0.97  # provenance kept for debug


def test_slm_pointer_answers_must_be_grounded_in_the_pointed_line():
    class FakeSlm(SlmRefiner):
        def __init__(self, answer):
            super().__init__("slm06", use_cache=False)
            self.answer = answer

        def _ask(self, section, lines):
            return self.answer

    d = doc()
    good = {"company": {"line": 0, "text": "Globex Holdings"}, "title": {"line": 0, "text": "Strategy Lead"}, "location": {"line": -1, "text": ""}}
    bad = {"company": {"line": 0, "text": "Initech"}, "title": {"line": 9, "text": "Strategy Lead"}, "location": {"line": 0, "text": ""}}
    assert extract_rules(d, refiner=FakeSlm(good))["workHistory"][0]["company"] == "Globex Holdings"
    base = extract_rules(d)["workHistory"][0]
    out = extract_rules(d, refiner=FakeSlm(bad))["workHistory"][0]
    assert out["company"] == base["company"] and out["title"] == base["title"]  # invented text / out-of-range pointer: dropped
