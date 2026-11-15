"""JSON Schema Draft 2020-12, the subset this tool actually implements.

Unsupported keywords that change validation are an error in strict mode.
Permissive mode still generates, and marks validity ``unknown`` unless the
supported validator agrees.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from lupaxa.data_poison.errors import InputError, UsageError
from lupaxa.data_poison.models import Case

SUPPORTED = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "enum",
    "const",
    "pattern",
    "format",
    "minProperties",
    "maxProperties",
    "uniqueItems",
    "$defs",
    "$ref",
}
ANNOTATIONS = {
    "title",
    "description",
    "default",
    "examples",
    "$schema",
    "$id",
    "$comment",
    "deprecated",
    "readOnly",
    "writeOnly",
}
FORMATS = {"email", "date-time", "uri", "uuid", "ipv4", "ipv6"}
MODES = {"valid", "invalid", "boundary", "mixed"}


def load_schema(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"could not read schema {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise InputError("schema must be a JSON object")
    return loaded


def unsupported(schema: dict[str, Any]) -> list[str]:
    """Keywords this generator will not pretend to honour."""
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"properties", "$defs"} and isinstance(value, dict):
                    for child in value.values():
                        walk(child)
                    continue
                if key not in SUPPORTED and key not in ANNOTATIONS:
                    found.append(key)
                if key == "$ref" and isinstance(value, str) and not value.startswith("#"):
                    found.append("$ref-remote")
                if key == "pattern" and isinstance(value, str) and _unsafe_pattern(value):
                    found.append("pattern")
                if key == "format" and value not in FORMATS:
                    found.append(f"format:{value}")
                if key == "additionalProperties" and not isinstance(value, bool):
                    found.append("additionalProperties")
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return sorted(set(found))


def _unsafe_pattern(pattern: str) -> bool:
    return len(pattern) > 80 or "+)" in pattern or "*)" in pattern or "(?:" in pattern


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    if not ref.startswith("#/$defs/"):
        raise InputError(f"only local #/$defs references are supported, not {ref}")
    name = ref.split("/")[-1]
    defs = root.get("$defs")
    if not isinstance(defs, dict) or name not in defs:
        raise InputError(f"missing $defs entry {name}")
    target = defs[name]
    if not isinstance(target, dict):
        raise InputError(f"$defs.{name} must be an object")
    return _resolve(target, root)


def _types(schema: dict[str, Any]) -> list[str]:
    kind = schema.get("type", "object")
    if isinstance(kind, list):
        return [item for item in kind if isinstance(item, str)]
    if isinstance(kind, str):
        return [kind]
    return ["object"]


def _valid_value(schema: dict[str, Any], root: dict[str, Any], depth: int) -> Any:
    schema = _resolve(schema, root)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    kinds = _types(schema)
    kind = next((item for item in kinds if item != "null"), kinds[0] if kinds else "object")
    if kind == "null":
        return None
    if kind == "boolean":
        return True
    if kind == "integer":
        lo = schema.get("minimum", schema.get("exclusiveMinimum"))
        hi = schema.get("maximum", schema.get("exclusiveMaximum"))
        if isinstance(schema.get("exclusiveMinimum"), (int, float)):
            lo = int(schema["exclusiveMinimum"]) + 1
        if isinstance(schema.get("exclusiveMaximum"), (int, float)):
            hi = int(schema["exclusiveMaximum"]) - 1
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            return int(lo)
        if isinstance(lo, (int, float)):
            return int(lo)
        return 0
    if kind == "number":
        return float(schema.get("minimum", 0))
    if kind == "string":
        fmt = schema.get("format")
        samples = {
            "email": "ada@example.com",
            "date-time": "2024-06-01T12:00:00Z",
            "uri": "https://example.com/a",
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "ipv4": "127.0.0.1",
            "ipv6": "::1",
        }
        if isinstance(fmt, str) and fmt in samples:
            return samples[fmt]
        lo = int(schema.get("minLength", 1 if schema.get("pattern") else 0))
        hi = int(schema.get("maxLength", max(lo, 8)))
        return "a" * min(max(lo, 1), hi)
    if kind == "array":
        count = int(schema.get("minItems", 0))
        items = schema.get("items")
        item_schema: dict[str, Any] = items if isinstance(items, dict) else {}
        return [_valid_value(item_schema, root, depth + 1) for _ in range(count)]
    if depth > 8:
        return {}
    raw_properties = schema.get("properties")
    properties: dict[str, Any] = raw_properties if isinstance(raw_properties, dict) else {}
    raw_required = schema.get("required")
    required: list[Any] = raw_required if isinstance(raw_required, list) else []
    required_names = [str(item) for item in required]
    names = list(dict.fromkeys([*required_names, *properties]))
    minimum = int(schema.get("minProperties", 0))
    while len(names) < minimum:
        names.append(f"extra{len(names)}")
    built = {}
    for name in names:
        child = properties.get(name, {})
        child_schema: dict[str, Any] = child if isinstance(child, dict) else {}
        built[str(name)] = _valid_value(child_schema, root, depth + 1)
    return built


def _invalid_value(schema: dict[str, Any], root: dict[str, Any]) -> tuple[Any, str]:
    schema = _resolve(schema, root)
    if "enum" in schema:
        return "not-in-enum", "enum"
    if "const" in schema:
        return None if schema["const"] is not None else "x", "const"
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    if required:
        value = _valid_value(schema, root, 0)
        if isinstance(value, dict) and required[0] in value:
            value.pop(required[0])
            return value, "required"
    if schema.get("additionalProperties") is False:
        value = _valid_value(schema, root, 0)
        if isinstance(value, dict):
            value["unexpected"] = 1
            return value, "additionalProperties"
    kinds = _types(schema)
    if "string" in kinds and "maxLength" in schema:
        return "x" * (int(schema["maxLength"]) + 1), "maxLength"
    if "integer" in kinds and "minimum" in schema:
        return int(schema["minimum"]) - 1, "minimum"
    if "array" in kinds and "maxItems" in schema:
        items = schema.get("items")
        item_schema = items if isinstance(items, dict) else {}
        count = int(schema["maxItems"]) + 1
        return [_valid_value(item_schema, root, 1) for _ in range(count)], "maxItems"
    if "array" in kinds and schema.get("uniqueItems") is True:
        return [1, 1], "uniqueItems"
    if kinds and kinds[0] != "string":
        return "wrong-type", "type"
    return 1, "type"


def generate_schema_cases(
    schema: dict[str, Any],
    *,
    count: int,
    seed: int,
    mode: str,
    strict: bool,
    schema_name: str,
    max_bytes: int,
) -> list[Case]:
    if mode not in MODES:
        raise UsageError(f"mode must be one of: {', '.join(sorted(MODES))}")
    problems = unsupported(schema)
    if problems and strict:
        raise InputError(
            "unsupported schema keyword "
            f"{problems[0]!r}. Strict mode will not claim the output is schema-valid."
        )
    rng = random.Random(seed)
    validator = Draft202012Validator(schema)
    cases: list[Case] = []
    for index in range(count):
        use_invalid = (
            mode == "invalid"
            or (mode == "mixed" and index % 2)
            or (mode == "boundary" and index % 2)
        )
        if use_invalid:
            value, broken = _invalid_value(schema, schema)
            expected = "invalid"
        else:
            value, broken = _valid_value(schema, schema, 0), ""
            expected = "valid"
        raw = json.dumps(value).encode()
        if len(raw) > max_bytes:
            raise InputError(f"schema case {index + 1} is larger than max-bytes")
        try:
            validator.validate(value)
            actual = "valid"
        except ValidationError as exc:
            actual = "invalid"
            broken = broken or (exc.validator or "schema")
        validity = expected if not problems else "unknown"
        if actual != expected and not problems:
            validity = "unknown"
        cases.append(
            Case(
                case_id=f"schema-{index + 1:04d}",
                category="schema",
                generator=f"schema-{mode}",
                payload=raw,
                encoding="utf-8",
                validity=validity,
                contract="json-schema-draft-2020-12-subset",
                explanation=(
                    f"Expected {expected}. Validator says {actual}."
                    + (f" Broke {broken}." if broken else "")
                    + (" Unsupported keywords were present." if problems else "")
                ),
                intended="One constraint at a time when the case is invalid.",
                seed=seed,
                parameters={
                    "mode": mode,
                    "expected": expected,
                    "actual": actual,
                    "constraint": broken,
                    "strict": strict,
                    "rng": rng.randrange(10),
                },
                schema_ref=schema_name,
                expected=expected,
                name=schema_name,
            )
        )
    return cases
