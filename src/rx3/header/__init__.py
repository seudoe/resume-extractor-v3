"""Header & contact extraction (rules only; PROMPT.md §5 Stage 8)."""

from dataclasses import dataclass, field

from ir import Document, Provenance

from rx3.header.contact import extract_email, extract_phone
from rx3.header.links import extract_links
from rx3.header.location import extract_location
from rx3.header.name import extract_name
from rx3.header.zone import header_lines


@dataclass
class HeaderResult:
    meta: dict  # shaped like ResumeMetaDetails
    provenance: dict[str, Provenance] = field(default_factory=dict)


def extract_header(doc: Document, filename: str = "") -> HeaderResult:
    """`doc` must already be through `analyze_layout` (name scoring uses the
    line features). `gender` is always None: never inferred (PROMPT.md §1.7)."""
    header = header_lines(doc)
    email, p_email = extract_email(doc)
    phone, p_phone = extract_phone(doc)
    name, p_name = extract_name(doc, filename, email)
    links = extract_links(doc, {l.id for l in header})
    address, p_loc = extract_location(doc, header)

    prov = {k: v for k, v in {"name": p_name, "email": p_email, "phone_no": p_phone, "address": p_loc}.items() if v}
    prov.update(links["provenance"])
    meta = {
        "name": name,
        "phone_no": phone,
        "gender": None,
        "email": email,
        "github_profile": links["github"],
        "linkedin": links["linkedin"],
        "address": address,
        "extra_links": links["extra_links"],
    }
    return HeaderResult(meta=meta, provenance=prov)
