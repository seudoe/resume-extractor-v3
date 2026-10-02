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
