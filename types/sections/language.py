"""Mirrors the anonymous `languages[]` entry in ifind/types/resume.ts."""

from pydantic import BaseModel


class Language(BaseModel):
    lang: str = ""
    proficiency: str = ""
    score: str | None = None
