from resume import ParsedResumeData


def test_empty_default_validates():
    data = ParsedResumeData()
    assert data.metaDetails.gender is None
    assert data.workHistory == []
    assert data.model_dump()["metaDetails"]["address"]["city"] == ""


def test_sample_round_trip():
    sample = {
        "summary": "CS student interested in backend systems.",
        "workHistory": [
            {
                "title": "Software Intern",
                "company": "Acme Corp",
                "location": "Pune",
                "type": "internship",
                "period": {"start": "2024-05-01", "end": "2024-07-01", "isCurrent": False},
                "responsibilities": ["Built internal tools"],
                "achievements": ["Cut build time by 30%"],
            }
        ],
        "education": [
            {
                "institution": "VIT Pune",
                "field": {"type": "Bachelor", "course": "Computer Science"},
                "period": {"start": "2022-08-01", "end": None, "isCurrent": True},
                "output": "8.5 CGPA",
            }
        ],
        "skills": [
            {
                "field": "Backend",
                "yearsOfExperience": 1.5,
                "lastUsed": "2024-07-01",
                "tools": [{"name": "Python", "score": 0.9}],
            }
        ],
        "projects": [],
        "certifications": [],
        "languages": [],
        "publications": [],
        "affiliations": [],
        "awards": [],
        "interests": [],
        "metaDetails": {
            "name": "Alex Johnson",
            "phone_no": "+911234567890",
            "gender": None,
            "email": "alex@example.com",
            "github_profile": "https://github.com/alexj",
            "linkedin": None,
            "address": {"city": "Pune", "state": "MH", "country": "India", "postal_code": "411001"},
            "extra_links": [{"name": "Portfolio", "link": "https://alexj.dev"}],
        }
    }

    parsed = ParsedResumeData.model_validate(sample)
    round_tripped = ParsedResumeData.model_validate(parsed.model_dump())

    assert round_tripped == parsed
    assert round_tripped.workHistory[0].type == "internship"
    assert round_tripped.education[0].period.isCurrent is True


def test_invalid_work_type_rejected():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ParsedResumeData.model_validate({"workHistory": [{"type": "ceo"}]})
