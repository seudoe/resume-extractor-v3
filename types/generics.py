"""Mirrors ifind/types/generics.ts (only the pieces resume.py needs)."""

from pydantic import BaseModel


class DateRange(BaseModel):
    start: str = ""
    end: str | None = None
    isCurrent: bool = False
