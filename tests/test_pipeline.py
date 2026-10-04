import json
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir import BBox, Document, Line, Page  # noqa: E402
from rx3.pipeline import UnreadableDocument, UnsupportedFormat, extract  # noqa: E402
from rx3.validate import clean, confidence  # noqa: E402
from rx3.validate.grounding import ground  # noqa: E402


def doc_of(*texts):
    lines = [Line(id=f"L{i}", page=0, bbox=BBox(x0=0, y0=i * 12, x1=100, y1=i * 12 + 10), text=t) for i, t in enumerate(texts)]
    return Document(pages=[Page(number=0, width=600, height=800, lines=lines)])


def make_pdf() -> bytes:
    pdf = pymupdf.open()
    page = pdf.new_page()
    rows = ["Jane Doe", "jane.doe@example.com", "EXPERIENCE", "Senior Engineer, Acme Inc.  Jan 2022 - Present",
            "• Built billing services and cut latency by 35%.", "EDUCATION", "B.Tech in Computer Science  Aug 2016 - May 2020",
            "Indian Institute of Technology", "SKILLS", "Languages: py, JavaScript, SQL"]
    for i, r in enumerate(rows):
        page.insert_text((50, 60 + i * 22), r, fontsize=18 if i == 0 else 11)
    return pdf.tobytes()


def test_grounding_drops_invented_text_keeps_normalised_values():
    doc = doc_of("Senior Engineer, Acme Inc. Jan 2022 - Present", "Built billing services in Python",
                 "Dean's List 2012 (Top 10%)", "github: janedoe")
    data = {
        "workHistory": [{"title": "Senior Engineer", "company": "Acme Inc.", "location": "", "type": "job",
                         "period": {"start": "2022-01-01", "end": None, "isCurrent": True},
                         "responsibilities": ["Built billing services in Python", "Led a team of 40 at Google"], "achievements": [],
                         "_lines": ["L0", "L1"]}],
        "awards": [{"name": "Dean's List", "issuingBody": "Dean's List (Top 10%", "date": "2012", "justification": "", "_lines": ["L2"]}],
        "skills": [{"field": "Programming Languages", "yearsOfExperience": 0, "lastUsed": "", "tools": [{"name": "Python", "score": None}]},
                   {"field": "Cloud", "yearsOfExperience": 0, "lastUsed": "", "tools": [{"name": "Kubernetes", "score": None}]}],
        "metaDetails": {"github_profile": "https://github.com/janedoe", "linkedin": "https://linkedin.com/in/ghost"},
    }
    g = ground(data, doc)
    w = g.data["workHistory"][0]
    assert w["responsibilities"] == ["Built billing services in Python"]  # the invented bullet is gone
    assert w["period"]["start"] == "2022-01-01"  # derived date kept
    assert g.data["awards"][0]["issuingBody"] == "Dean's List (Top 10%"  # date cut from the middle still grounds
    assert [t["name"] for s in g.data["skills"] for t in s["tools"]] == ["Python"]  # Kubernetes never appears
    assert g.data["metaDetails"]["github_profile"] and g.data["metaDetails"]["linkedin"] == ""  # handle present / absent
    assert {d.value for d in g.dropped} == {"Led a team of 40 at Google", "Kubernetes", "https://linkedin.com/in/ghost"}


def test_dedupe_order_and_validation_fallback():
    def work(title, line, start="2020-01-01"):
        return {"title": title, "company": "Acme", "location": "", "type": "job", "period": {"start": start, "end": None, "isCurrent": False},
                "responsibilities": [title], "achievements": [], "_lines": [line]}

    data = {"workHistory": [work("Engineer", "L9"), work("Analyst", "L2", "2018-01-01"), work("Engineer ", "L10"),
                            {**work("", "L11"), "company": "", "period": {"start": "", "end": None, "isCurrent": False}}]}
    out, notes = clean.dedupe_and_order({**{k: [] for k in ("education", "projects", "certifications", "awards", "affiliations", "publications", "languages", "interests", "skills")}, **data})
    assert [e["title"] for e in out["workHistory"]] == ["Analyst", "Engineer"]  # ordered by line, duplicate merged, empty dropped
    assert any("merged duplicate" in n for n in notes)
    bad = {"workHistory": [{"title": "ok", "period": {"start": "", "end": None, "isCurrent": "not-a-bool"}}], "summary": "fine"}
    final, vnotes = clean.validate(bad)
    assert final["summary"] == "fine" and final["workHistory"] == [] and vnotes  # bad entry dropped, never raises


def test_extract_end_to_end_schema_determinism_and_debug():
    pdf = make_pdf()
    a = extract(pdf, "jane.pdf", debug=True, with_confidence=True)
    b = extract(pdf, "jane.pdf", debug=True, with_confidence=True)
    for x in (a, b):
        x["_debug"].pop("timings_ms")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)  # deterministic
    assert a["metaDetails"]["name"] == "Jane Doe" and a["metaDetails"]["email"] == "jane.doe@example.com"
    w = a["workHistory"][0]
    assert w["title"] == "Senior Engineer" and w["period"]["isCurrent"] and w["achievements"]
    assert a["education"][0]["field"]["type"] == "Bachelor of Technology"
    assert "Python" in [t["name"] for s in a["skills"] for t in s["tools"]]
    assert all(0.0 <= v <= 1.0 for v in a["_confidence"].values()) and "workHistory[0].title" in a["_confidence"]
    assert not a["_debug"]["dropped_ungrounded"]
    assert "_lines" not in json.dumps({k: v for k, v in a.items() if k != "_debug"})
    assert {"ingest", "layout", "sections", "header", "entries", "normalise", "ground"} <= set(extract(pdf, "j.pdf", debug=True)["_debug"]["timings_ms"])


def test_extract_rejects_bad_input():
    with pytest.raises(UnsupportedFormat):
        extract(b"hello", "notes.txt")
    with pytest.raises(UnreadableDocument):
        extract(b"%PDF-1.7 definitely not a pdf", "broken.pdf")


def test_confidence_prefers_clear_titles():
    e = {"title": "Senior Software Engineer", "company": "Acme Inc.", "period": {"start": "2020-01-01", "end": None, "isCurrent": True}}
    weak = {**e, "title": "Responsible for the quarterly reconciliation of all intercompany balances", "period": {"start": "", "end": None, "isCurrent": False}}
    c = confidence.score({"workHistory": [e, weak]})
    assert c["workHistory[0].title"] > c["workHistory[1].title"] and 0 <= c["workHistory[1].title"] <= 1
