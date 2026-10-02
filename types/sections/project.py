"""Mirrors Project in ifind/types/resume.ts."""

from pydantic import BaseModel


class ProjectLinks(BaseModel):
    repo: str = ""
    live: str | None = None
    demo: str | None = None


class Project(BaseModel):
    title: str = ""
    role: str = ""
    links: ProjectLinks = ProjectLinks()
    techStack: list[str] = []
    problemStatement: str | None = None
    metrics: list[str] = []
    technicalChallenges: list[str] = []
    description: list[str] = []
    architecture: str = ""
