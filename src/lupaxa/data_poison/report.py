"""Summaries of generation and test runs. There is no quality score."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from lupaxa.data_poison.errors import InputError
from lupaxa.data_poison.models import Case
from lupaxa.data_poison.runner import RunResult


def generation_summary(cases: list[Case]) -> dict[str, Any]:
    validity = Counter(case.validity for case in cases)
    category = Counter(case.category for case in cases)
    return {
        "total_generated": len(cases),
        "valid": validity["valid"],
        "invalid": validity["invalid"],
        "malformed": validity["malformed"],
        "unknown": validity["unknown"],
        "total_bytes": sum(len(case.payload) for case in cases),
        "categories": dict(sorted(category.items())),
        "validities": dict(sorted(validity.items())),
    }


def execution_summary(results: list[RunResult]) -> dict[str, Any]:
    counts = Counter(result.classification for result in results)
    durations = [result.duration_seconds for result in results]
    average = sum(durations) / len(durations) if durations else 0.0
    return {
        "total_executed": len(results),
        "passed": counts["passed"],
        "rejected_expected": counts["rejected_expected"],
        "unexpected_acceptance": counts["unexpected_acceptance"],
        "unexpected_rejection": counts["unexpected_rejection"],
        "crash": counts["crash"],
        "timeout": counts["timeout"],
        "execution_error": counts["execution_error"],
        "inconclusive": counts["inconclusive"],
        "average_duration_seconds": average,
        "maximum_duration_seconds": max(durations, default=0.0),
    }


def failures(results: list[RunResult]) -> list[RunResult]:
    quiet = {"passed", "rejected_expected"}
    return [result for result in results if result.classification not in quiet]


def render_report(body: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(body, indent=2) + "\n"
    if fmt == "markdown":
        return _markdown(body)
    if fmt == "text":
        return _text(body)
    from lupaxa.data_poison.errors import UsageError

    raise UsageError(f"unknown report format {fmt!r}")


def _text(body: dict[str, Any]) -> str:
    lines = [
        f"{key}: {value}" for key, value in body.items() if not isinstance(value, (dict, list))
    ]
    return "\n".join(lines) + "\n"


def _markdown(body: dict[str, Any]) -> str:
    lines = ["# Data Poison Report", ""]
    for key, value in body.items():
        if isinstance(value, dict):
            lines.append(f"## {key}")
            lines.append("")
            for child, count in value.items():
                lines.append(f"- {child}: {count}")
            lines.append("")
        elif not isinstance(value, list):
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def load_report(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"could not read report {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise InputError("a report must be a JSON object")
    return loaded
