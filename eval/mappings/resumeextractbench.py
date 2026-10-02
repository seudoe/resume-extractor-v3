"""Map Careerflow/ResumeExtractBench (HF, CC-BY-4.0) to v3's schema.

Deferred: downloading the dataset needs `huggingface_hub` (not in the
default `dependencies` — only pulled in transitively by the `train` extra),
and there's no extractor yet to benchmark against it (PROMPT.md calls this
"test-only" / external robustness benchmark). Wire this up in Stage 6+ when
there's an OCR/extraction pipeline to actually run against the 28 scanned +
10 adversarial-LaTeX PDFs.

Expected shape once downloaded to data/external/resumeextractbench/: one
PDF + one gold JSON per sample. `map_sample` below is the field-mapping
stub to fill in once the real gold schema is inspected.
"""


def map_sample(bench_gold: dict) -> dict:
    """Map one ResumeExtractBench gold record to v3's ParsedResumeData shape.

    TODO(Stage 6): inspect the real schema from the HF dataset card and fill
    this in. Left unimplemented rather than guessed, per PROMPT.md's
    "measure, don't claim" rule — a guessed mapping would silently produce
    wrong scores.
    """
    raise NotImplementedError(
        "ResumeExtractBench not downloaded yet — see module docstring. "
        "Implement once Stage 6 (OCR) needs the external robustness benchmark."
    )
