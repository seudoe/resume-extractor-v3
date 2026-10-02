import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from matching import match_entities  # noqa: E402
from metrics import (  # noqa: E402
    hallucination_rate,
    score_entity_section,
    score_scalar_fields,
    skills_prf1,
    token_f1,
)


def test_match_entities_aligns_by_similarity():
    predicted = [{"title": "Acme Corp"}, {"title": "Totally Different"}]
    gold = [{"title": "Acme Corporation"}]
    matched, unmatched_p, unmatched_g = match_entities(predicted, gold, lambda e: e["title"])
    assert matched == [(0, 0)]
    assert unmatched_p == [1]
    assert unmatched_g == []


def test_score_scalar_fields_marks_missing_gold_not_applicable():
    gold = {"metaDetails": {"name": "Alex", "email": "", "phone_no": "", "linkedin": None, "github_profile": None}}
    pred = {"metaDetails": {"name": "Alex", "email": "x@y.com", "phone_no": "", "linkedin": None, "github_profile": None}}
    result = score_scalar_fields(pred, gold)
    assert result["metaDetails.name"] == {"applicable": True, "correct": True}
    assert result["metaDetails.email"]["applicable"] is False


def test_score_entity_section_perfect_match():
    entry = {"company": "Acme", "title": "Engineer", "location": "NY", "type": "job",
              "period": {"start": "2020-01-01", "end": "2021-01-01", "isCurrent": False}}
    result = score_entity_section([entry], [entry], "workHistory")
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["subfield_accuracy"]["company"] == 1.0


def test_score_entity_section_empty_gold_is_not_a_crash():
    result = score_entity_section([{"company": "Acme", "title": "X"}], [], "workHistory")
    assert result["n_gold"] == 0
    assert result["omission_rate"] == 0.0


def test_token_f1_identical_lists():
    assert token_f1(["Built an app"], ["Built an app"]) == 1.0


def test_token_f1_disjoint_lists():
    assert token_f1(["abc def"], ["xyz uvw"]) == 0.0


def test_skills_prf1_both_empty_is_perfect():
    result = skills_prf1({"skills": []}, {"skills": []})
    assert result == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_hallucination_rate_catches_invented_strings():
    source = "Sambhav Mirajgaonkar worked on a URL Shortener project."
    predicted = {"workHistory": [{"title": "Invented Title Not In Source"}]}
    result = hallucination_rate(predicted, source)
    assert result["n_hallucinated"] == 1
    assert result["rate"] == 1.0


def test_hallucination_rate_no_false_positive_on_grounded_string():
    source = "Sambhav Mirajgaonkar worked on a URL Shortener project."
    predicted = {"projects": [{"title": "URL Shortener"}]}
    result = hallucination_rate(predicted, source)
    assert result["n_hallucinated"] == 0
