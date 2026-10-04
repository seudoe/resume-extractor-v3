import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir import BBox, Document, Line, Page, Span  # noqa: E402
from rx3.fields.rules import extract_rules  # noqa: E402
from rx3.fields.rules.dates import find_range, to_iso  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402


def mk(text, y, size=10.0, bold=False, x0=40, x1=420):
    bb = BBox(x0=x0, y0=y, x1=x1, y1=y + size * 1.2)
    return Line(id="X", page=0, bbox=bb, text=text, spans=[Span(text=text, bbox=bb, size=size, bold=bold)])


def run(rows):
    """rows: (text, bold, size) top to bottom, 16 pt apart."""
    lines = [mk(t, 40 + 16 * i, size=s, bold=b) for i, (t, b, s) in enumerate(rows)]
    return extract_rules(analyze_layout(Document(pages=[Page(number=0, width=600, height=800, lines=lines)])))


def test_dates():
    f = find_range("Jun 2023 – Present")
    assert (f.start, f.end, f.current) == ("2023-06-01", None, True)
    assert find_range("08/2023 to 05/2024").end == "2024-05-01"
    assert find_range("2022-23").end == "2023-01-01"
    assert find_range("Aug '22 - Dec '22").start == "2022-08-01"
    assert find_range("Expected May 2027").end == "2027-05-01" and find_range("Expected May 2027").start == ""
    assert find_range("Led 40 engineers") is None
    assert to_iso("2019") == "2019-01-01"


def test_styled_entries_with_dates_and_wrapped_title_above_date():
    r = run([
        ("Jane Doe", True, 22), ("EXPERIENCE", True, 13),
        ("Senior Engineer, Acme Inc. Jan 2022 - Present", True, 10),
        ("• Built billing services for the team.", False, 10), ("• Reduced latency by 30%.", False, 10),
        ("Data Analyst", False, 10), ("Mar 2019 - Dec 2021 Globex Corporation", False, 10),
        ("• Wrote weekly reports for management.", False, 10),
        ("• I won the 2020 Employee of the Year Award.", False, 10),  # a year inside a sentence is not an entry
    ])
    w = r["workHistory"]
    assert [e["title"] for e in w] == ["Senior Engineer", "Data Analyst"]
    assert w[0]["company"] == "Acme Inc." and w[0]["period"]["isCurrent"]
    assert w[1]["period"] == {"start": "2019-03-01", "end": "2021-12-01", "isCurrent": False}
    assert len(w[1]["responsibilities"]) == 2


def test_education_rows_with_several_degrees_split_and_institution_lifted():
    r = run([
        ("Jane Doe", True, 22), ("EDUCATION", True, 13),
        ("Master of Science : Data Science University of Boston 2020 Bachelor of Science : Physics University of Tufts 2018", False, 10),
    ])
    e = r["education"]
    assert [x["institution"] for x in e] == ["University of Boston", "University of Tufts"]
    assert e[0]["field"] == {"type": "Master of Science", "course": "Data Science"}
    assert e[1]["period"]["end"] == "2018-01-01"
