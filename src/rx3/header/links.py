"""Profile and extra links (PROMPT.md §5 Stage 8): link annotations first (they
carry the real URL even when the visible text is an icon or just a handle),
then URL regex over text, then explicit "github: handle" labels."""

import re
from urllib.parse import urlparse

from ir import Document, Line, Provenance

from rx3.header.zone import EMAIL_RE, contact_text, has_contact_data

# host suffix -> display name, for profiles that go in extra_links
PLATFORMS = {
    "leetcode.com": "LeetCode", "codeforces.com": "Codeforces", "codechef.com": "CodeChef",
    "kaggle.com": "Kaggle", "hackerrank.com": "HackerRank", "geeksforgeeks.org": "GeeksforGeeks",
    "twitter.com": "Twitter", "x.com": "Twitter", "medium.com": "Medium", "behance.net": "Behance",
    "dribbble.com": "Dribbble", "stackoverflow.com": "StackOverflow", "gitlab.com": "GitLab",
    "orcid.org": "ORCID", "scholar.google.com": "Google Scholar", "hackerearth.com": "HackerEarth",
}
_BARE_DOMAINS = (
    r"(?:linkedin|github|leetcode|codeforces|codechef|kaggle|hackerrank|geeksforgeeks|medium|behance|dribbble|gitlab)"
    r"\.(?:com|org|net)|[a-z0-9\-]{3,}\.(?:dev|io|me|app)"
)
URL_RE = re.compile(
    rf"(?i)(?:https?://|www\.)[^\s|,;<>()\"'\u2022]+|\b(?:{_BARE_DOMAINS})(?:/[^\s|,;<>()\"'\u2022]*)?"
)
LABELLED_RE = re.compile(r"(?i)\b(linkedin|github)\s*:\s*(?!https?\b|www\b)([A-Za-z0-9._\-]+)(?![:/A-Za-z0-9._\-])")


def _clean(url: str) -> str:
    url = url.rstrip(".,;:)")
    return url if re.match(r"(?i)https?://", url) else "https://" + url


def _host_path(url: str) -> tuple[str, list[str]]:
    try:
        p = urlparse(url)
    except ValueError:  # malformed annotation target
        return "", []
    host = p.netloc.lower().removeprefix("www.")
    return host, [s for s in p.path.split("/") if s]


def classify(url: str) -> tuple[str, str]:
    """-> (kind, display name). kind: linkedin | github_profile | github_repo |
    platform | other | skip."""
    host, parts = _host_path(url)
    if host.endswith("linkedin.com"):
        return ("linkedin", "LinkedIn") if parts[:1] in (["in"], ["pub"]) else ("skip", "")
    if host == "github.com":
        return ("github_profile", "GitHub") if len(parts) == 1 else ("github_repo", "GitHub")
    for suffix, name in PLATFORMS.items():
        if host == suffix or host.endswith("." + suffix):
            return "platform", name
    if host.endswith(("netlify.app", "vercel.app", "herokuapp.com", "onrender.com", "streamlit.app")):
        return "other", ""  # deployed project, not a personal site
    return "other", ""


def norm_url(url: str) -> str:
    host, parts = _host_path(_clean(url))
    return host + "/" + "/".join(parts)


def _in_zone(line: Line | None, zone_ids: set[str]) -> bool:
    return line is not None and line.id in zone_ids


def _line_at(doc: Document, page_idx: int, bbox) -> Line | None:
    """Line whose box overlaps the link rect most."""
    best, best_overlap = None, 0.0
    for line in doc.pages[page_idx].lines:
        ox = min(line.bbox.x1, bbox.x1) - max(line.bbox.x0, bbox.x0)
        oy = min(line.bbox.y1, bbox.y1) - max(line.bbox.y0, bbox.y0)
        if ox > 0 and oy > 0 and ox * oy > best_overlap:
            best, best_overlap = line, ox * oy
    return best


def extract_links(doc: Document, header_ids: set[str]) -> dict:
    """Returns {"linkedin", "github", "extra_links", "provenance"}. Only links
    on page 1 in the header zone or on a contact line qualify — a github.com/
    user/repo link under Projects is a project link, not the candidate's."""
    candidates: list[tuple[str, Line | None, str]] = []  # (url, line, how)
    for page_idx, page in enumerate(doc.pages):
        for link in page.links:
            if not link.uri.lower().startswith(("mailto:", "tel:")):
                candidates.append((_clean(link.uri), _line_at(doc, page_idx, link.bbox), "annotation"))
        for line in page.lines:
            text = EMAIL_RE.sub(" ", contact_text(line))
            for m in URL_RE.finditer(text):
                candidates.append((_clean(m.group(0)), line, "text"))

    contact_ys = [
        (l.bbox.y0 + l.bbox.y1) / 2 for l in (doc.pages[0].lines if doc.pages else []) if has_contact_data(l)
    ]

    def qualifies(line: Line | None) -> bool:
        if line is None:
            return False
        if line.id in header_ids:
            return True
        if line.page != 0:
            return False
        cy, h = (line.bbox.y0 + line.bbox.y1) / 2, line.bbox.y1 - line.bbox.y0
        return any(abs(cy - y) <= 1.5 * h for y in contact_ys)

    out = {"linkedin": None, "github": None, "extra_links": [], "provenance": {}}
    seen: set[str] = set()
    for url, line, how in candidates:
        key = norm_url(url)
        if key in seen:
            continue
        kind, name = classify(url)
        # Coding-platform profiles (codeforces.com/profile/x ...) are always
        # the candidate's own, wherever they sit; everything else must be in
        # the header zone — a github.com/user/repo or a deployed demo under
        # Projects is not a profile link.
        if kind != "platform" and not qualifies(line):
            continue
        prov = Provenance(line_ids=[line.id] if line else [], component=f"header.links.{how}")
        if kind == "linkedin" and out["linkedin"] is None:
            out["linkedin"], out["provenance"]["linkedin"] = url, prov
        elif kind == "github_profile" and out["github"] is None:
            out["github"], out["provenance"]["github"] = url, prov
        elif kind in ("platform", "other"):
            out["extra_links"].append({"name": name or "Portfolio", "link": url})
        else:
            continue
        seen.add(key)

    # "linkedin: handle" / "github: handle" labels (icon fonts whose ToUnicode
    # map spells the platform out). The handle is kept as written — no URL is
    # invented — and only fills a field the annotations left empty.
    for line in (doc.pages[0].lines if doc.pages else []):
        if not qualifies(line):
            continue
        for m in LABELLED_RE.finditer(contact_text(line)):
            field = "linkedin" if m.group(1).lower() == "linkedin" else "github"
            if out[field] is None:
                out[field] = m.group(2)
                out["provenance"][field] = Provenance(line_ids=[line.id], component="header.links.label")
    return out
