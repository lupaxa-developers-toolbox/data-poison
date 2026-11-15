"""Run a user-supplied command. This is not a sandbox.

Generated payloads are data. They are never executed. The default is to pass
the payload on stdin, with ``shell=False``.
"""

from __future__ import annotations

import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from lupaxa.data_poison.errors import UsageError
from lupaxa.data_poison.models import Case

CLASSIFICATIONS = (
    "passed",
    "rejected_expected",
    "unexpected_acceptance",
    "unexpected_rejection",
    "crash",
    "timeout",
    "execution_error",
    "inconclusive",
)


@dataclass
class RunResult:
    case_id: str
    classification: str
    exit_code: int | None
    signal: int | None
    duration_seconds: float
    stdout: bytes
    stderr: bytes
    truncated: bool
    expected: str
    observed: str
    command: list[str]
    payload_sha256: str

    def record(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "classification": self.classification,
            "exit_code": self.exit_code,
            "signal": self.signal,
            "duration_seconds": self.duration_seconds,
            "stdout": self.stdout.decode("utf-8", "replace"),
            "stderr": self.stderr.decode("utf-8", "replace"),
            "truncated": self.truncated,
            "expected": self.expected,
            "observed": self.observed,
            "command": self.command,
            "payload_sha256": self.payload_sha256,
        }


def parse_command(command: str) -> list[str]:
    """Split a command. ``{input}`` stays as its own token until a file is ready."""
    parts = shlex.split(command, posix=True)
    if not parts:
        raise UsageError("command is empty")
    return parts


def _classify(
    case: Case, code: int | None, signal: int | None, timed_out: bool, expect: str
) -> tuple[str, str, str]:
    if timed_out:
        return "timeout", "finish within the timeout", "timed out"
    if signal:
        return "crash", "a normal exit", f"signal {signal}"
    if code is None:
        return "execution_error", "a launched process", "the process did not start"
    expected = "accept" if case.validity == "valid" else "reject"
    if expect == "accept":
        expected = "accept"
    elif expect == "reject":
        expected = "reject"
    accepted = code == 0
    if expected == "accept" and accepted:
        return "passed", "exit 0", f"exit {code}"
    if expected == "reject" and not accepted:
        return "rejected_expected", "non-zero exit", f"exit {code}"
    if expected == "accept" and not accepted:
        return "unexpected_rejection", "exit 0", f"exit {code}"
    if expected == "reject" and accepted:
        return "unexpected_acceptance", "non-zero exit", f"exit {code}"
    return "inconclusive", expected, f"exit {code}"


def run_cases(
    cases: list[Case],
    *,
    command: str,
    input_mode: str,
    timeout: float,
    capture_bytes: int,
    expect: str = "by-validity",
    keep_temporary: bool = False,
) -> list[RunResult]:
    """Execute ``command`` once per case. A non-zero exit is not a crash."""
    if input_mode not in {"stdin", "file", "argument"}:
        raise UsageError("input-mode must be stdin, file, or argument")
    template = parse_command(command)
    if (
        input_mode in {"file", "argument"}
        and "{input}" not in template
        and input_mode == "argument"
    ):
        raise UsageError("argument mode needs a {input} placeholder")
    results: list[RunResult] = []
    for case in cases:
        results.append(
            _one(
                case,
                template=template,
                input_mode=input_mode,
                timeout=timeout,
                capture_bytes=capture_bytes,
                expect=expect,
                keep_temporary=keep_temporary,
            )
        )
    return results


def _one(
    case: Case,
    *,
    template: list[str],
    input_mode: str,
    timeout: float,
    capture_bytes: int,
    expect: str,
    keep_temporary: bool,
) -> RunResult:
    temporary: Path | None = None
    argv = list(template)
    stdin_bytes = case.payload if input_mode == "stdin" else None
    if input_mode in {"file", "argument"} or "{input}" in argv:
        with tempfile.NamedTemporaryFile(prefix="data-poison-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(case.payload)
        argv = [str(temporary) if part == "{input}" else part for part in argv]
        if input_mode == "file" and "{input}" not in template:
            argv.append(str(temporary))
    started = time.monotonic()
    timed_out = False
    code: int | None = None
    signal: int | None = None
    out = b""
    err = b""
    truncated = False
    try:
        completed = subprocess.run(
            argv,
            input=stdin_bytes,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        code = completed.returncode
        if code < 0:
            signal = -code
            code = None
        out = completed.stdout
        err = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        out = exc.stdout or b""
        err = exc.stderr or b""
    except OSError as exc:
        err = str(exc).encode()
        classification, expected, observed = "execution_error", "a launched process", str(exc)
        return _result(
            case,
            classification,
            None,
            None,
            started,
            out,
            err,
            False,
            expected,
            observed,
            argv,
            temporary,
            keep_temporary,
        )
    if len(out) > capture_bytes:
        out = out[:capture_bytes]
        truncated = True
    if len(err) > capture_bytes:
        err = err[:capture_bytes]
        truncated = True
    classification, expected, observed = _classify(case, code, signal, timed_out, expect)
    return _result(
        case,
        classification,
        code,
        signal,
        started,
        out,
        err,
        truncated,
        expected,
        observed,
        argv,
        temporary,
        keep_temporary,
    )


def _result(
    case: Case,
    classification: str,
    code: int | None,
    signal: int | None,
    started: float,
    out: bytes,
    err: bytes,
    truncated: bool,
    expected: str,
    observed: str,
    argv: list[str],
    temporary: Path | None,
    keep_temporary: bool,
) -> RunResult:
    if temporary is not None and not keep_temporary:
        temporary.unlink(missing_ok=True)
    return RunResult(
        case_id=case.case_id,
        classification=classification,
        exit_code=code,
        signal=signal,
        duration_seconds=time.monotonic() - started,
        stdout=out,
        stderr=err,
        truncated=truncated,
        expected=expected,
        observed=observed,
        command=argv,
        payload_sha256=case.sha256,
    )
