"""Education normalisation: degree abbreviations, course split, CGPA/percentage (Stage 11)."""

import re

# (canonical name, pattern matched against the whole degree text, case-insensitive)
_DEGREES = [
    ("Bachelor of Technology", r"b\.?\s?tech\.?|bachelors?'?s?\s+(?:of|in)\s+technology"),
    ("Master of Technology", r"m\.?\s?tech\.?|masters?'?s?\s+(?:of|in)\s+technology"),
    ("Bachelor of Engineering", r"b\.?\s?e\.?|bachelors?'?s?\s+(?:of|in)\s+engineering"),
    ("Master of Engineering", r"m\.?\s?e\.?|masters?'?s?\s+(?:of|in)\s+engineering"),
    ("Bachelor of Science", r"b\.?\s?sc?\.?|bachelors?'?s?\s+(?:of|in)\s+science"),
    ("Master of Science", r"m\.?\s?sc?\.?|masters?'?s?\s+(?:of|in)\s+science"),
    ("Bachelor of Arts", r"b\.?\s?a\.?|bachelors?'?s?\s+(?:of|in)\s+arts"),
    ("Master of Arts", r"m\.?\s?a\.?|masters?'?s?\s+(?:of|in)\s+arts"),
    ("Bachelor of Commerce", r"b\.?\s?com\.?|bachelors?'?s?\s+(?:of|in)\s+commerce"),
    ("Master of Commerce", r"m\.?\s?com\.?|masters?'?s?\s+(?:of|in)\s+commerce"),
    ("Bachelor of Business Administration", r"bba|b\.?\s?b\.?\s?a\.?|bachelors?'?s?\s+(?:of|in)\s+business\s+administration"),
    ("Master of Business Administration", r"mba|m\.?\s?b\.?\s?a\.?|masters?'?s?\s+(?:of|in)\s+business\s+administration"),
    ("Bachelor of Computer Applications", r"bca|bachelors?'?s?\s+(?:of|in)\s+computer\s+applications?"),
    ("Master of Computer Applications", r"mca|masters?'?s?\s+(?:of|in)\s+computer\s+applications?"),
    ("Doctor of Philosophy", r"ph\.?\s?d\.?|doctorate|doctor\s+of\s+philosophy"),
    ("Associate Degree", r"associates?'?s?(?:\s+degree)?|a\.?a\.?s?\.?"),
    ("Bachelor's Degree", r"bachelors?'?s?(?:\s+degree)?"),
    ("Master's Degree", r"masters?'?s?(?:\s+degree)?"),
    ("Diploma", r"diploma|polytechnic"),
    ("HSC", r"hsc|12th|xii|higher\s+secondary(?:\s+certificate)?|intermediate|senior\s+secondary|a[- ]levels?"),
    ("SSC", r"ssc|10th|x|secondary(?:\s+school\s+certificate)?|matriculation|o[- ]levels?|high\s+school(?:\s+diploma)?"),
]
_COMPILED = [(name, re.compile(rf"^(?:{pat})$", re.I)) for name, pat in _DEGREES]
_SPLIT = re.compile(r"\s+in\s+|\s*[:,(]\s*|\s+[-–—]\s+", re.I)
_SCORE = re.compile(r"\b(cgpa|gpa|percentage|percent|marks|grade|aggregate)\b\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(%|/\s*\d+(?:\.\d+)?|out of \d+(?:\.\d+)?)?", re.I)
_BARE_PCT = re.compile(r"\b(\d{2,3}(?:\.\d+)?)\s*%")


def canonical_degree(text: str) -> str:
    """Canonical degree name, or the cleaned input when unknown. 'B.Tech' / 'BTech' -> 'Bachelor of Technology'."""
    t = re.sub(r"\s+", " ", text or "").strip(" .,;:()")
    for name, rx in _COMPILED:
        if rx.match(t):
            return name
    return t


def split_degree(type_text: str, course_text: str = "") -> tuple[str, str]:
    """('B.Tech in IT', '') -> ('Bachelor of Technology', 'IT'); keeps an existing course."""
    t = re.sub(r"\s+", " ", type_text or "").strip()
    c = (course_text or "").strip()
    if t and not c:
        m = _SPLIT.search(t)
        if m and canonical_degree(t[: m.start()]) != t[: m.start()].strip(" .,;:()"):
            t, c = t[: m.start()], t[m.end() :].strip(" .,;:()")
    return canonical_degree(t), c


def score_output(text: str) -> str:
    """'cgpa 9.875 /10' -> 'CGPA: 9.875/10'; '92.8%' -> 'Percentage: 92.8%'. A scale is only added when the
    text states one; nothing is inferred. Returns '' if no score is present."""
    m = _SCORE.search(text or "")
    if m:
        label = m.group(1).upper() if m.group(1).lower() in ("cgpa", "gpa") else {"percent": "Percentage", "marks": "Marks"}.get(m.group(1).lower(), m.group(1).title())
        scale = re.sub(r"\s+|out of ", lambda s: "/" if s.group(0).startswith("out") else "", m.group(3) or "")
        return f"{label}: {m.group(2)}{scale}"
    m = _BARE_PCT.search(text or "")
    return f"Percentage: {m.group(1)}%" if m else ""


def normalise_education(e: dict) -> dict:
    t, c = split_degree(e["field"]["type"], e["field"]["course"])
    out = e["output"]
    return {**e, "field": {"type": t, "course": c}, "output": score_output(out) or out}
