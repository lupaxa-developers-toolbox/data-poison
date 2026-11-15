"""Five built-in generation profiles. None of them raise a hard ceiling."""

from __future__ import annotations

from dataclasses import dataclass

from lupaxa.data_poison.errors import UsageError


@dataclass(frozen=True)
class Profile:
    """Selection policy for one named profile."""

    name: str
    summary: str
    validities: frozenset[str]
    risks: frozenset[str]
    mutation_min: int
    mutation_max: int
    complexity: int


PROFILES: dict[str, Profile] = {
    "mild": Profile(
        "mild",
        "Common edges: empty values, whitespace, nulls, and small boundaries.",
        frozenset({"valid"}),
        frozenset({"mild"}),
        0,
        0,
        1,
    ),
    "awkward": Profile(
        "awkward",
        "Valid input that breaks casual assumptions about text, dates, and shape.",
        frozenset({"valid"}),
        frozenset({"mild", "awkward"}),
        0,
        1,
        2,
    ),
    "hostile": Profile(
        "hostile",
        "Invalid types, schema breaks, encoding problems, and malformed syntax.",
        frozenset({"invalid", "malformed"}),
        frozenset({"hostile"}),
        1,
        2,
        3,
    ),
    "nightmare": Profile(
        "nightmare",
        "Combined Unicode, nesting, truncation, and mixed validity.",
        frozenset({"valid", "invalid", "malformed"}),
        frozenset({"awkward", "hostile", "nightmare"}),
        2,
        4,
        4,
    ),
    "apocalypse": Profile(
        "apocalypse",
        "Extreme but bounded size, depth, and parser pressure.",
        frozenset({"valid", "invalid", "malformed"}),
        frozenset({"nightmare", "apocalypse"}),
        3,
        8,
        5,
    ),
}


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        known = ", ".join(PROFILES)
        raise UsageError(f"unknown profile {name!r}. Known profiles: {known}") from exc
