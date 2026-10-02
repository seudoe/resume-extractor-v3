"""Mirrors Award in ifind/types/resume.ts."""

from pydantic import BaseModel


class Award(BaseModel):
    name: str = ""
    issuingBody: str = ""
    date: str = ""
    justification: str = ""
