# Decisions

Each entry: the choice, the alternatives considered, and the eval numbers (if
any) that decided it. Append-only within a stage; superseding decisions should
reference the entry they replace rather than deleting it.

## Stage 1 — Scaffold

- **Package manager: uv.** Alternatives: pip+venv, poetry. uv is fast,
  lockfile-based, and specified by PROMPT.md §3. No eval numbers (tooling
  choice, not a modeling choice) — deferred detail to Stage 3.
- **Package name `rx3`** for `src/rx3/` to keep imports short (`from rx3.ingest import pdf`).
- Nothing else decided yet — Stage 1 is scaffolding only, no extraction code.

## Stage 2 — Types / schema

- **`types/` is not dot-imported as a package.** Bug found while building this
  stage: `from types.resume import X` silently resolves to the *stdlib*
  `types` module (not our directory) because `types` is already cached in
  `sys.modules` before any of our code runs — Python never re-checks
  `sys.path` for a name already in the module cache, and the stdlib `types`
  module has no `resume` attribute, so the import raises `ModuleNotFoundError`.
  Confirmed empirically (`tools/export_schema.py` failed exactly this way on
  first run). Fix: keep the on-disk folder named `types/` (per PROMPT.md §4),
  but never dot-import it as `types.X`. Instead `types/` itself is put on
  `sys.path` (via `conftest.py` for tests, inline in `tools/export_schema.py`
  for scripts) and its modules import each other flatly
  (`from generics import DateRange`, `from sections.work import WorkHistory`).
  Anything under `src/rx3/` that needs these schemas later should do the same
  — add `types/` to `sys.path`, then import flat names, never `import types`.
- **Empty-value policy:** required string fields default to `""`, fields typed
  `X | null` in `ifind/types/resume.ts` default to `None`, arrays default to
  `[]`. Decided by reading `ifind/lib/resumeParser.ts` (`normaliseHFOutput`,
  which already builds `metaDetails` with `?? ""` for required strings and
  `?? null` for nullable ones) and `ifind/components/dashboard/OverviewTab.tsx`
  (defensive `?? 0` / `|| []` on `workHistory`/`education`/`skills`), so v3's
  defaults match what the current glue code and UI already assume.
  `gender` defaults to `None` per PROMPT.md §1.7 (never infer it).
- **One Pydantic module per TS interface**, named sections placed under
  `types/sections/` as PROMPT.md §4 specifies; anonymous TS interfaces
  (`certifications[]`, `languages[]`, `interests[]`, `Address`, `ExtraLink`,
  `SkillTool`, `ProjectLinks`, `EducationField`) were given explicit names
  since Pydantic needs a class name even where TS left the shape inline.
- **Schema diff tool (`tools/export_schema.py`) is a naive, hand-rolled JSON
  Schema → `.ts` renderer**, not a full codegen library (no new dependency
  for a one-shot diffing aid). Known cosmetic limitation: every field renders
  as optional (`field?:`) in the generated `.ts` because every Pydantic field
  here has a default value (so none are JSON-Schema "required") — this is not
  a real mismatch with `ifind/types/resume.ts`, since v3's `extract()` always
  populates every key; it only affects the diff tool's rendering, not runtime
  output. Field names, nesting and enum values matched `ifind/types/resume.ts`
  exactly on inspection.
