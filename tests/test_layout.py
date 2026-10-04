import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir import BBox, Document, Line, Page, Span  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402


def mk(text, x0, y0, x1, y1=None, size=10.0, bold=False):
    y1 = y1 if y1 is not None else y0 + size * 1.2
    bb = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
    return Line(id="X", page=0, bbox=bb, text=text, spans=[Span(text=text, bbox=bb, size=size, bold=bold)])


def run(lines):
    doc = Document(pages=[Page(number=0, width=600, height=800, lines=lines)])
    return analyze_layout(doc).pages[0].lines


def texts(lines):
    return [l.text for l in lines]


def test_two_columns_read_column_by_column():
    left = [mk(f"L{i} text here.", 40, 100 + i * 16, 250 - i) for i in range(8)]
    right = [mk(f"R{i} other words.", 300, 107 + i * 16, 520 - i) for i in range(8)]  # baselines not aligned
    out = texts(run(left + right))
    assert out == [f"L{i} text here." for i in range(8)] + [f"R{i} other words." for i in range(8)]


def test_full_width_header_comes_first_then_columns():
    header = [mk("JANE DOE", 40, 20, 520, size=24)]
    left = [mk(f"L{i} text here.", 40, 100 + i * 16, 250 - i) for i in range(6)]
    right = [mk(f"R{i} other words.", 300, 107 + i * 16, 520 - i) for i in range(6)]
    out = texts(run(right + left + header))
    assert out[0] == "JANE DOE"
    assert out[1:7] == [f"L{i} text here." for i in range(6)]


def test_right_aligned_dates_stay_on_their_row():
    lines = []
    for i, (org, date) in enumerate([("Acme Corp", "2020 - 2022"), ("Globex", "2018 - 2020"), ("Initech", "2016 - 2018")]):
        y = 100 + i * 40
        lines += [mk(org, 40, y, 200), mk(date, 460, y, 540), mk(f"did things at {org} for a while", 40, y + 14, 330)]
    out = texts(run(lines))
    assert "Acme Corp	2020 - 2022" in out and "Initech	2016 - 2018" in out  # one row, cells kept apart


def test_left_date_column_is_not_a_column():
    lines = []
    for i, date in enumerate(["Jan 2022 -", "Jul 2019 -", "Jan 2019 -"]):
        y = 100 + i * 50
        lines += [mk(date, 40, y, 100), mk(f"Engineer {i}", 130, y, 300, size=10, bold=True), mk(f"Built stuff number {i} for the team", 130, y + 14, 440)]
    out = texts(run(lines))
    assert "Jan 2022 -	Engineer 0" in out


def test_wrapped_bullet_is_merged_and_dehyphenated():
    first = mk("• Designed scalable backend services using Spring Boot and Post-", 40, 100, 400)
    second = mk("greSQL for the whole platform.", 52, 112, 300)
    third = mk("• Led migration of legacy applications.", 40, 124, 280)
    out = texts(run([first, second, third]))
    assert out[0].endswith("PostgreSQL for the whole platform.")
    assert len(out) == 2


def test_stacked_contact_lines_are_not_merged():
    lines = [mk("alex.johnson@gmail.com", 40, 100, 190), mk("www.alexjohnson.dev", 40, 112, 170), mk("alexjohnson", 40, 124, 110)]
    assert len(run(lines)) == 3


def test_features_body_size_headings_and_ids():
    body = [mk(f"normal body line number {i} with text", 40, 100 + i * 14, 400) for i in range(6)]
    heading = mk("EXPERIENCE", 40, 60, 200, size=14, bold=True)
    out = run(body + [heading])
    assert [l.id for l in out] == [f"L{i}" for i in range(len(out))]
    head = next(l for l in out if l.text == "EXPERIENCE")
    assert head.features.all_caps and head.features.bold and head.features.rel_size > 1.2
    assert out[1].features.rel_size == 1.0


def test_text_drawn_rule_is_dropped_and_flags_line_above():
    heading = mk("EXPERIENCE", 40, 100, 200, size=12, bold=True)
    rule = mk("_" * 60, 40, 114, 400)
    body = mk("Built things for the team in 2020.", 40, 130, 300)
    out = run([heading, rule, body])
    assert texts(out) == ["EXPERIENCE", "Built things for the team in 2020."]
    assert out[0].features.rule_below is True


def test_table_rows_are_not_wrapped_into_each_other():
    rows = [
        mk("B.Tech in IT", 40, 100, 120), mk("Dwarkadas College of Engineering", 160, 100, 330),
        mk("A.Y. 2024 - Present", 380, 100, 470), mk("CGPA: 9.10", 500, 100, 560),
        mk("HSC", 40, 114, 70), mk("Ramniranjan Junior College of Science", 160, 114, 360),
        mk("2023", 410, 114, 440), mk("79.2%", 510, 114, 560),
    ]
    out = texts(run(rows))
    assert out == [
        "B.Tech in IT	Dwarkadas College of Engineering	A.Y. 2024 - Present	CGPA: 9.10",
        "HSC	Ramniranjan Junior College of Science	2023	79.2%",
    ]


def test_first_line_indented_paragraph_merges():
    first = mk("BMS graduate specializing in finance with a strong foundation in analysis and", 60, 100, 540)
    second = mk("strategic thinking. Adept at conducting research and preparing reports.", 40, 112, 540)
    assert len(run([first, second])) == 1


def test_heading_below_a_multi_cell_row_is_not_glued_to_it():
    # Aagam's resume: "PROJECTS" sat right under "National English High School | Score: 90.0%"
    rows = [
        mk("National English High School (SSC)", 50, 185, 223),
        mk("Score: 90.0%", 482, 183, 548),
        mk("PROJECTS", 50, 206, 103, size=11, bold=True),
    ]
    out = texts(run(rows))
    assert out == ["National English High School (SSC)\tScore: 90.0%", "PROJECTS"]
