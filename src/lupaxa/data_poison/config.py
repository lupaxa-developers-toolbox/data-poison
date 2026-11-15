"""TOML settings. Unknown keys are errors.

Precedence, highest first: command-line flags, recipe, ``--config``, user
file, built-in defaults.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from lupaxa.data_poison.errors import InputError, UsageError
from lupaxa.data_poison.limits import (
    DEFAULT_CAPTURE_BYTES,
    DEFAULT_CONCURRENCY,
    DEFAULT_COUNT,
    DEFAULT_FORMAT,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_TOTAL_BYTES,
    DEFAULT_PROFILE,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TOTAL_TIMEOUT_SECONDS,
)

ALLOWED = {
    "profile",
    "count",
    "seed",
    "format",
    "output_dir",
    "max_bytes",
    "max_depth",
    "max_total_bytes",
    "max_cases",
    "timeout_seconds",
    "total_timeout_seconds",
    "capture_bytes",
    "concurrency",
    "categories",
    "keep_temporary",
    "expect",
}


def user_config_path() -> Path:
    return Path.home() / ".config" / "data-poison" / "config.toml"


def defaults() -> dict[str, Any]:
    return {
        "profile": DEFAULT_PROFILE,
        "count": DEFAULT_COUNT,
        "seed": None,
        "format": DEFAULT_FORMAT,
        "output_dir": None,
        "max_bytes": DEFAULT_MAX_BYTES,
        "max_depth": DEFAULT_MAX_DEPTH,
        "max_total_bytes": DEFAULT_MAX_TOTAL_BYTES,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "total_timeout_seconds": DEFAULT_TOTAL_TIMEOUT_SECONDS,
        "capture_bytes": DEFAULT_CAPTURE_BYTES,
        "concurrency": DEFAULT_CONCURRENCY,
        "categories": None,
        "keep_temporary": False,
        "expect": "by-validity",
    }


def read_toml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"could not read {path}: {exc}") from exc
    try:
        loaded = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise InputError(f"invalid TOML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise InputError(f"{path} must be a TOML table")
    unknown = sorted(set(loaded) - ALLOWED)
    if unknown:
        raise UsageError(f"unknown configuration key {unknown[0]!r} in {path}")
    return loaded


def load_config(explicit: Path | None) -> dict[str, Any]:
    """Merge built-in defaults, the user file, and an explicit file."""
    settings = defaults()
    user = user_config_path()
    if user.is_file():
        settings.update(read_toml(user))
    if explicit is not None:
        settings.update(read_toml(explicit))
    return settings
