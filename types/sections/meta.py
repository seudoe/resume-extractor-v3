"""Mirrors ResumeMetaDetails in ifind/types/resume.ts.

Privacy: `gender` must stay None unless the resume states it explicitly
(PROMPT.md §1.7) — never infer it.
"""

from typing import Literal

from pydantic import BaseModel

Gender = Literal["Male", "Female", "Other", "Prefer Not to Say"]


class Address(BaseModel):
    city: str = ""
    state: str | None = None
    country: str = ""
    postal_code: str | None = None


class ExtraLink(BaseModel):
    name: str = ""
    link: str = ""


class ResumeMetaDetails(BaseModel):
    name: str = ""
    phone_no: str = ""
    gender: Gender | None = None
    email: str = ""
    github_profile: str | None = None
    linkedin: str | None = None
    address: Address = Address()
    extra_links: list[ExtraLink] = []
