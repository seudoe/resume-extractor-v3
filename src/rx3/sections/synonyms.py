"""Heading synonym table -> canonical sections (PROMPT.md §5 Stage 9).

Canonical sections follow the schema: summary, workHistory, education, skills,
projects, certifications, languages, publications, affiliations, awards,
interests, other. Built from the headings actually seen in the 32 gold
resumes plus the 24-resume LiveCareer sample (Highlights, Accomplishments,
Executive Profile, Professional Affiliations, Additional Information ...) plus
the usual resume vocabulary. Extend by appending; nothing here is a model.
"""

import re

from rapidfuzz import fuzz, process

SYNONYMS: dict[str, list[str]] = {
    "summary": [
        "summary", "professional summary", "career summary", "executive summary", "summary of qualifications",
        "qualifications summary", "profile", "professional profile", "executive profile", "personal profile",
        "about me", "about", "objective", "career objective", "career goal", "career focus", "professional objective",
        "personal statement", "introduction", "bio", "professional overview", "career overview", "summary of skills",
    ],
    "workHistory": [
        "experience", "work experience", "professional experience", "work history", "employment history",
        "employment", "career history", "relevant experience", "relevant work experience", "internships",
        "internship", "internship experience", "industry experience", "professional background", "experience summary",
        "positions held", "previous experience", "work experience and internships", "professional history",
        "employment experience", "experience and internships",
    ],
    "education": [
        "education", "academic background", "academic qualifications", "educational qualifications", "academics",
        "education and training", "educational background", "academic details", "education details", "degrees",
        "scholastic record", "academic record", "academic profile", "relevant coursework", "coursework", "relevant courses",
    ],
    "skills": [
        "skills", "technical skills", "key skills", "core skills", "core competencies", "competencies", "skills summary",
        "areas of expertise", "expertise", "technologies", "tech stack", "technical expertise", "tools and technologies",
        "skills and tools", "skills and abilities", "hard skills", "soft skills", "highlights", "skill set",
        "proficiencies", "qualifications", "technical proficiency", "technical summary", "skills and technologies", "strengths", "key strengths", "core strengths", "programming", "technical competencies", "core qualifications", "skill highlights", "professional highlights", "career highlights", "summary of skills", "special skills",
    ],
    "projects": [
        "projects", "academic projects", "personal projects", "key projects", "selected projects", "project experience",
        "side projects", "notable projects", "technical projects", "open source", "open source contributions",
        "projects and research", "major projects", "course projects", "project work",
    ],
    "certifications": [
        "certifications", "certification", "certificates", "licenses", "licenses and certifications", "certifications and courses",
        "courses", "online courses", "training", "trainings", "professional development", "courses and certifications",
        "training and certifications", "certificates and awards", "certifications and licenses", "certifications and training",
        "licenses and certificates", "professional certifications",
    ],
    "languages": ["languages", "language skills", "spoken languages", "linguistic skills", "language proficiency"],
    "publications": [
        "publications", "publication", "research", "research papers", "papers", "patents", "talks", "presentations",
        "conference papers", "research publications", "research and publications", "talks and presentations",
    ],
    "affiliations": [
        "affiliations", "professional affiliations", "memberships", "professional memberships", "positions of responsibility",
        "por", "leadership", "leadership experience", "leadership and activities", "extracurricular", "extra curricular",
        "extracurricular activities", "extra curricular activities", "activities", "volunteer", "volunteering",
        "volunteer experience", "volunteer work", "volunteering activities", "volunteer activities", "community involvement", "social work", "organizations", "clubs",
        "committees", "co curricular activities", "leadership and volunteer work", "leadership volunteer work",
        "leadership and involvement", "club activities", "positions of responsibility and activities",
    ],
    "awards": [
        "awards", "honors", "honours", "honors and awards", "honours and awards", "awards and achievements", "achievements",
        "accomplishments", "awards and honors", "scholarships", "recognition", "competitions", "hackathons",
        "awards and recognition", "achievements and awards", "hackathons and competitions", "standout awards", "most proud of",
        "accolades", "core accomplishments", "activities and honors", "honors and activities", "activities and awards", "achievements and honors",
    ],
    "interests": [
        "interests", "hobbies", "hobbies and interests", "personal interests", "interests and hobbies",
        "activities and interests", "hobbies and activities",
    ],
    "other": [
        "additional information", "additional details", "additional", "personal details", "personal information",
        "personal", "references", "declaration", "contact", "contact me", "contact information", "contact details",
        "contact info", "get in touch", "miscellaneous", "other", "others", "extras", "other information",
        "other details", "other activities", "more about me", "social media", ],
}


def normalize(text: str) -> str:
    """Lowercase letters/spaces only, '&' read as 'and' ("Awards & Honors" ==
    "awards and honors"), trailing 'section' dropped."""
    t = text.lower().replace("&", " and ").replace("/", " ")
    t = re.sub(r"[^a-z ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"\s+section$", "", t)


_LOOKUP = {normalize(p): canon for canon, phrases in SYNONYMS.items() for p in phrases}
_NOSPACE = {k.replace(" ", ""): v for k, v in _LOOKUP.items()}  # "CON TACT" from small-caps/OCR gaps
_CHOICES = list(_LOOKUP)

MAX_HEADING_WORDS = 6


def match_heading(text: str, cutoff: float = 88.0) -> tuple[str, float] | None:
    """(canonical section, score 0-100) if `text` reads as a section heading,
    else None. Exact normalised match scores 100; otherwise token-sort fuzzy
    match above `cutoff` (typos/plurals: "Certification", "Skill set")."""
    n = normalize(text)
    if not n or len(n.split()) > MAX_HEADING_WORDS:
        return None
    if n in _LOOKUP:
        return _LOOKUP[n], 100.0
    if n.replace(" ", "") in _NOSPACE:
        return _NOSPACE[n.replace(" ", "")], 100.0
    hit = process.extractOne(n, _CHOICES, scorer=fuzz.token_sort_ratio, score_cutoff=cutoff)
    # Capped below 100: only an exact normalised match is 'exact' (token-sort
    # also scores reordered words 100: 'Development Professional' vs the
    # 'professional development' heading).
    return (_LOOKUP[hit[0]], min(float(hit[1]), 99.0)) if hit else None


# Words that, inside a heading we already know *is* a heading by its style
# ("Volunteering Activities", "University Project", "Teaching Experience"),
# say which section it opens. Only used for style-detected headings: as a
# standalone matcher these single words would misfire on ordinary lines.
_KEYWORDS = {
    "education": "education", "academic": "education", "experience": "workHistory", "internship": "workHistory",
    "internships": "workHistory", "employment": "workHistory", "project": "projects", "projects": "projects",
    "skill": "skills", "skills": "skills", "certification": "certifications", "certifications": "certifications",
    "certificate": "certifications", "certificates": "certifications", "course": "certifications",
    "courses": "certifications", "training": "certifications", "award": "awards", "awards": "awards",
    "achievement": "awards", "achievements": "awards", "honors": "awards", "honours": "awards",
    "accomplishments": "awards", "volunteer": "affiliations", "volunteering": "affiliations",
    "activities": "affiliations", "extracurricular": "affiliations", "leadership": "affiliations",
    "membership": "affiliations", "memberships": "affiliations", "affiliations": "affiliations",
    "language": "languages", "languages": "languages", "interest": "interests", "interests": "interests",
    "hobbies": "interests", "publication": "publications", "publications": "publications", "papers": "publications",
    "summary": "summary", "objective": "summary",
}


# Keywords that are nearly always a *section name* when they appear in a short
# title-case line. The rest of _KEYWORDS (leadership, project, volunteer,
# activities, research, training...) are also skill tags in plain documents
# ("Project Management", "Leadership"), so they're only trusted when layout
# already says "heading".
_STRICT = {
    "skill", "skills", "education", "experience", "certification", "certifications", "award", "awards", "achievement",
    "achievements", "accomplishments", "honors", "honours", "publications", "summary", "objective", "affiliations",
    "interests", "hobbies", "memberships",
}
# One-word synonyms that double as skill tags / sub-labels in plain documents.
AMBIGUOUS_ONE_WORD = {
    "leadership", "research", "volunteer", "volunteering", "activities", "training", "courses", "clubs",
    "organizations", "recognition", "competitions", "hackathons", "programming", "strengths", "expertise",
    "technologies", "language", "other",
}


def keyword_section(text: str, strict: bool = False) -> str | None:
    for token in reversed(normalize(text).split()):  # last keyword wins: 'Summary of Skills' -> skills
        if token in _KEYWORDS and (not strict or token in _STRICT):
            return _KEYWORDS[token]
    return None
