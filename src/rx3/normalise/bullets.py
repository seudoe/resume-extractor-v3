"""Bullets: responsibilities vs achievements, project metrics (Stage 11)."""

import re

_NUM = re.compile(r"(?:\d[\d,.]*\s*(?:%|x\b|k\b|m\b|\+|percent|million|billion|crore|lakh|users|customers|clients|requests|ms|hours|days|weeks)|\$\s?\d|₹\s?\d|\b\d{2,}\b)", re.I)
_RANK = re.compile(r"\b(?:ranked?|rank\s*\d+|top\s*\d+|top\s+\d+%|1st|2nd|3rd|first place|second place|third place|winner|won|runner[- ]up|finalist|awarded|recognized|recognised|selected|promoted|employee of the (?:year|month))\b", re.I)
_IMPACT = re.compile(r"\b(?:reduced|increased|improved|boosted|saved|grew|cut|generated|achieved|exceeded|surpassed|accelerated|doubled|tripled)\b[^.]{0,60}?\b(?:by|to|from|over|of)\b", re.I)


def is_achievement(text: str) -> bool:
    """A bullet with a measurable result: a metric, a rank/award wording, or an impact verb with a figure."""
    if _RANK.search(text):
        return True
    return bool(_NUM.search(text) and (_IMPACT.search(text) or "%" in text or re.search(r"\$|₹|\bx\b", text)))


def has_number(text: str) -> bool:
    return bool(re.search(r"\d", text)) and bool(_NUM.search(text))


def split_bullets(bullets: list[str]) -> tuple[list[str], list[str]]:
    """(responsibilities, achievements); achievements keep document order and leave the responsibilities."""
    resp, ach = [], []
    for b in bullets:
        (ach if is_achievement(b) else resp).append(b)
    return resp, ach
