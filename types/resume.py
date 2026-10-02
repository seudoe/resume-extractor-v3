"""Pydantic v2 mirror of ifind/types/resume.ts — the output contract.

Field names, nesting and optionality must match the TS source of truth
exactly. Empty-value policy (see DECISIONS.md Stage 2): required strings
default to `""`, fields typed `X | null` in TS default to `None`, arrays
default to `[]`. This matches how `ifind/lib/resumeParser.ts`
(`normaliseHFOutput`) already builds `metaDetails`.
"""

from pydantic import BaseModel

from sections.affiliation import Affiliation
from sections.award import Award
from sections.certification import Certification
from sections.education import ResumeEducation
from sections.interest import Interest
from sections.language import Language
from sections.meta import ResumeMetaDetails
from sections.project import Project
from sections.publication import Publication
from sections.skill import Skill
from sections.work import WorkHistory

__all__ = [
    "Affiliation",
    "Award",
    "Certification",
    "Interest",
    "Language",
    "ParsedResumeData",
    "Project",
    "Publication",
    "ResumeEducation",
    "ResumeMetaDetails",
    "Skill",
    "WorkHistory",
]


class ParsedResumeData(BaseModel):
    summary: str = ""
    workHistory: list[WorkHistory] = []
    education: list[ResumeEducation] = []
    skills: list[Skill] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
    languages: list[Language] = []
    publications: list[Publication] = []
    affiliations: list[Affiliation] = []
    awards: list[Award] = []
    interests: list[Interest] = []
    metaDetails: ResumeMetaDetails = ResumeMetaDetails()
