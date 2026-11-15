"""URL edges. Nothing here performs a lookup.

Validity uses a documented policy:

- ``absolute-url``: a scheme, a host, and no raw spaces or controls.
- ``relative-reference``: no scheme, still no raw spaces.
- ``url-syntax``: the text is not an absolute URL or a relative reference.
"""

from __future__ import annotations

from lupaxa.data_poison.catalogue import fixed

_C = "urls"


def _url(
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
        tags=("url",),
        explanation=why,
        intended="URL joiners and allow-lists that only expect a short http URL.",
    )


_url(
    "urls.http",
    "HTTP",
    "http://example.com/a",
    "valid",
    "absolute-url",
    "mild",
    "A plain http URL.",
)
_url(
    "urls.https",
    "HTTPS",
    "https://example.com/a",
    "valid",
    "absolute-url",
    "mild",
    "A plain https URL.",
)
_url(
    "urls.idna",
    "Internationalised Domain",
    "https://xn--bcher-kva.example/a",
    "valid",
    "absolute-url",
    "awkward",
    "A punycode label. This is not a claim about the Unicode display form.",
)
_url(
    "urls.idna-unicode",
    "Unicode Domain",
    "https://bücher.example/a",
    "valid",
    "absolute-url",
    "awkward",
    "A Unicode host. IDNA encoding is a separate step and is not done here.",
)
_url(
    "urls.ipv4",
    "IPv4 Host",
    "https://127.0.0.1/a",
    "valid",
    "absolute-url",
    "awkward",
    "An IPv4 host.",
)
_url(
    "urls.ipv6",
    "IPv6 Host",
    "https://[::1]/a",
    "valid",
    "absolute-url",
    "awkward",
    "A bracketed IPv6 host.",
)
_url(
    "urls.port",
    "Explicit Port",
    "https://example.com:8443/a",
    "valid",
    "absolute-url",
    "mild",
    "A non-default port.",
)
_url(
    "urls.default-port",
    "Default Port",
    "https://example.com:443/a",
    "valid",
    "absolute-url",
    "awkward",
    "The scheme's default port written out.",
)
_url(
    "urls.empty-path",
    "Empty Path",
    "https://example.com",
    "valid",
    "absolute-url",
    "mild",
    "No path.",
)
_url(
    "urls.empty-query",
    "Empty Query",
    "https://example.com/a?",
    "valid",
    "absolute-url",
    "awkward",
    "A question mark and no query.",
)
_url(
    "urls.duplicate-query",
    "Duplicate Query",
    "https://example.com/a?x=1&x=2",
    "valid",
    "absolute-url",
    "awkward",
    "The same query name twice.",
)
_url(
    "urls.percent",
    "Percent Encoding",
    "https://example.com/a%20b",
    "valid",
    "absolute-url",
    "awkward",
    "A space written as %20.",
)
_url(
    "urls.double-encoded",
    "Double Encoded",
    "https://example.com/a%2520b",
    "valid",
    "absolute-url",
    "hostile",
    "%2520 decodes once to %20, not to a space.",
)
_url(
    "urls.bad-percent",
    "Invalid Percent Escape",
    "https://example.com/%zz",
    "malformed",
    "url-syntax",
    "hostile",
    "%zz is not a hex escape.",
)
_url(
    "urls.unicode-path",
    "Unicode Path",
    "https://example.com/café",
    "valid",
    "absolute-url",
    "awkward",
    "A non-ASCII path. It still needs encoding before it goes on the wire.",
)
_url(
    "urls.fragment",
    "Fragment",
    "https://example.com/a#frag",
    "valid",
    "absolute-url",
    "mild",
    "A fragment.",
)
_url(
    "urls.long-path",
    "Long Path",
    "https://example.com/" + ("a" * 200),
    "valid",
    "absolute-url",
    "nightmare",
    "A long path.",
)
_url(
    "urls.long-query",
    "Long Query",
    "https://example.com/a?" + ("q=1&" * 40),
    "valid",
    "absolute-url",
    "nightmare",
    "A long query.",
)
_url(
    "urls.userinfo",
    "User Info",
    "https://user:secret@example.com/a",
    "valid",
    "absolute-url",
    "hostile",
    "User information. Do not treat this as a secret store.",
)
_url(
    "urls.missing-scheme",
    "Missing Scheme",
    "example.com/a",
    "valid",
    "relative-reference",
    "awkward",
    "No scheme. This policy calls it a relative reference, not an absolute URL.",
)
_url(
    "urls.scheme-relative",
    "Scheme Relative",
    "//example.com/a",
    "valid",
    "relative-reference",
    "awkward",
    "A network-path reference.",
)
_url(
    "urls.unexpected-scheme",
    "Unexpected Scheme",
    "javascript:alert(1)",
    "valid",
    "absolute-url",
    "hostile",
    "Syntactically an absolute URL. An application policy may still forbid the scheme.",
)
_url(
    "urls.whitespace",
    "Embedded Whitespace",
    "https://example.com/a b",
    "malformed",
    "url-syntax",
    "hostile",
    "A raw space.",
)
_url(
    "urls.control",
    "Control Character",
    "https://example.com/\n",
    "malformed",
    "url-syntax",
    "hostile",
    "A raw line feed.",
)
_url(
    "urls.dot-segments",
    "Dot Segments",
    "https://example.com/a/../../b",
    "valid",
    "absolute-url",
    "hostile",
    "Dot segments. Resolution can leave the expected tree.",
)
_url(
    "urls.encoded-slash",
    "Encoded Separator",
    "https://example.com/a%2fb",
    "valid",
    "absolute-url",
    "hostile",
    "%2f is a slash some routers decode and some do not.",
)
_url(
    "urls.bad-authority",
    "Malformed Authority",
    "https://[gggg]/a",
    "malformed",
    "url-syntax",
    "hostile",
    "Brackets that are not an IPv6 address.",
)
