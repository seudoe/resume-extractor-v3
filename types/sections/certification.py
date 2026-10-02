"""Mirrors the anonymous `certifications[]` entry in ifind/types/resume.ts."""

from pydantic import BaseModel


class Certification(BaseModel):
    name: str = ""
    issuer: str = ""
    skillsEarned: list[str] = []
    type: str = ""
    date: str = ""
