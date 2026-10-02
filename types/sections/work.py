"""Mirrors WorkHistory in ifind/types/resume.ts."""

from typing import Literal

from pydantic import BaseModel

from generics import DateRange

WorkType = Literal["job", "internship", "volunteer", "co-op"]


class WorkHistory(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    type: WorkType = "job"
    period: DateRange = DateRange()
    responsibilities: list[str] = []
    achievements: list[str] = []
