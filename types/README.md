# types/

Source-of-truth schemas, filled in at Stage 2.

- `resume.py` — Pydantic v2 models mirroring `ifind/types/resume.ts` + `generics.ts` (the output contract).
- `sections/` — one module per resume section (work, education, project, ...).
- `ir.py` — internal Document IR (Span, Line, Block, Page, Document, Provenance) used between pipeline stages.
- `generated/` — exported `resume.schema.json` and a generated `.ts` for diffing against `ifind/types/resume.ts`.
