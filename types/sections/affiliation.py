"""Mirrors Affiliation in ifind/types/resume.ts."""

from pydantic import BaseModel

from generics import DateRange


class Affiliation(BaseModel):
    organization: str = ""
    role: str = ""
    type: str = ""
    impact: list[str] = []
    period: DateRange = DateRange()
