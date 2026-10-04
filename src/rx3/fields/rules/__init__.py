"""Rules baseline (Stage 10.2 #1): Document -> ParsedResumeData-shaped dict."""

from ir import Document

from rx3.fields.rules.build import build_section
from rx3.header import extract_header
from rx3.sections.segment import segment_sections

LIST_SECTIONS = ["workHistory", "education", "skills", "projects", "certifications", "languages",
                 "publications", "affiliations", "awards", "interests"]


def extract_rules(doc: Document, filename: str = "") -> dict:
    """`doc` must already be through `analyze_layout`."""
    by_id = {l.id: l for p in doc.pages for l in p.lines}
    out: dict = {"summary": "", **{k: [] for k in LIST_SECTIONS}}
    for s in segment_sections(doc):
        if s.name in ("header", "other"):
            continue
        lines = [by_id[i] for i in s.line_ids]
        if s.inline and s.heading:  # "Languages<tab>English, Hindi": drop the label itself
            lines = [l.model_copy(update={"text": l.text.replace(s.heading, "", 1).lstrip(" :\t-–")}) for l in lines]
        built = build_section(s.name, lines)
        if s.name == "summary":
            out["summary"] = (out["summary"] + " " + built).strip()
        else:
            out[s.name] += built
    out["metaDetails"] = extract_header(doc, filename).meta
    return out
