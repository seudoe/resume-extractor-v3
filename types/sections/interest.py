"""Mirrors the anonymous `interests[]` entry in ifind/types/resume.ts."""

from pydantic import BaseModel


class Interest(BaseModel):
    activity: str = ""
    description: str = ""
    commitmentMetric: str | None = None
