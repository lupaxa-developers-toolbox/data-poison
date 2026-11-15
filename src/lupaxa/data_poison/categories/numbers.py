"""Numeric edge cases. JSON mode never emits NaN or infinity."""

from __future__ import annotations

import random
import struct

from lupaxa.data_poison.catalogue import Options, fixed, parameterised

_C = "numbers"


def _t(
    identifier: str, name: str, payload: str, validity: str, contract: str, risk: str, why: str
) -> None:
    fixed(
        identifier,
        category=_C,
        name=name,
        payload=payload,
        validity=validity,
        contract=contract,
        risk=risk,
        tags=("boundary",),
        explanation=why,
        intended="Parsers that only accept everyday decimal integers.",
    )


_t("numbers.zero", "Zero", "0", "valid", "integer-text", "mild", "Zero.")
_t(
    "numbers.negative-zero",
    "Negative Zero",
    "-0",
    "valid",
    "integer-text",
    "awkward",
    "Negative zero as text.",
)
_t(
    "numbers.explicit-plus",
    "Explicit Plus",
    "+42",
    "valid",
    "numeric-text",
    "awkward",
    "A leading plus. JSON numbers reject it.",
)
_t(
    "numbers.leading-zeros",
    "Leading Zeros",
    "007",
    "valid",
    "numeric-text",
    "awkward",
    "Leading zeros. Not a JSON number.",
)
_t(
    "numbers.whitespace",
    "Whitespace Around Number",
    " 42 ",
    "valid",
    "numeric-text",
    "mild",
    "Spaces around a number.",
)
_t(
    "numbers.thousands",
    "Thousands Separator",
    "1,000",
    "invalid",
    "integer-text",
    "awkward",
    "A comma thousands separator is not a plain integer.",
)
_t(
    "numbers.locale-decimal",
    "Locale Decimal",
    "1,5",
    "invalid",
    "integer-text",
    "awkward",
    "A comma used as a decimal mark.",
)
_t(
    "numbers.empty",
    "Empty Numeric String",
    "",
    "malformed",
    "numeric-text",
    "hostile",
    "No digits at all.",
)
_t(
    "numbers.invalid-token",
    "Invalid Token",
    "12abc",
    "malformed",
    "numeric-text",
    "hostile",
    "Digits followed by letters.",
)
_t(
    "numbers.numeric-string",
    "Numeric String",
    '"42"',
    "valid",
    "json-string",
    "awkward",
    "A JSON string that looks like a number.",
)
_t(
    "numbers.scientific",
    "Scientific Notation",
    "1e309",
    "valid",
    "numeric-text",
    "hostile",
    "An exponent many floats cannot hold.",
)
_t(
    "numbers.exponent.large",
    "Large Exponent",
    "1e+9999",
    "valid",
    "numeric-text",
    "apocalypse",
    "A huge exponent.",
)
_t(
    "numbers.exponent.small",
    "Small Exponent",
    "1e-9999",
    "valid",
    "numeric-text",
    "apocalypse",
    "A tiny exponent.",
)
_t(
    "numbers.json-overflow",
    "JSON Number Overflow",
    "1e309",
    "valid",
    "json-number",
    "hostile",
    "Valid JSON number text that overflows IEEE-754.",
)
_t(
    "numbers.json.nan",
    "JSON NaN",
    "NaN",
    "malformed",
    "json-number",
    "hostile",
    "NaN is not a JSON numeric literal.",
)
_t(
    "numbers.json.infinity",
    "JSON Infinity",
    "Infinity",
    "malformed",
    "json-number",
    "hostile",
    "Infinity is not a JSON numeric literal.",
)


def _bounds(rng: random.Random, options: Options) -> bytes:
    bits = options.bits or 32
    signed = True if options.signed is None else options.signed
    if bits not in {8, 16, 32, 64}:
        bits = 32
    if signed:
        lo = -(1 << (bits - 1))
        hi = (1 << (bits - 1)) - 1
    else:
        lo = 0
        hi = (1 << bits) - 1
    return f"{lo},{hi}".encode()


parameterised(
    "numbers.integer-bounds",
    category=_C,
    name="Integer Bounds",
    build=_bounds,
    validity="valid",
    contract="integer-width",
    risk="awkward",
    tags=("boundary",),
    explanation=(
        "Minimum and maximum for the requested width and signedness. Default is signed 32-bit."
    ),
    intended="Off-by-one checks at the ends of an integer width.",
)


def _outside(rng: random.Random, options: Options) -> bytes:
    lo = 0 if options.minimum is None else options.minimum
    hi = 100 if options.maximum is None else options.maximum
    return f"{lo - 1},{hi + 1}".encode()


parameterised(
    "numbers.outside-range",
    category=_C,
    name="Outside Range",
    build=_outside,
    validity="invalid",
    contract="configured-range",
    risk="hostile",
    tags=("boundary",),
    explanation="One below the minimum and one above the maximum. Defaults are 0 and 100.",
    intended="Range checks that use a strict comparison the wrong way.",
)


def _float_precision(_rng: random.Random, _options: Options) -> bytes:
    value = struct.unpack("!d", bytes.fromhex("3ff0000000000001"))[0]
    return repr(value).encode()


parameterised(
    "numbers.float-precision",
    category=_C,
    name="Float Precision",
    build=_float_precision,
    validity="valid",
    contract="ieee-754-binary64",
    risk="awkward",
    tags=("float",),
    explanation=(
        "The double just above 1.0. It is not the decimal 1.0000000000000002 in every printer."
    ),
    intended="Decimal formatting that assumes binary floats are exact.",
)


def _subnormal(_rng: random.Random, _options: Options) -> bytes:
    value = struct.unpack("!d", bytes.fromhex("0000000000000001"))[0]
    return repr(value).encode()


parameterised(
    "numbers.subnormal",
    category=_C,
    name="Subnormal",
    build=_subnormal,
    validity="valid",
    contract="ieee-754-binary64",
    risk="hostile",
    tags=("float",),
    explanation="The smallest positive subnormal double.",
    intended="Code that flushes subnormals to zero.",
)


def _normal_min(_rng: random.Random, _options: Options) -> bytes:
    value = struct.unpack("!d", bytes.fromhex("0010000000000000"))[0]
    return repr(value).encode()


parameterised(
    "numbers.smallest-normal",
    category=_C,
    name="Smallest Normal",
    build=_normal_min,
    validity="valid",
    contract="ieee-754-binary64",
    risk="awkward",
    tags=("float",),
    explanation="The smallest positive normal double.",
    intended="Underflow checks.",
)

fixed(
    "numbers.infinity.positive",
    category=_C,
    name="Positive Infinity",
    payload="inf",
    validity="valid",
    contract="ieee-754-binary64",
    risk="hostile",
    tags=("float",),
    explanation="Positive infinity as Python float text. Not valid JSON.",
    intended="Comparisons that assume every number is finite.",
)
fixed(
    "numbers.infinity.negative",
    category=_C,
    name="Negative Infinity",
    payload="-inf",
    validity="valid",
    contract="ieee-754-binary64",
    risk="hostile",
    tags=("float",),
    explanation="Negative infinity. Not valid JSON.",
    intended="Comparisons that assume every number is finite.",
)
fixed(
    "numbers.nan",
    category=_C,
    name="NaN",
    payload="nan",
    validity="valid",
    contract="ieee-754-binary64",
    risk="hostile",
    tags=("float",),
    explanation="NaN compares unequal to itself. Not valid JSON.",
    intended="Equality checks.",
)
fixed(
    "numbers.bigint",
    category=_C,
    name="Big Integer",
    payload="9" * 80,
    validity="valid",
    contract="arbitrary-precision-integer",
    risk="apocalypse",
    tags=("boundary",),
    explanation="An 80-digit integer. Fine for arbitrary precision, not for a 64-bit int.",
    intended="Fixed-width integer conversions.",
)
fixed(
    "numbers.decimal-boundary",
    category=_C,
    name="Decimal Boundary",
    payload="0.0000000000000000001",
    validity="valid",
    contract="decimal-text",
    risk="awkward",
    tags=("decimal",),
    explanation="A decimal with more places than binary64 can keep.",
    intended="Money code that uses binary floats.",
)
fixed(
    "numbers.mixed-types",
    category=_C,
    name="Mixed Numeric Types",
    payload='[1, 1.0, "1"]',
    validity="valid",
    contract="json-array",
    risk="awkward",
    tags=("json",),
    explanation="An integer, a float, and a numeric string in one JSON array.",
    intended="Code that treats those three as the same value.",
)
