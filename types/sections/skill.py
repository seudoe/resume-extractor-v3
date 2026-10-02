"""Mirrors Skill in ifind/types/resume.ts."""

from pydantic import BaseModel


class SkillTool(BaseModel):
    name: str = ""
    score: float | None = None


class Skill(BaseModel):
    field: str = ""
    yearsOfExperience: float = 0
    lastUsed: str = ""
    tools: list[SkillTool] = []
