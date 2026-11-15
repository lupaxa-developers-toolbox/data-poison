"""Filename strings. These never create files or become output paths."""

from __future__ import annotations

import random

from lupaxa.data_poison.catalogue import Options, fixed, parameterised

_C = "filenames"


def _f(
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
        tags=("filename",),
        explanation=why + " This is a string, not a path the tool will create.",
        intended="Code that uses the name as a filesystem path or a shell argument.",
    )


_f("filenames.empty", "Empty Name", "", "invalid", "posix-filename", "mild", "An empty name.")
_f(
    "filenames.leading-dot",
    "Leading Dot",
    ".hidden",
    "valid",
    "posix-filename",
    "mild",
    "A leading dot. Hidden on POSIX and macOS.",
)
_f(
    "filenames.trailing-dot",
    "Trailing Dot",
    "notes.",
    "valid",
    "posix-filename",
    "awkward",
    "A trailing dot. Windows often strips it.",
)
_f(
    "filenames.trailing-space",
    "Trailing Space",
    "notes ",
    "valid",
    "posix-filename",
    "awkward",
    "A trailing space. Windows often strips it.",
)
_f(
    "filenames.reserved-name",
    "Reserved Windows Name",
    "CON",
    "invalid",
    "windows-filename",
    "hostile",
    "CON is a reserved device name on Windows.",
)
_f(
    "filenames.case-sensitive",
    "Case Sensitive Pair",
    "Readme",
    "valid",
    "posix-filename",
    "awkward",
    "POSIX can keep Readme and readme as two files.",
)
_f(
    "filenames.case-insensitive",
    "Case Insensitive Pair",
    "readme",
    "valid",
    "windows-filename",
    "awkward",
    "On a case-insensitive volume this collides with Readme.",
)
_f(
    "filenames.normalisation-collision",
    "Normalisation Collision",
    "e\u0301",
    "valid",
    "macos-filename",
    "hostile",
    "NFD text can collide with NFC on a normalising volume.",
)
_f(
    "filenames.long-name",
    "Long Name",
    "a" * 255,
    "valid",
    "posix-filename",
    "nightmare",
    "255 bytes, a common name limit.",
)
_f(
    "filenames.long-path",
    "Long Path",
    "/".join(["dir"] * 40) + "/file",
    "valid",
    "posix-path",
    "apocalypse",
    "A deep relative path.",
)
_f(
    "filenames.multi-ext",
    "Multiple Extensions",
    "archive.tar.gz",
    "valid",
    "posix-filename",
    "mild",
    "Two extensions.",
)
_f("filenames.no-ext", "No Extension", "README", "valid", "posix-filename", "mild", "No dot.")
_f(
    "filenames.embedded-separator",
    "Embedded Separator",
    "a/b",
    "invalid",
    "posix-filename",
    "hostile",
    "A slash is a path separator, not part of one name.",
)
_f(
    "filenames.relative",
    "Relative Components",
    "a/./b",
    "valid",
    "posix-path",
    "awkward",
    "A dot segment.",
)
_f(
    "filenames.parent",
    "Parent Directory",
    "../secret",
    "valid",
    "posix-path",
    "hostile",
    "A parent segment. Dangerous if joined to a base without a check.",
)
_f(
    "filenames.absolute",
    "Absolute Path",
    "/etc/passwd",
    "valid",
    "posix-path",
    "hostile",
    "An absolute path.",
)
_f(
    "filenames.mixed-separators",
    "Mixed Separators",
    "a\\b/c",
    "valid",
    "windows-path",
    "awkward",
    "Both separators. POSIX treats the backslash as a character.",
)
_f(
    "filenames.nul",
    "NUL",
    "a\x00b",
    "malformed",
    "posix-filename",
    "hostile",
    "A NUL cannot appear in a path on POSIX or Windows.",
)
_f(
    "filenames.controls",
    "Control Characters",
    "a\nb",
    "invalid",
    "posix-filename",
    "hostile",
    "A newline in a name.",
)
_f(
    "filenames.option-like",
    "Option Shaped Name",
    "--force",
    "valid",
    "posix-filename",
    "hostile",
    "A name that looks like a flag if it is passed unquoted.",
)
_f(
    "filenames.hidden",
    "Hidden Convention",
    ".git",
    "valid",
    "posix-filename",
    "mild",
    "A conventional hidden name.",
)
_f(
    "filenames.reserved-character",
    "Reserved Character",
    "a:b",
    "invalid",
    "windows-filename",
    "hostile",
    "A colon is reserved on Windows.",
)


def _platform(rng: random.Random, options: Options) -> bytes:
    platform = (options.platform or "posix").lower()
    samples = {"windows": "AUX", "posix": "a/b", "macos": "e\u0301"}
    if platform not in samples:
        from lupaxa.data_poison.errors import UsageError

        raise UsageError("platform must be windows, posix, or macos")
    return samples[platform].encode()


parameterised(
    "filenames.platform-sample",
    category=_C,
    name="Platform Sample",
    build=_platform,
    validity="invalid",
    contract="selected-platform",
    risk="hostile",
    tags=("filename", "platform"),
    explanation=(
        "AUX on Windows, a slash on POSIX, or an NFD name on macOS. Default platform is posix."
    ),
    intended="A check written for one operating system used on another.",
)
