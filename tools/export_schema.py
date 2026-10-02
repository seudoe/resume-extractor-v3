"""Export types/resume.py to JSON Schema, and a naive .ts for diffing against
ifind/types/resume.ts.

Usage: python tools/export_schema.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# `types/` is kept off sys.path's parent deliberately: dot-importing it as
# `types.resume` would collide with the stdlib `types` module, which is
# already cached in sys.modules by the time any script runs. Put `types/`
# itself on sys.path so its modules import each other flatly instead.
sys.path.insert(0, str(ROOT / "types"))

from resume import ParsedResumeData  # noqa: E402

OUT_DIR = ROOT / "types" / "generated"

# Pydantic field type -> TS type, for the simple scalar cases. Nested models
# are walked recursively below.
_SCALAR_TS = {"string": "string", "integer": "number", "number": "number", "boolean": "boolean"}


def _ts_type(schema: dict, defs: dict) -> str:
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return name
    if "anyOf" in schema:
        parts = [_ts_type(s, defs) for s in schema["anyOf"]]
        return " | ".join(dict.fromkeys(parts))  # dedupe, keep order
    t = schema.get("type")
    if t == "array":
        item = _ts_type(schema.get("items", {}), defs)
        return f"{item}[]"
    if t == "null":
        return "null"
    if "enum" in schema:
        return " | ".join(json.dumps(v) for v in schema["enum"])
    if t in _SCALAR_TS:
        return _SCALAR_TS[t]
    return "unknown"


def _render_interface(name: str, schema: dict, defs: dict) -> str:
    lines = [f"export interface {name} {{"]
    required = set(schema.get("required", []))
    for field, field_schema in schema.get("properties", {}).items():
        optional = "" if field in required else "?"
        lines.append(f"  {field}{optional}: {_ts_type(field_schema, defs)};")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    schema = ParsedResumeData.model_json_schema()
    (OUT_DIR / "resume.schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

    defs = schema.get("$defs", {})
    blocks = [_render_interface(name, s, defs) for name, s in defs.items()]
    blocks.append(_render_interface("ParsedResumeData", schema, defs))
    (OUT_DIR / "resume.ts").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_DIR / 'resume.schema.json'}")
    print(f"Wrote {OUT_DIR / 'resume.ts'}")


if __name__ == "__main__":
    main()
