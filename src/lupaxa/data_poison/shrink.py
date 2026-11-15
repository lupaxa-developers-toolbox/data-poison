"""Shrink a failing payload. The result is smaller when possible, not proven minimal."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from lupaxa.data_poison.errors import UsageError
from lupaxa.data_poison.models import Case
from lupaxa.data_poison.runner import parse_command, run_cases

PREDICATES = ("same-exit", "same-signal", "timeout", "nonzero")


@dataclass
class ShrinkReport:
    original_size: int
    final_size: int
    attempts: int
    reductions: int
    predicate: str
    consistent: bool
    payload: bytes

    @property
    def reduction_percent(self) -> float:
        if self.original_size == 0:
            return 0.0
        return 100.0 * (self.original_size - self.final_size) / self.original_size

    def record(self) -> dict[str, object]:
        return {
            "original_size": self.original_size,
            "final_size": self.final_size,
            "reduction_percent": round(self.reduction_percent, 2),
            "attempts": self.attempts,
            "reductions": self.reductions,
            "predicate": self.predicate,
            "consistent": self.consistent,
            "note": "Shrinking is heuristic and is not a proof of the smallest input.",
        }


def _fails(
    payload: bytes, command: str, predicate: str, timeout: float, origin: int | None
) -> bool:
    case = Case(
        case_id="shrink",
        category="shrink",
        generator="shrink",
        payload=payload,
        encoding="binary",
        validity="unknown",
        contract="shrink-predicate",
        explanation="Candidate.",
        intended="Preserve the selected failure.",
    )
    result = run_cases(
        cases=[case], command=command, input_mode="stdin", timeout=timeout, capture_bytes=4096
    )[0]
    if predicate == "timeout":
        return result.classification == "timeout"
    if predicate == "nonzero":
        return result.exit_code not in (None, 0)
    if predicate == "same-signal":
        return result.signal is not None and result.signal == origin
    if predicate == "same-exit":
        return result.exit_code == origin and origin not in (None, 0)
    raise UsageError(f"unknown predicate {predicate!r}")


def shrink_payload(
    payload: bytes,
    *,
    command: str,
    predicate: str = "same-exit",
    attempts: int = 200,
    timeout: float = 2.0,
) -> ShrinkReport:
    """Reduce ``payload`` while ``command`` still fails the same way."""
    if predicate not in PREDICATES:
        raise UsageError(f"predicate must be one of: {', '.join(PREDICATES)}")
    parse_command(command)
    probe = Case(
        case_id="origin",
        category="shrink",
        generator="shrink",
        payload=payload,
        encoding="binary",
        validity="unknown",
        contract="shrink-predicate",
        explanation="Original.",
        intended="Establish the failure to preserve.",
    )
    first = run_cases(
        cases=[probe], command=command, input_mode="stdin", timeout=timeout, capture_bytes=4096
    )[0]
    origin = first.signal if predicate == "same-signal" else first.exit_code
    if not _fails(payload, command, predicate, timeout, origin):
        return ShrinkReport(len(payload), len(payload), 1, 0, predicate, False, payload)
    cache: dict[str, bool] = {}
    used = 0
    reductions = 0

    def interesting(candidate: bytes) -> bool:
        nonlocal used
        if used >= attempts:
            return False
        digest = hashlib.sha256(candidate).hexdigest()
        if digest in cache:
            return cache[digest]
        used += 1
        answer = _fails(candidate, command, predicate, timeout, origin)
        cache[digest] = answer
        return answer

    current = payload
    granularity = 2
    while used < attempts and len(current) >= 2 and granularity <= len(current):
        size = len(current)
        chunk = max(1, size // granularity)
        reduced = False
        start = 0
        while start < size and used < attempts:
            stop = min(size, start + chunk)
            candidate = current[:start] + current[stop:]
            if candidate and interesting(candidate):
                current = candidate
                reductions += 1
                reduced = True
                granularity = max(2, granularity - 1)
                break
            start = stop
        if not reduced:
            if granularity >= len(current):
                break
            granularity = min(len(current), granularity * 2)
    second = interesting(current)
    return ShrinkReport(
        original_size=len(payload),
        final_size=len(current),
        attempts=used,
        reductions=reductions,
        predicate=predicate,
        consistent=second,
        payload=current,
    )
