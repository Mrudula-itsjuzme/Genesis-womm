"""Generate wire types using Core's installed PyYAML; --check detects contract drift."""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "apps/web/src/types/core-api.ts"


def convert(schema):
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "const" in schema:
        return json.dumps(schema["const"])
    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])
    if "anyOf" in schema:
        return " | ".join(convert(value) for value in schema["anyOf"])
    kind = schema.get("type")
    if kind == "array":
        return f"Array<{convert(schema['items'])}>"
    if kind == "object":
        required = schema.get("required", [])
        fields = [f"{json.dumps(key)}{'' if key in required else '?'}: {convert(value)};" for key, value in schema.get("properties", {}).items()]
        if schema.get("additionalProperties"):
            fields.append("[key: string]: unknown;")
        return "{ " + " ".join(fields) + " }" if fields else "Record<string, unknown>"
    return {"string": "string", "integer": "number", "number": "number", "boolean": "boolean", "null": "null"}.get(kind, "unknown")


schemas = yaml.safe_load((ROOT / "contracts/core-api.openapi.yaml").read_text(encoding="utf-8"))["components"]["schemas"]
result = "// Generated from contracts/core-api.openapi.yaml. Do not edit.\n" + "\n".join(f"export type {name} = {convert(schema)};" for name, schema in sorted(schemas.items())) + "\n"
if "--check" in sys.argv:
    if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != result:
        raise SystemExit("Wire types drifted; run apps/web/scripts/export_types.py with Core's Python.")
else:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(result, encoding="utf-8")
