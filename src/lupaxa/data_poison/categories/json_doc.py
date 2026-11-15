"""JSON documents. Malformed cases are raw text and are never re-serialised."""

from __future__ import annotations

import random

from lupaxa.data_poison.catalogue import Options, fixed, parameterised

_C = "json"


def _j(identifier: str, name: str, payload: str, validity: str, risk: str, why: str) -> None:
    contract = "json-syntax" if validity != "malformed" else "json-syntax"
    fixed(
        identifier,
        category=_C,
        name=name,
        payload=payload,
        validity=validity,
        contract=contract,
        risk=risk,
        tags=("json",),
        explanation=why,
        intended="A JSON parser or a schema check.",
    )


_j("json.empty-object", "Empty Object", "{}", "valid", "mild", "An empty object.")
_j("json.empty-array", "Empty Array", "[]", "valid", "mild", "An empty array.")
_j(
    "json.nested-object",
    "Nested Object",
    '{"a":{"b":1}}',
    "valid",
    "awkward",
    "One level of nesting.",
)
_j("json.nested-array", "Nested Array", "[[1]]", "valid", "awkward", "An array inside an array.")
_j(
    "json.mixed-array",
    "Mixed Array",
    '[1, "a", null, true]',
    "valid",
    "awkward",
    "Several JSON types in one array.",
)
_j("json.null", "Null", "null", "valid", "mild", "JSON null.")
_j(
    "json.empty-string",
    "Empty String",
    '{"": ""}',
    "valid",
    "awkward",
    "An empty name and an empty value.",
)
_j(
    "json.large-int",
    "Large Integer",
    '{"n": ' + ("9" * 40) + "}",
    "valid",
    "nightmare",
    "A JSON number wider than 64 bits.",
)
_j(
    "json.small-decimal",
    "Small Decimal",
    '{"n": 1e-20}',
    "valid",
    "awkward",
    "A small decimal in JSON number form.",
)
_j(
    "json.unicode",
    "Unicode String",
    '{"s": "café\\u0000"}',
    "valid",
    "awkward",
    "A non-ASCII character and an escaped NUL.",
)
_j(
    "json.escaped",
    "Escaped Characters",
    '{"s": "\\"\\\\\\/\\b\\f\\n\\r\\t"}',
    "valid",
    "awkward",
    "The JSON escapes.",
)
_j(
    "json.duplicate-keys",
    "Duplicate Keys",
    '{"a": 1, "a": 2}',
    "valid",
    "hostile",
    "Duplicate names are legal JSON and ambiguous. Parsers disagree about which value wins.",
)
_j(
    "json.unterminated-string",
    "Unterminated String",
    '{"a": "hi}',
    "malformed",
    "hostile",
    "The string never closes.",
)
_j(
    "json.invalid-escape",
    "Invalid Escape",
    '{"a": "\\q"}',
    "malformed",
    "hostile",
    "\\q is not a JSON escape.",
)
_j(
    "json.missing-comma",
    "Missing Comma",
    '{"a": 1 "b": 2}',
    "malformed",
    "hostile",
    "Two members and no comma.",
)
_j(
    "json.trailing-comma",
    "Trailing Comma",
    '{"a": 1,}',
    "malformed",
    "hostile",
    "A comma before the closing brace.",
)
_j(
    "json.missing-colon",
    "Missing Colon",
    '{"a" 1}',
    "malformed",
    "hostile",
    "A name with no colon.",
)
_j(
    "json.unquoted-key",
    "Unquoted Name",
    "{a: 1}",
    "malformed",
    "hostile",
    "JSON names must be quoted.",
)
_j(
    "json.truncated-array",
    "Truncated Array",
    "[1, 2",
    "malformed",
    "hostile",
    "The array never closes.",
)
_j(
    "json.truncated-object",
    "Truncated Object",
    '{"a": 1',
    "malformed",
    "hostile",
    "The object never closes.",
)
_j(
    "json.bad-number",
    "Invalid Number",
    '{"a": 01}',
    "malformed",
    "hostile",
    "A leading zero is not a JSON number.",
)
_j(
    "json.trailing-content",
    "Trailing Content",
    "{}{}",
    "malformed",
    "hostile",
    "A second value after a complete document.",
)
_j(
    "json.bad-unicode-escape",
    "Broken Unicode Escape",
    '{"a": "\\u12"}',
    "malformed",
    "hostile",
    "A short \\u escape.",
)


def _deep(rng: random.Random, options: Options) -> bytes:
    depth = min(options.max_depth, 8 if options.profile != "apocalypse" else options.max_depth)
    depth = max(1, depth)
    return ("[" * depth + "0" + "]" * depth).encode()


parameterised(
    "json.deep",
    category=_C,
    name="Deep Nesting",
    build=_deep,
    validity="valid",
    contract="json-syntax",
    risk="apocalypse",
    tags=("json", "depth"),
    explanation="Nested arrays bounded by the depth ceiling. Apocalypse uses the full ceiling.",
    intended="Recursive parsers.",
)


def _wide(rng: random.Random, options: Options) -> bytes:
    count = 32 if options.profile != "apocalypse" else min(1000, options.max_bytes // 4)
    body = ",".join(["1"] * max(1, count))
    return f"[{body}]".encode()


parameterised(
    "json.large-array",
    category=_C,
    name="Large Array",
    build=_wide,
    validity="valid",
    contract="json-syntax",
    risk="nightmare",
    tags=("json", "length"),
    explanation="A flat array. Apocalypse makes it larger, still under the byte ceiling.",
    intended="Code that loads the whole array before checking the length.",
)

fixed(
    "json.invalid-utf8",
    category=_C,
    name="Invalid UTF-8",
    payload=b'{"a":"\xff"}',
    validity="malformed",
    contract="json-syntax",
    risk="hostile",
    tags=("json", "encoding"),
    explanation="A byte that is not UTF-8 inside a JSON string.",
    intended="The parser must reject the document.",
    encoding="binary",
)
