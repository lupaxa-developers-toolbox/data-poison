"""Email edges. Syntax is not delivery.

Policies, selected with ``--policy``:

- ``conservative``: everyday ASCII addresses, plus-tags allowed, no quoted spaces.
- ``standards``: a documented subset of RFC 5321 syntax, including a quoted local part.
- ``ascii``: the same shape as conservative, and any non-ASCII byte is invalid.
"""

from __future__ import annotations

from lupaxa.data_poison.catalogue import fixed

_C = "emails"


def _e(
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
        tags=("email",),
        explanation=why + " This does not mean the mailbox exists.",
        intended="Address checks that only allow a short ASCII local part.",
    )


_e(
    "emails.ordinary",
    "Ordinary",
    "ada@example.com",
    "valid",
    "email-conservative",
    "mild",
    "A short ASCII address.",
)
_e(
    "emails.plus",
    "Plus Addressing",
    "ada+tag@example.com",
    "valid",
    "email-conservative",
    "awkward",
    "A plus tag. Some apps strip it and some reject it.",
)
_e(
    "emails.subdomain",
    "Subdomain",
    "ada@mail.example.com",
    "valid",
    "email-conservative",
    "mild",
    "A host with a subdomain.",
)
_e(
    "emails.idna",
    "Internationalised Domain",
    "ada@xn--bcher-kva.example",
    "valid",
    "email-standards",
    "awkward",
    "A punycode domain.",
)
_e(
    "emails.unicode-local",
    "Unicode Local Part",
    "ádá@example.com",
    "valid",
    "email-standards",
    "hostile",
    "A non-ASCII local part. Invalid under the ascii policy.",
)
_e(
    "emails.quoted-local",
    "Quoted Local Part",
    '"ada lovelace"@example.com',
    "valid",
    "email-standards",
    "hostile",
    "A quoted local part. The conservative policy rejects the space.",
)
_e(
    "emails.punctuation",
    "Unusual Punctuation",
    "ada!tag@example.com",
    "valid",
    "email-standards",
    "awkward",
    "A bang in the local part.",
)
_e(
    "emails.length",
    "Length Boundary",
    ("a" * 64) + "@example.com",
    "valid",
    "email-standards",
    "nightmare",
    "A 64-character local part, the common maximum.",
)
_e(
    "emails.empty-local",
    "Empty Local Part",
    "@example.com",
    "invalid",
    "email-conservative",
    "hostile",
    "Nothing before the @.",
)
_e(
    "emails.empty-domain",
    "Empty Domain",
    "ada@",
    "invalid",
    "email-conservative",
    "hostile",
    "Nothing after the @.",
)
_e(
    "emails.consecutive-dots",
    "Consecutive Dots",
    "ada..love@example.com",
    "invalid",
    "email-conservative",
    "hostile",
    "Two dots in a row.",
)
_e(
    "emails.missing-separator",
    "Missing Separator",
    "ada.example.com",
    "invalid",
    "email-conservative",
    "hostile",
    "No @.",
)
_e(
    "emails.whitespace",
    "Embedded Whitespace",
    "ada @example.com",
    "invalid",
    "email-conservative",
    "hostile",
    "A space before the @.",
)
_e(
    "emails.padding",
    "Surrounding Whitespace",
    " ada@example.com ",
    "invalid",
    "email-conservative",
    "mild",
    "Spaces around the address.",
)
_e(
    "emails.case",
    "Case Variation",
    "Ada@Example.COM",
    "valid",
    "email-conservative",
    "awkward",
    "Domain case is not significant. Local-part case often is.",
)
_e(
    "emails.bad-label",
    "Invalid Domain Label",
    "ada@-example.com",
    "invalid",
    "email-conservative",
    "hostile",
    "A domain label must not start with a hyphen.",
)
_e(
    "emails.too-long",
    "Excessively Long",
    ("a" * 70) + "@" + ("b" * 250) + ".example",
    "invalid",
    "email-standards",
    "apocalypse",
    "Longer than the usual 64- and 255-character limits.",
)
