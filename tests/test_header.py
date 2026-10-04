import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir import BBox, Document, Line, Link, Page, Span  # noqa: E402
from rx3.header import extract_header  # noqa: E402
from rx3.layout import analyze_layout  # noqa: E402


def mk(text, x0, y0, x1, y1=None, size=10.0, bold=False, page=0):
    y1 = y1 if y1 is not None else y0 + size * 1.2
    bb = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
    return Line(id="X", page=page, bbox=bb, text=text, spans=[Span(text=text, bbox=bb, size=size, bold=bold)])


def lnk(uri, x0, y0, x1, y1):
    return Link(bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1), uri=uri)


def header(lines, links=(), filename="", page2=None):
    pages = [Page(number=0, width=600, height=800, lines=list(lines), links=list(links))]
    if page2:
        pages.append(Page(number=1, width=600, height=800, lines=page2[0], links=page2[1]))
    return extract_header(analyze_layout(Document(pages=pages)), filename).meta


BODY = [mk(f"Built things number {i} for the team.", 40, 300 + i * 14, 400) for i in range(5)]


def test_name_is_biggest_line_not_the_job_title():
    meta = header([mk("Jane Doe", 200, 30, 400, size=26, bold=True), mk("Senior Software Engineer", 200, 62, 400, size=14)] + BODY)
    assert meta["name"] == "Jane Doe"


def test_name_small_caps_gap_is_fixed_and_two_line_name_joined():
    meta = header([mk("M ohd Asif", 100, 30, 400, size=30, bold=True), mk("Shershahvadi", 100, 64, 400, size=30, bold=True)] + BODY)
    assert meta["name"] == "Mohd Asif Shershahvadi"


def test_filename_breaks_a_tie_between_equal_candidates():
    lines = [mk("Alice Smith", 40, 30, 200, size=20), mk("Robert Brown", 300, 30, 460, size=20)] + BODY
    assert header(lines, filename="RobertBrown_Resume.pdf")["name"] == "Robert Brown"


def test_visible_email_beats_stale_mailto_but_mailto_is_fallback():
    top = mk("Jane Doe", 40, 30, 200, size=24, bold=True)
    contact = mk("me@jane.dev | +91 98765 43210", 40, 62, 300)
    meta = header([top, contact] + BODY, links=[lnk("mailto:someone.else@x.com", 40, 62, 120, 74)])
    assert meta["email"] == "me@jane.dev"
    meta = header([top, mk("Contact via the icon", 40, 62, 300)] + BODY, links=[lnk("mailto:only@link.com", 40, 62, 120, 74)])
    assert meta["email"] == "only@link.com"


def test_phone_is_e164_and_date_ranges_are_not_phones():
    meta = header([mk("Jane Doe", 40, 30, 200, size=24, bold=True), mk("2017 - 2021 | 8779635900", 40, 62, 300)] + BODY)
    assert meta["phone_no"] == "+918779635900"
    assert header([mk("Jane Doe", 40, 30, 200, size=24, bold=True), mk("B.Tech 2024 - 2028 | 2019 - 2023", 40, 62, 300)] + BODY)["phone_no"] == ""


def test_links_annotations_classify_profile_vs_repo_vs_post():
    top = mk("Jane Doe", 40, 30, 200, size=24, bold=True)
    row = mk("jane@x.com | LinkedIn | GitHub | Portfolio", 40, 62, 400)
    links = [
        lnk("https://www.linkedin.com/in/jane-doe/", 150, 62, 200, 74),
        lnk("https://github.com/janedoe", 210, 62, 250, 74),
        lnk("https://janedoe.dev", 260, 62, 320, 74),
        lnk("https://github.com/janedoe/some-repo", 40, 300, 100, 312),
        lnk("https://www.linkedin.com/posts/x_activity-1", 40, 314, 100, 326),
    ]
    meta = header([top, row] + BODY, links=links)
    assert meta["linkedin"] == "https://www.linkedin.com/in/jane-doe/"
    assert meta["github_profile"] == "https://github.com/janedoe"
    assert [e["link"] for e in meta["extra_links"]] == ["https://janedoe.dev"]  # repo + post are not profile links


def test_coding_profiles_count_from_anywhere_but_demos_in_body_do_not():
    top = mk("Jane Doe", 40, 30, 200, size=24, bold=True)
    contact = mk("jane@x.com", 40, 62, 200)
    body = BODY + [mk("Achievement lines", 40, 500, 300)]
    page2 = ([mk("Awards", 40, 40, 200), mk("Specialist on Codeforces", 40, 60, 300)],
             [lnk("https://codeforces.com/profile/jane", 40, 60, 300, 72), lnk("https://demo.netlify.app", 40, 80, 100, 90)])
    meta = header([top, contact] + body, page2=page2)
    assert [e["link"] for e in meta["extra_links"]] == ["https://codeforces.com/profile/jane"]
    assert meta["extra_links"][0]["name"] == "Codeforces"


def test_btech_is_not_a_domain_and_labelled_handles_are_kept_as_written():
    top = mk("Jane Doe", 40, 30, 200, size=24, bold=True)
    meta = header([top, mk("B.Tech | github : https://github.com/janedoe/proj | jane@x.com", 40, 62, 400)] + BODY)
    assert meta["github_profile"] is None and meta["extra_links"] == []
    meta = header([top, mk("jane@x.com | github: janedoe | linkedin: jane-doe", 40, 62, 400)] + BODY)
    assert (meta["github_profile"], meta["linkedin"]) == ("janedoe", "jane-doe")  # no URL invented


def test_location_general_city_nothing_inferred_and_pin_and_us_state():
    top = mk("Jane Doe", 40, 30, 200, size=24, bold=True)
    a = header([top, mk("Andheri, Mumbai, Maharashtra - 400058 | jane@x.com", 40, 62, 400)] + BODY)["address"]
    assert (a["city"], a["state"], a["country"], a["postal_code"]) == ("Mumbai", "Maharashtra", "", "400058")
    b = header([top, mk("Atlanta, GA | jane@x.com", 40, 62, 300)] + BODY)["address"]
    assert (b["city"], b["state"]) == ("Atlanta", "GA")
    c = header([top, mk("jane@x.com", 40, 62, 200), mk("EDUCATION", 40, 90, 200, bold=True), mk("University of Mumbai", 40, 110, 300)] + BODY)["address"]
    assert c["city"] == ""  # a college in the education section is not the candidate's city


def test_gender_is_never_inferred():
    assert header([mk("Priya Sharma", 40, 30, 300, size=24, bold=True), mk("Female | priya@x.com", 40, 62, 300)] + BODY)["gender"] is None
