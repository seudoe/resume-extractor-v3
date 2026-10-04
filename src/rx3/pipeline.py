"""The extraction pipeline (PROMPT.md §5 Stage 12): bytes -> ParsedResumeData-shaped dict.

    from rx3.pipeline import extract
    out = extract(pdf_bytes, "resume.pdf", debug=True)   # out["_debug"]["timings_ms"] has per-stage timing

Stages: ingest (+OCR fallback) -> layout -> sections -> header -> rules entries -> normalise -> ground ->
dedupe/order -> confidence -> validate. Deterministic: no randomness, no network, no model calls yet (GLiNER
slots in at the rules stage once Stage 10 finishes)."""

import os
import time
from pathlib import Path

import rx3  # noqa: F401  (puts types/ on sys.path)
from rx3.fields.rules import extract_rules
from rx3.header import extract_header
from rx3.ingest.docx import ingest_docx
from rx3.ingest.pdf import ingest_pdf
from rx3.ingest.quality import page_quality
from rx3.layout import analyze_layout
from rx3.normalise import normalise, strip_private
from rx3.ocr.select import apply_ocr_fallback
from rx3.sections.segment import segment_sections
from rx3.validate import clean, confidence, grounding

VERSION = "0.12.0-stage12"


class UnsupportedFormat(ValueError):
    """Not a PDF or DOCX (the API maps this to 415)."""


class UnreadableDocument(ValueError):
    """Corrupt or password-protected (the API maps this to 422)."""


def _kind(data: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if data[:5] == b"%PDF-" or ext == ".pdf":
        return "pdf"
    if data[:2] == b"PK" and ext in (".docx", ""):
        return "docx"
    raise UnsupportedFormat(f"unsupported file type {ext or 'unknown'!r} (PDF or DOCX only)")


def extract(data: bytes, filename: str = "", debug: bool = False, with_confidence: bool = False, gliner: bool | None = None) -> dict:
    """`gliner`: refine entry fields with GLiNER2 (Stage 10). None -> env RX3_ENABLE_GLINER=1; off by default so the
    rules-only path needs neither torch nor the model download."""
    timings: dict[str, float] = {}
    t0 = last = time.perf_counter()

    def lap(name: str) -> None:
        nonlocal last
        now = time.perf_counter()
        timings[name] = round((now - last) * 1000, 1)
        last = now

    kind = _kind(data, filename)
    try:
        doc = ingest_pdf(data, filename) if kind == "pdf" else ingest_docx(data, filename)
    except Exception as e:  # noqa: BLE001  (pymupdf / python-docx raise assorted types)
        raise UnreadableDocument(f"could not read {kind}: {e}") from e
    lap("ingest")
    ocr_pages = 0
    if kind == "pdf":
        ocr_pages = sum(page_quality(p)["needs_ocr"] for p in doc.pages)
        doc = apply_ocr_fallback(doc, data)
        lap("ocr")
    doc = analyze_layout(doc)
    lap("layout")
    sections = segment_sections(doc)
    lap("sections")
    header = extract_header(doc, filename)
    lap("header")
    refiner = None
    if os.environ.get("RX3_ENABLE_SLM") == "1":  # Stage 13 experiment, off by default and not recommended (see DECISIONS)
        from rx3.fields.slm import SlmRefiner

        refiner = globals().setdefault("_SLM", SlmRefiner("slm17", use_cache=False))
        refiner.last_ms = 0.0
    elif (os.environ.get("RX3_ENABLE_GLINER") == "1") if gliner is None else gliner:
        from rx3.fields.gliner import shared_refiner

        refiner = shared_refiner()
        refiner.last_ms = 0.0
    raw = extract_rules(doc, filename, sections=sections, header=header, refiner=refiner)
    lap("entries")
    if refiner:
        timings["gliner"] = round(refiner.last_ms, 1)  # already inside "entries"
    norm = normalise(raw, doc, keep_private=True)
    lap("normalise")
    grounded = grounding.ground(norm, doc)
    lap("ground")
    cleaned, notes = clean.dedupe_and_order(grounded.data)
    conf = confidence.score(cleaned, header.provenance)
    lap("confidence")
    final, vnotes = clean.validate(strip_private(cleaned))
    lap("validate")

    if with_confidence:
        final["_confidence"] = conf
    if debug:
        timings["total"] = round((time.perf_counter() - t0) * 1000, 1)
        final["_debug"] = {
            "version": VERSION,
            "source": kind,
            "n_pages": len(doc.pages),
            "n_lines": sum(len(p.lines) for p in doc.pages),
            "ocr_pages": ocr_pages,
            "timings_ms": timings,
            "sections": [{"name": s.name, "heading": s.heading, "n_lines": len(s.line_ids)} for s in sections],
            "dropped_ungrounded": [{"path": d.path, "value": d.value} for d in grounded.dropped],
            "n_strings_checked": grounded.n_checked,
            "notes": notes + vnotes,
            "provenance": grounded.provenance,
            "confidence": conf,
            "uncalibrated_confidence": confidence.UNCALIBRATED,
            "gliner": refiner is not None,
        }
    return final
