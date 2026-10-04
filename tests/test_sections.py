import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir import BBox, Document, Line, Page, Span  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402
from rx3.sections.segment import line_sections, segment_sections  # noqa: E402
from rx3.sections.synonyms import match_heading  # noqa: E402


def mk(text, x0, y0, x1, size=10.0, bold=False):
    bb = BBox(x0=x0, y0=y0, x1=x1, y1=y0 + size * 1.2)
    return Line(id="X", page=0, bbox=bb, text=text, spans=[Span(text=text, bbox=bb, size=size, bold=bold)])


def heading(text, y, size=13.0):
    return mk(text, 40, y, 40 + 7 * len(text), size=size, bold=True)


def body(text, y, x1=420):
    return mk(text, 40, y, x1)


def run(lines):
    doc = analyze_layout(Document(pages=[Page(number=0, width=600, height=800, lines=lines)]))
    secs = segment_sections(doc)
    return secs, line_sections(secs), doc


def names(secs):
    return [(s.name, s.heading) for s in secs if s.heading]


def test_synonyms_exact_fuzzy_and_non_headings():
    assert match_heading("Education") == ("education", 100.0)
    assert match_heading("AWARDS & HONORS")[0] == "awards"
    assert match_heading("CON TACT")[0] == "other"  # gap from small caps / OCR
    cert = match_heading("Certification Courses")  # near-match, never reported as exact
    assert cert and cert[0] == "certifications" and cert[1] < 100.0
    assert match_heading("Experience in Python and Java") is None
    assert match_heading("Led a team of five engineers across three product areas") is None


def test_styled_headings_split_sections_and_unknown_heading_is_other_not_glued():
    lines = [
        mk("Jane Doe", 40, 20, 200, size=22, bold=True),
        heading("EDUCATION", 80), body("B.Tech in Computer Science, 2024.", 100),
        heading("EXPERIENCE", 140), body("Built a billing service for the team.", 160),
        heading("GUIDING PHILOSOPHY", 200), body("Calm under pressure.", 220),
    ]
    secs, labels, _ = run(lines)
    assert [n for n, _ in names(secs)] == ["education", "workHistory", "other"]
    assert [s.name for s in secs][0] == "header"
    assert secs[1].line_ids and secs[3].line_ids  # content stays with its own section


def test_inline_row_opens_its_own_section_and_previous_section_continues():
    lines = [
        heading("SKILLS", 80), body("Python, SQL, Docker.", 100),
        mk("Languages\tEnglish, Hindi (Native), Marathi", 40, 120, 420, bold=False),
        body("Git and Linux.", 140),
    ]
    lines[2].spans[0] = Span(text="Languages", bbox=lines[2].bbox, size=10.0, bold=True)  # bold label cell
    secs, labels, doc = run(lines)
    by_text = {l.text.split("\t")[0]: labels[l.id] for l in doc.pages[0].lines}
    assert by_text["Languages"] == "languages"
    assert by_text["Git and Linux."] == "skills"


def test_programming_languages_row_inside_skills_is_a_subrow_not_spoken_languages():
    lines = [heading("Skills", 80), mk("Languages: C, C++, Java, Python, JavaScript", 40, 100, 420)]
    secs, labels, _ = run(lines)
    assert [s.name for s in secs if s.heading] == ["skills"]


def test_plain_tag_label_inside_a_content_section_is_not_a_section():
    lines = [heading("EDUCATION", 40), body("B.Tech.", 56), heading("GUIDING PHILOSOPHY", 80), mk("Leadership\tProblem Solving", 40, 100, 300)]
    secs, _, _ = run(lines)
    assert [s.name for s in secs if s.heading] == ["education", "other"]  # no "affiliations" from the tag row


def test_entry_subtitle_in_a_different_style_is_not_a_fuzzy_heading():
    lines = [
        heading("PROJECTS", 80, size=14), heading("EXPERIENCE", 200, size=14), heading("EDUCATION", 300, size=14),
        mk("Personal Project", 40, 120, 160, size=9, bold=True),  # near-match of "personal projects", wrong style
        body("Built a thing for fun.", 140),
    ]
    secs, _, _ = run(lines)
    assert [n for n, _ in names(secs)] == ["projects", "workHistory", "education"]


def test_resume_without_headings_is_one_header_block():
    secs, labels, doc = run([body(f"Just some text on line {i} of an unstructured resume.", 40 + i * 14) for i in range(6)])
    assert [s.name for s in secs] == ["header"] and len(secs[0].line_ids) == len(doc.pages[0].lines)


def test_plain_document_accepts_multiword_exact_headings_but_not_skill_tags():
    lines = [mk("Summary", 40, 40, 100), body("Accountant with five years of experience in audit and tax work.", 56),
             mk("Education and Training", 40, 80, 200), body("B.Com, University of Mumbai", 96),
             mk("Leadership", 40, 120, 100), mk("Teamwork", 40, 134, 100)]
    secs, _, _ = run(lines)
    assert [n for n, _ in names(secs)] == ["summary", "education"]  # "Leadership" alone is a skill tag


def test_heading_right_after_a_full_width_line_is_not_merged_into_it():
    lines = [mk("Python, SQL, Excel, Tableau, Power BI, communication, presentation, planning, budgeting, auditing", 40, 100, 560),
             mk("Additional Information", 40, 114, 190), body("Valid driving licence.", 130)]
    _, _, doc = run(lines)
    assert "Additional Information" in [l.text for l in doc.pages[0].lines]
