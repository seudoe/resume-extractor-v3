"""Assign every line to a canonical section (PROMPT.md §5 Stage 9)."""

from dataclasses import dataclass, field

from ir import Document

from rx3.sections.headings import Heading, detect_headings, looks_like_programming


@dataclass
class Section:
    name: str  # canonical: summary | workHistory | ... | other | header
    heading: str | None  # None for the pre-heading block / headless blocks
    heading_id: str | None
    line_ids: list[str] = field(default_factory=list)  # content lines (heading line excluded unless inline)
    inline: bool = False
    source: str = "synonym"


def segment_sections(doc: Document) -> list[Section]:
    """Sections in document order. The first is always the `header` block
    (everything before the first heading — name/contact — empty if none).
    Resumes with no recognisable headings come back as that single block.
    An inline heading ("Languages<tab>English, Hindi") is a one-line section
    and the previous section carries on afterwards."""
    headings = detect_headings(doc)
    sections = [Section("header", None, None)]
    current = sections[0]

    for page in doc.pages:
        prev_region = None
        for line in page.lines:
            region = line.features.region if line.features else 0
            h: Heading | None = headings.get(line.id)
            if h and not h.inline:
                if current.heading_id and not current.line_ids and current.name == h.section:
                    pass  # "SKILLS" immediately followed by "Hard Skills": one section, not two
                else:
                    current = Section(h.section, h.label, line.id, source=h.source)
                    sections.append(current)
            elif h and h.inline:
                # An inline "Label: content" row only opens its own section when
                # its label is styled (bold/caps/...), written "Label:", or it sits in a catch-all
                # block (ADDITIONAL: Languages / Awards ...). A plain label inside
                # a content section ("Leadership" tag in Strengths) is a sub-row.
                sub_row = (
                    h.section == current.name
                    or (h.section == "languages" and current.name == "skills" and looks_like_programming(h.rest))
                    or not (h.styled or h.colon or current.name == "header" or (current.name == "other" and current.source == "synonym"))
                )
                if sub_row:
                    current.line_ids.append(line.id)
                else:
                    sections.append(Section(h.section, h.label, line.id, [line.id], inline=True, source=h.source))
            else:
                # A new column/sidebar starting without its own heading (a
                # contact-icon block, a photo caption) isn't a continuation of
                # the previous column's last section.
                if prev_region is not None and region != prev_region and current.name not in ("other", "header") and current.line_ids:
                    current = Section("other", None, None)
                    sections.append(current)
                current.line_ids.append(line.id)
            prev_region = region
    return sections


def line_sections(sections: list[Section]) -> dict[str, str]:
    """line id -> canonical section name (heading lines belong to their section)."""
    out: dict[str, str] = {}
    for s in sections:
        if s.heading_id and not s.inline:
            out[s.heading_id] = s.name
        for lid in s.line_ids:
            out[lid] = s.name
    return out
