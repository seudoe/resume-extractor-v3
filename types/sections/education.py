"""Mirrors ResumeEducation in ifind/types/resume.ts."""

from pydantic import BaseModel

from generics import DateRange


class EducationField(BaseModel):
    type: str = ""
    course: str = ""


class ResumeEducation(BaseModel):
    institution: str = ""
    field: EducationField = EducationField()
    period: DateRange = DateRange()
    output: str = ""
