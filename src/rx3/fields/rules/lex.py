"""Title / company word tests shared by entry splitting and field roles."""

import re

from rx3.fields.rules._title_words import TITLE_HEADS

TITLE_WORDS = TITLE_HEADS | {
    "intern", "trainee", "freelancer", "founder", "cofounder", "scientist", "researcher", "lead", "head", "officer",
    "specialist", "programmer", "tester", "consultant", "member", "volunteer", "fellow", "engineer", "developer",
    "manager", "analyst", "director", "president", "secretary", "coordinator", "executive", "designer", "mentor",
    "captain", "representative", "supervisor", "technician", "teacher", "professor", "lecturer", "instructor",
}
_COMPANY_WORDS = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|company|co|technologies|technology|solutions|labs|systems|group|pvt|"
    r"private|bank|services|consulting|university|institute|college|school|foundation|club|society|association|"
    r"software|studio|studios|industries|enterprises|partners|agency|hospital|center|centre)\b\.?", re.I)


def is_title(s: str) -> bool:
    toks = re.findall(r"[a-z]+", s.lower())
    return bool(toks) and (toks[-1] in TITLE_WORDS or any(t in TITLE_WORDS for t in toks[:3])) and len(s) <= 70


def is_company(s: str) -> bool:
    return bool(_COMPANY_WORDS.search(s))
