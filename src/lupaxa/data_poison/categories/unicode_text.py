"""Unicode and text edge cases. Confusables are not claimed to be equivalent."""

from __future__ import annotations

import random
import unicodedata
from typing import Literal, cast

from lupaxa.data_poison.catalogue import Options, fixed, parameterised

_C = "unicode"
_TEXT = "unicode-scalar-values"


def _u(
    identifier: str, name: str, payload: str, risk: str, tags: tuple[str, ...], why: str
) -> None:
    fixed(
        identifier,
        category=_C,
        name=name,
        payload=payload,
        validity="valid",
        contract=_TEXT,
        risk=risk,
        tags=tags,
        explanation=why,
        intended="Text handling that assumes a single code unit per character.",
    )


_u("unicode.empty", "Empty String", "", "mild", ("empty",), "An empty string is valid text.")
_u(
    "unicode.whitespace.leading",
    "Leading Whitespace",
    "  hello",
    "mild",
    ("whitespace",),
    "Spaces before the value.",
)
_u(
    "unicode.whitespace.trailing",
    "Trailing Whitespace",
    "hello  ",
    "mild",
    ("whitespace",),
    "Spaces after the value.",
)
_u(
    "unicode.whitespace.repeated",
    "Repeated Whitespace",
    "a   b",
    "mild",
    ("whitespace",),
    "Runs of spaces inside the value.",
)
_u("unicode.whitespace.tab", "Tab", "a\tb", "mild", ("whitespace",), "A horizontal tab.")
_u(
    "unicode.newline.lf",
    "Line Feed",
    "a\nb",
    "awkward",
    ("newline",),
    "A line feed inside the value.",
)
_u(
    "unicode.newline.cr",
    "Carriage Return",
    "a\rb",
    "awkward",
    ("newline",),
    "A carriage return inside the value.",
)
_u(
    "unicode.newline.mixed",
    "Mixed Line Endings",
    "a\r\nb\nc\r",
    "awkward",
    ("newline",),
    "CRLF, LF, and CR in one string.",
)
_u(
    "unicode.nbsp",
    "Non-Breaking Space",
    "a\u00a0b",
    "awkward",
    ("whitespace",),
    "U+00A0 NO-BREAK SPACE.",
)
_u(
    "unicode.zero-width",
    "Zero-Width Space",
    "a\u200bb",
    "awkward",
    ("zero-width",),
    "U+200B ZERO WIDTH SPACE.",
)
_u(
    "unicode.zwj",
    "Zero-Width Joiner",
    "a\u200db",
    "awkward",
    ("zero-width",),
    "U+200D ZERO WIDTH JOINER.",
)
_u(
    "unicode.zwnj",
    "Zero-Width Non-Joiner",
    "a\u200cb",
    "awkward",
    ("zero-width",),
    "U+200C ZERO WIDTH NON-JOINER.",
)
_u(
    "unicode.combining",
    "Combining Characters",
    "e\u0301",
    "awkward",
    ("normalisation",),
    "U+0065 plus U+0301 COMBINING ACUTE ACCENT.",
)
_u(
    "unicode.normalisation.nfc-nfd",
    "NFC and NFD",
    "\u00e9",
    "awkward",
    ("normalisation",),
    "U+00E9 is NFC. Its NFD pair is e + combining acute.",
)
_u(
    "unicode.normalisation.nfkc-nfkd",
    "NFKC and NFKD",
    "\ufb01",
    "awkward",
    ("normalisation",),
    "U+FB01 LATIN SMALL LIGATURE FI expands under NFKC and NFKD.",
)
_u(
    "unicode.bidi",
    "Bidirectional Controls",
    "a\u202eb",
    "hostile",
    ("bidi",),
    "U+202E RIGHT-TO-LEFT OVERRIDE can reorder display.",
)
_u(
    "unicode.rtl",
    "Right to Left",
    "\u05d0\u05d1",
    "awkward",
    ("bidi",),
    "Hebrew letters are right-to-left text.",
)
_u(
    "unicode.confusable",
    "Confusable Characters",
    "p\u0430ypal",
    "hostile",
    ("confusable",),
    "Cyrillic a looks like Latin a. They are not the same character.",
)
_u(
    "unicode.emoji",
    "Emoji Sequence",
    "\U0001f468\u200d\U0001f469\u200d\U0001f467",
    "awkward",
    ("emoji",),
    "A family emoji made of several code points and joiners.",
)
_u(
    "unicode.emoji.skin",
    "Emoji Skin Tone",
    "\U0001f44d\U0001f3fd",
    "awkward",
    ("emoji",),
    "Thumbs up plus a skin-tone modifier.",
)
_u(
    "unicode.regional",
    "Regional Indicators",
    "\U0001f1ec\U0001f1e7",
    "awkward",
    ("emoji",),
    "Regional indicators that render as a flag.",
)
_u(
    "unicode.variation",
    "Variation Selector",
    "\u2764\ufe0f",
    "awkward",
    ("emoji",),
    "Heart plus emoji variation selector 16.",
)
_u(
    "unicode.supplementary",
    "Supplementary Plane",
    "\U0001f600",
    "awkward",
    ("plane",),
    "U+1F600 is outside the basic multilingual plane.",
)
_u(
    "unicode.unassigned",
    "Unassigned Code Point",
    "\U00040000",
    "hostile",
    ("unassigned",),
    "A private-use-adjacent unassigned scalar, not a named character.",
)
_u(
    "unicode.noncharacter",
    "Noncharacter",
    "\ufffe",
    "hostile",
    ("noncharacter",),
    "U+FFFE is a noncharacter. It is a valid scalar but not for interchange.",
)
_u(
    "unicode.repeated",
    "Repeated Character",
    "a" * 64,
    "mild",
    ("length",),
    "The same character many times.",
)
_u(
    "unicode.nul",
    "Embedded NUL",
    "a\x00b",
    "hostile",
    ("control",),
    "U+0000 inside a string. C-style strings stop here.",
)
_u(
    "unicode.controls",
    "ASCII Controls",
    "\x01\x02\x1b",
    "hostile",
    ("control",),
    "SOH, STX, and ESC.",
)
_u(
    "unicode.line-separator",
    "Line Separator",
    "a\u2028b",
    "awkward",
    ("newline",),
    "U+2028 LINE SEPARATOR.",
)
_u(
    "unicode.paragraph-separator",
    "Paragraph Separator",
    "a\u2029b",
    "awkward",
    ("newline",),
    "U+2029 PARAGRAPH SEPARATOR.",
)
_u(
    "unicode.casefold.turkish-i",
    "Turkish I",
    "I\u0131i\u0130",
    "awkward",
    ("casefold",),
    "Dotted and dotless I. Turkish case folding is not English case folding.",
)
_u(
    "unicode.casefold.sharp-s",
    "German Sharp S",
    "\u00df",
    "awkward",
    ("casefold",),
    "U+00DF case-folds to SS.",
)
_u(
    "unicode.mixed-scripts",
    "Mixed Scripts",
    "Latin\u041a\u03a9",
    "awkward",
    ("mixed-script",),
    "Latin, Cyrillic, and Greek in one string.",
)


def _long(rng: random.Random, options: Options) -> bytes:
    width = 4096 if options.profile != "apocalypse" else options.max_bytes
    width = max(1, min(width, options.max_bytes))
    piece = "\u0301"
    return (piece * (width // len(piece.encode()))).encode()


parameterised(
    "unicode.very-long",
    category=_C,
    name="Very Long String",
    build=_long,
    validity="valid",
    contract=_TEXT,
    risk="apocalypse",
    tags=("length", "boundary"),
    explanation="A long combining sequence, clipped to the payload ceiling.",
    intended="Allocations and length checks that use bytes instead of scalars.",
)

fixed(
    "unicode.utf8.invalid",
    category=_C,
    name="Invalid UTF-8",
    payload=b"\xff\xfe",
    validity="malformed",
    contract="utf-8",
    risk="hostile",
    tags=("encoding",),
    explanation="FF FE is not a valid UTF-8 sequence.",
    intended="Decoders must reject the bytes rather than substitute silently.",
    encoding="binary",
)
fixed(
    "unicode.utf8.truncated",
    category=_C,
    name="Truncated UTF-8",
    payload="é".encode()[:1],
    validity="malformed",
    contract="utf-8",
    risk="hostile",
    tags=("encoding",),
    explanation="The first byte of U+00E9 without its continuation.",
    intended="A decoder must not invent the missing byte.",
    encoding="binary",
)
fixed(
    "unicode.utf8.surrogate",
    category=_C,
    name="UTF-8 Encoded Surrogate",
    payload=b"\xed\xa0\x80",
    validity="malformed",
    contract="utf-8",
    risk="hostile",
    tags=("encoding",),
    explanation="ED A0 80 encodes a surrogate, which UTF-8 forbids.",
    intended="Reject WTF-8 style surrogate encodings.",
    encoding="binary",
)


def names_for(text: str) -> str:
    """Unicode names for the code points in ``text``, when Python knows them."""
    parts: list[str] = []
    for char in text:
        try:
            label = unicodedata.name(char)
        except ValueError:
            label = f"U+{ord(char):04X}"
        parts.append(f"U+{ord(char):04X} {label}")
    return ", ".join(parts)


def normalise(text: str, form: str) -> str:
    """Return ``text`` in NFC, NFD, NFKC, or NFKD."""
    if form not in {"NFC", "NFD", "NFKC", "NFKD"}:
        from lupaxa.data_poison.errors import UsageError

        raise UsageError(f"unknown normalisation form {form!r}")
    checked = cast(Literal["NFC", "NFD", "NFKC", "NFKD"], form)
    return unicodedata.normalize(checked, text)
