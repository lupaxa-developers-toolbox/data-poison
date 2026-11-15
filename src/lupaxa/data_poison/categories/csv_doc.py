"""CSV edges for one documented dialect: comma, double quote, LF, optional header.

A value that starts with ``=``, ``+``, ``-``, or ``@`` is marked as a spreadsheet
formula risk. This tool never opens the file.
"""

from __future__ import annotations

from lupaxa.data_poison.catalogue import fixed

_C = "csv"
_DIALECT = "csv-strict-comma-quote-lf"


def _c(identifier: str, name: str, payload: str, validity: str, risk: str, why: str) -> None:
    fixed(
        identifier,
        category=_C,
        name=name,
        payload=payload,
        validity=validity,
        contract=_DIALECT,
        risk=risk,
        tags=("csv",),
        explanation=why,
        intended="A strict CSV reader with a header and a stable column count.",
    )


_c("csv.empty-file", "Empty File", "", "valid", "mild", "No bytes. There is no header and no row.")
_c("csv.header-only", "Header Only", "name,age\n", "valid", "mild", "A header and no data row.")
_c(
    "csv.empty-field",
    "Empty Field",
    "name,age\nada,\n",
    "valid",
    "awkward",
    "A present but empty field.",
)
_c(
    "csv.empty-row",
    "Empty Row",
    "name,age\n\nada,1\n",
    "invalid",
    "hostile",
    "A blank line is not two columns.",
)
_c(
    "csv.quoted",
    "Quoted Field",
    'name,age\n"ada lovelace",1\n',
    "valid",
    "awkward",
    "A quoted field with a space.",
)
_c(
    "csv.embedded-comma",
    "Embedded Comma",
    'name,note\n"a,b",ok\n',
    "valid",
    "awkward",
    "A comma inside quotes.",
)
_c(
    "csv.embedded-newline",
    "Embedded Newline",
    'name,note\n"a\nb",ok\n',
    "valid",
    "hostile",
    "A newline inside quotes. Line-based splitters break this.",
)
_c(
    "csv.embedded-quote",
    "Embedded Quote",
    'name,note\n"say ""hi""",ok\n',
    "valid",
    "awkward",
    "A doubled quote inside a quoted field.",
)
_c(
    "csv.mixed-endings",
    "Mixed Line Endings",
    "name,age\r\nada,1\n",
    "invalid",
    "hostile",
    "CRLF then LF. The strict dialect wants LF only.",
)
_c(
    "csv.inconsistent-columns",
    "Inconsistent Columns",
    "name,age\nada\n",
    "invalid",
    "hostile",
    "A data row with fewer columns than the header.",
)
_c(
    "csv.duplicate-headers",
    "Duplicate Headers",
    "name,name\nada,bee\n",
    "invalid",
    "hostile",
    "The same header twice.",
)
_c(
    "csv.missing-header",
    "Missing Header",
    "ada,1\n",
    "invalid",
    "awkward",
    "Rows and no header, under the header-required dialect.",
)
_c(
    "csv.unexpected-delimiter",
    "Unexpected Delimiter",
    "name|age\nada|1\n",
    "malformed",
    "hostile",
    "Pipes where the dialect wants commas.",
)
_c(
    "csv.long-field",
    "Long Field",
    "name\n" + ("a" * 300) + "\n",
    "valid",
    "nightmare",
    "A long field.",
)
_c("csv.unicode", "Unicode Field", "name\ncafé\n", "valid", "awkward", "Non-ASCII text in UTF-8.")
_c("csv.nul", "NUL", "name\na\x00b\n", "invalid", "hostile", "A NUL inside a field.")
_c(
    "csv.broken-quotes",
    "Broken Quotes",
    'name\n"ada\n',
    "malformed",
    "hostile",
    "A quote that never closes.",
)
_c(
    "csv.truncated-quote",
    "Truncated Quote",
    'name\n"ada',
    "malformed",
    "hostile",
    "The file ends inside a quote.",
)
_c(
    "csv.formula",
    "Spreadsheet Formula",
    "name\n=cmd|'/c calc'\n",
    "valid",
    "hostile",
    "Starts with =. Spreadsheet apps may treat this as a formula. This tool does not open it.",
)

fixed(
    "csv.invalid-encoding",
    category=_C,
    name="Invalid Encoding",
    payload=b"name\n\xff\n",
    validity="malformed",
    contract="csv-utf-8",
    risk="hostile",
    tags=("csv", "encoding"),
    explanation="A byte that is not UTF-8.",
    intended="The reader must not guess another encoding.",
    encoding="binary",
)
