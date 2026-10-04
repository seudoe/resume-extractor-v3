import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from ir import Document  # noqa: E402
from rx3.normalise import normalise, parse_period  # noqa: E402
from rx3.normalise.bullets import is_achievement, split_bullets  # noqa: E402
from rx3.normalise.education import canonical_degree, score_output, split_degree  # noqa: E402
from rx3.normalise.enrich import classify_award_or_cert, work_type  # noqa: E402
from rx3.normalise.skills import build_skills, canonical  # noqa: E402

TODAY = date(2026, 10, 4)
ISO = re.compile(r"^\d{4}-\d{2}-01$")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def p(text, **kw):
    r = parse_period(text, today=TODAY, **kw)
    return r.start, r.end, r.isCurrent


def test_parse_period_formats():
    assert p("Jun 2023 – Present") == ("2023-06-01", None, True)
    assert p("Aug '22 - Dec '22") == ("2022-08-01", "2022-12-01", False)
    assert p("2022-23") == ("2022-01-01", "2023-01-01", False)
    assert p("08/2023 to 05/2024") == ("2023-08-01", "2024-05-01", False)
    assert p("Q3 2023") == ("2023-07-01", None, False)
    assert p("Summer 2024") == ("2024-06-01", None, False)
    assert p("Summer 2024 - Fall 2024") == ("2024-06-01", "2024-09-01", False)
    assert p("2019 – 2023") == ("2019-01-01", "2023-01-01", False)
    assert p("2021") == ("2021-01-01", None, False)  # a lone year is a start for a job
    assert p("2021", lone_is_end=True) == ("", "2021-01-01", False)
    assert p("Expected May 2027") == ("", "2027-05-01", True)  # future end -> still enrolled
    assert p("Expected May 2025") == ("", "2025-05-01", False)
    assert p("") == ("", None, False)


@settings(max_examples=200, deadline=None)
@given(st.text(max_size=60))
def test_parse_period_never_raises_and_never_fabricates(text):
    r = parse_period(text, today=TODAY)
    for v in (r.start, r.end):
        assert v in ("", None) or ISO.match(v)
    if not re.search(r"\d|present|current|now|ongoing|till|today|spring|summer|fall|autumn|winter|expected|pursuing|progress|exp|anticipated", text, re.I):
        assert (r.start, r.end) == ("", None)  # nothing readable -> empty policy, not today's date


@settings(max_examples=200, deadline=None)
@given(st.integers(2000, 2030), st.integers(1, 12), st.integers(0, 40), st.sampled_from(["{m} {y} - {m2} {y2}", "{mm}/{y} to {mm2}/{y2}", "{m} {y} – {m2} {y2}"]))
def test_parse_period_roundtrip_ordered_ranges(y, m, delta, fmt):
    total = y * 12 + (m - 1) + delta
    y2, m2 = divmod(total, 12)
    m2 += 1
    text = fmt.format(m=MONTHS[m - 1], y=y, m2=MONTHS[m2 - 1], y2=y2, mm=f"{m:02d}", mm2=f"{m2:02d}")
    start, end, cur = p(text)
    assert (start, end) == (f"{y:04d}-{m:02d}-01", f"{y2:04d}-{m2:02d}-01") and not cur


def test_degrees_and_scores():
    assert canonical_degree("B.Tech") == "Bachelor of Technology"
    assert canonical_degree("M.S.") == "Master of Science"
    assert canonical_degree("HSC") == "HSC"
    assert split_degree("B.Tech in Information Technology") == ("Bachelor of Technology", "Information Technology")
    assert split_degree("Bachelor of Science", "Physics") == ("Bachelor of Science", "Physics")
    assert score_output("CGPA: 9.875") == "CGPA: 9.875"
    assert score_output("cgpa 8.4 / 10") == "CGPA: 8.4/10"
    assert score_output("Percentage: 92.80%") == "Percentage: 92.80%"
    assert score_output("no score here") == ""


def test_achievements_and_work_type():
    assert is_achievement("Reduced deployment time by 40% using Docker.")
    assert is_achievement("Winner of the national hackathon.")
    assert not is_achievement("Maintained the customer database.")
    r, a = split_bullets(["Maintained the customer database.", "Improved API latency by over 35%."])
    assert r == ["Maintained the customer database."] and a == ["Improved API latency by over 35%."]
    base = {"title": "Software Engineer", "company": "Acme", "type": "job"}
    assert work_type({**base, "title": "Software Engineering Intern"}) == "internship"
    assert work_type({**base, "_heading": "Volunteer Experience"}) == "volunteer"
    assert work_type(base) == "job"


def test_award_vs_certification_rule():
    assert classify_award_or_cert("Winner, SPIT CodeHunt") == "award"
    assert classify_award_or_cert("AWS Certified Cloud Practitioner") == "certification"
    assert classify_award_or_cert("Machine Learning", "Coursera") == "certification"
    assert classify_award_or_cert("Hackathon Winner Certificate") is None  # both signals: stays where it sat


def test_skills_canonical_grouping_and_years():
    assert canonical("js") == ("JavaScript", "Programming Languages")
    assert canonical("postgres") == ("PostgreSQL", "Databases")
    parsed = {
        "skills": [{"field": "", "tools": [{"name": "py"}, {"name": "Docker"}, {"name": "py"}]},
                   {"field": "Languages:", "tools": [{"name": "Hindi"}]}],
        "projects": [{"techStack": ["React", "Node.js"], "title": "T", "description": []}],
        "workHistory": [
            {"title": "Dev", "responsibilities": ["Built services in Python."], "achievements": [],
             "period": {"start": "2020-01-01", "end": "2021-01-01", "isCurrent": False}},
            {"title": "Dev 2", "responsibilities": ["More Python work."], "achievements": [],
             "period": {"start": "2021-01-01", "end": None, "isCurrent": True}},
        ],
    }
    by_field = {s["field"]: s for s in build_skills(parsed)}
    assert [t["name"] for t in by_field["Programming Languages"]["tools"]] == ["Python"]  # py deduped, canonical name
    assert by_field["Programming Languages"]["lastUsed"] == "Present" and by_field["Programming Languages"]["yearsOfExperience"] >= 4.9
    assert by_field["Languages"]["yearsOfExperience"] == 0 and by_field["Languages"]["lastUsed"] == ""  # empty policy
    assert {"React", "Node.js"} <= {t["name"] for s in by_field.values() for t in s["tools"]}


def test_normalise_strips_private_keys_and_reclassifies():
    parsed = {
        "summary": "", "languages": [], "publications": [], "affiliations": [], "interests": [],
        "workHistory": [{"title": "ML Intern", "company": "X", "location": "", "type": "job", "period": {"start": "", "end": None, "isCurrent": False},
                         "responsibilities": ["Cut inference cost by 30%."], "achievements": [], "_lines": ["L1"], "_heading": "Experience"}],
        "education": [{"institution": "IIT", "field": {"type": "B.Tech in CSE", "course": ""}, "period": {"start": "", "end": "2030-05-01", "isCurrent": False}, "output": "cgpa 9.1", "_lines": []}],
        "projects": [], "skills": [],
        "awards": [{"name": "AWS Certified Developer", "issuingBody": "Amazon", "date": "2024", "justification": ""}],
        "certifications": [{"name": "Winner, Smart India Hackathon", "issuer": "", "skillsEarned": [], "type": "", "date": "2023"}],
    }
    n = normalise(parsed, Document(), today=TODAY)
    assert n["workHistory"][0]["type"] == "internship" and n["workHistory"][0]["achievements"] == ["Cut inference cost by 30%."]
    assert n["education"][0]["field"] == {"type": "Bachelor of Technology", "course": "CSE"} and n["education"][0]["period"]["isCurrent"]
    assert [a["name"] for a in n["awards"]] == ["Winner, Smart India Hackathon"]
    assert [c["name"] for c in n["certifications"]] == ["AWS Certified Developer"]
    assert "_lines" not in str(n) and "_heading" not in str(n)
