"""Mirrors Publication in ifind/types/resume.ts."""

from typing import Literal

from pydantic import BaseModel

PublicationType = Literal["paper", "article", "talk"]


class Publication(BaseModel):
    title: str = ""
    platform: str = ""
    type: PublicationType = "paper"
    link: str = ""
    keywords: list[str] = []
    date: str = ""
