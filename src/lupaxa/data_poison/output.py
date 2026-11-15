"""Render cases. Raw stdout is the payload bytes and nothing else."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from lupaxa.data_poison.errors import UsageError
from lupaxa.data_poison.models import Case


def escape_text(payload: bytes) -> str:
    """A single-line, escaped view. Control characters are not written raw."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.hex()
    return text.encode("unicode_escape").decode("ascii")


def render_text(cases: list[Case]) -> str:
    lines: list[str] = []
    for case in cases:
        lines.append(f"{case.case_id}  {case.validity}  {case.generator}")
        lines.append(f"  contract: {case.contract}")
        lines.append(f"  why: {case.explanation}")
        lines.append(f"  tests: {case.intended}")
        lines.append(f"  payload: {escape_text(case.payload)}")
    return "\n".join(lines) + ("\n" if lines else "")


def render_json(cases: list[Case]) -> str:
    return json.dumps([case.record() for case in cases], indent=2) + "\n"


def render_jsonl(cases: list[Case]) -> str:
    return "".join(json.dumps(case.record(), separators=(",", ":")) + "\n" for case in cases)


def render_encoded(cases: list[Case], kind: str) -> str:
    lines: list[str] = []
    for case in cases:
        if kind == "hex":
            lines.append(case.payload.hex())
        else:
            lines.append(base64.b64encode(case.payload).decode("ascii"))
    return "\n".join(lines) + ("\n" if lines else "")


def write_cases(
    cases: list[Case],
    *,
    fmt: str,
    output: Path | None,
    force: bool,
    frame: str | None = None,
) -> None:
    """Write cases to a file, a directory, or stdout."""
    if fmt == "raw":
        _write_raw(cases, output=output, force=force, frame=frame)
        return
    if fmt == "text":
        body = render_text(cases).encode()
    elif fmt == "json":
        body = render_json(cases).encode()
    elif fmt == "jsonl":
        body = render_jsonl(cases).encode()
    elif fmt in {"hex", "base64"}:
        body = render_encoded(cases, fmt).encode()
    else:
        raise UsageError(f"unknown format {fmt!r}")
    _write_bytes(body, output, force, binary=False)


def _write_bytes(body: bytes, output: Path | None, force: bool, *, binary: bool) -> None:
    if output is None:
        stream = sys.stdout.buffer if binary else sys.stdout.buffer
        stream.write(body)
        stream.flush()
        return
    if output.exists() and not force:
        raise UsageError(f"{output} already exists. Pass --force to overwrite it.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(output)


def _write_raw(cases: list[Case], *, output: Path | None, force: bool, frame: str | None) -> None:
    if len(cases) > 1 and output is None and frame != "length-prefix":
        raise UsageError(
            "multiple raw cases need --output DIRECTORY or --frame length-prefix. "
            "They are not concatenated."
        )
    if output is not None and output.exists() and output.is_dir():
        from lupaxa.data_poison.manifest import write_directory

        write_directory(cases, output, force=force)
        return
    if len(cases) > 1 and output is not None and frame != "length-prefix":
        from lupaxa.data_poison.manifest import write_directory

        write_directory(cases, output, force=force)
        return
    if frame == "length-prefix":
        chunks = b"".join(len(case.payload).to_bytes(4, "big") + case.payload for case in cases)
        _write_bytes(chunks, output, force, binary=True)
        return
    payload = cases[0].payload if cases else b""
    _write_bytes(payload, output, force, binary=True)
