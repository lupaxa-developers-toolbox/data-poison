"""XML edges. Parsing in this package disables entity resolution.

Entity-expansion fixtures are small on purpose. They are not a billion laughs.
"""

from __future__ import annotations

import random

from lupaxa.data_poison.catalogue import Options, fixed, parameterised

_C = "xml"


def _x(
    identifier: str,
    name: str,
    payload: str,
    validity: str,
    risk: str,
    why: str,
    contract: str = "xml-syntax",
) -> None:
    fixed(
        identifier,
        category=_C,
        name=name,
        payload=payload,
        validity=validity,
        contract=contract,
        risk=risk,
        tags=("xml",),
        explanation=why,
        intended="An XML parser with external entities and expansion turned off.",
    )


_x("xml.empty-element", "Empty Element", "<a/>", "valid", "mild", "An empty element.")
_x("xml.nested", "Nested Elements", "<a><b>c</b></a>", "valid", "mild", "One child.")
_x("xml.attributes", "Attributes", '<a b="c"/>', "valid", "mild", "One attribute.")
_x(
    "xml.namespaces",
    "Namespaces",
    '<a xmlns:p="urn:example"><p:b/></a>',
    "valid",
    "awkward",
    "A prefixed element.",
)
_x(
    "xml.cdata",
    "CDATA",
    "<a><![CDATA[x<y]]></a>",
    "valid",
    "awkward",
    "CDATA that would be markup outside the section.",
)
_x("xml.entity", "Entity Reference", "<a>&amp;</a>", "valid", "awkward", "A predefined entity.")
_x("xml.unicode", "Unicode Text", "<a>café</a>", "valid", "awkward", "Non-ASCII text.")
_x(
    "xml.escaped",
    "Escaped Specials",
    "<a>&lt;&gt;&amp;</a>",
    "valid",
    "mild",
    "The predefined escapes.",
)
_x("xml.missing-close", "Missing Close", "<a>", "malformed", "hostile", "No end tag.")
_x(
    "xml.mismatched-tags",
    "Mismatched Tags",
    "<a></b>",
    "malformed",
    "hostile",
    "The end tag is a different name.",
)
_x(
    "xml.bad-attribute-quotes",
    "Invalid Attribute Quoting",
    "<a b=c/>",
    "malformed",
    "hostile",
    "An unquoted attribute value.",
)
_x(
    "xml.duplicate-attributes",
    "Duplicate Attributes",
    '<a b="1" b="2"/>',
    "malformed",
    "hostile",
    "The same attribute twice.",
)
_x(
    "xml.bad-char-ref",
    "Invalid Character Reference",
    "<a>&#0;</a>",
    "malformed",
    "hostile",
    "NUL is not a legal XML character.",
)
_x(
    "xml.truncated",
    "Truncated Document",
    "<a",
    "malformed",
    "hostile",
    "The start tag never finishes.",
)
_x(
    "xml.bad-prefix",
    "Unexpected Prefix",
    "<p:a/>",
    "invalid",
    "hostile",
    "A prefix with no declaration. This contract rejects it.",
    "xml-namespaces",
)
_x(
    "xml.entity-expansion",
    "Bounded Entity Expansion",
    '<!DOCTYPE a [<!ENTITY x "hi"><!ENTITY y "&x;&x;">]><a>&y;</a>',
    "invalid",
    "hostile",
    "Two tiny entities. A secure parser must not expand them. This is not a large expansion.",
    "xml-secure",
)


def _deep(rng: random.Random, options: Options) -> bytes:
    depth = min(options.max_depth, 8 if options.profile != "apocalypse" else options.max_depth)
    depth = max(1, depth)
    return ("<a>" * depth + "</a>" * depth).encode()


parameterised(
    "xml.deep",
    category=_C,
    name="Deep Nesting",
    build=_deep,
    validity="valid",
    contract="xml-syntax",
    risk="apocalypse",
    tags=("xml", "depth"),
    explanation="Nested elements bounded by the depth ceiling.",
    intended="Recursive XML parsers.",
)

fixed(
    "xml.invalid-encoding",
    category=_C,
    name="Invalid Encoding",
    payload=b"<?xml version='1.0' encoding='UTF-8'?><a>\xff</a>",
    validity="malformed",
    contract="xml-syntax",
    risk="hostile",
    tags=("xml", "encoding"),
    explanation="The declaration says UTF-8 and the body is not UTF-8.",
    intended="The parser must reject the bytes.",
    encoding="binary",
)
