"""Select catalogue cases. The same seed selects the same payloads."""

from __future__ import annotations

import hashlib
import random

from lupaxa.data_poison.catalogue import Options, Spec, load, lookup
from lupaxa.data_poison.errors import LimitError, UsageError
from lupaxa.data_poison.limits import (
    HARD_MAX_BYTES,
    HARD_MAX_CASES,
    HARD_MAX_DEPTH,
    HARD_MAX_TOTAL_BYTES,
)
from lupaxa.data_poison.models import Case
from lupaxa.data_poison.profiles import Profile, get_profile


def _ceil(value: int, hard: int, label: str) -> int:
    if value < 1:
        raise UsageError(f"{label} must be at least 1")
    if value > hard:
        raise LimitError(f"{label} {value} is above the hard ceiling {hard}")
    return value


def case_id(seed: int, sequence: int, generator: str) -> str:
    """An identifier that depends only on the generation context and sequence."""
    digest = hashlib.sha256(f"{seed}:{sequence}:{generator}".encode()).hexdigest()[:8]
    return f"case-{sequence:04d}-{digest}"


def select_specs(
    *,
    profile: Profile,
    categories: list[str] | None,
    validity: str,
    case: str | None,
    tags: list[str] | None = None,
) -> list[Spec]:
    """Return catalogue entries that match the filters, in identifier order."""
    if case:
        spec = lookup(case)
        return [spec]
    specs = list(load().values())
    if categories:
        wanted = {item.strip() for item in categories if item.strip()}
        unknown = wanted - {spec.category for spec in specs}
        if unknown:
            raise UsageError(f"unknown category {sorted(unknown)[0]!r}")
        specs = [spec for spec in specs if spec.category in wanted]
    if validity != "all":
        if validity not in {"valid", "invalid", "malformed"}:
            raise UsageError("validity must be valid, invalid, malformed, or all")
        specs = [spec for spec in specs if spec.validity == validity]
    else:
        specs = [
            spec
            for spec in specs
            if spec.validity in profile.validities or spec.risk in profile.risks
        ]
        specs = [
            spec
            for spec in specs
            if spec.validity in profile.validities and spec.risk in profile.risks
        ]
    if tags:
        wanted_tags = set(tags)
        specs = [spec for spec in specs if wanted_tags.intersection(spec.tags)]
    if not specs:
        raise UsageError("no catalogue cases match those filters")
    return sorted(specs, key=lambda spec: spec.identifier)


def generate(
    *,
    count: int = 1,
    seed: int | None = None,
    profile: str = "awkward",
    categories: list[str] | None = None,
    validity: str = "all",
    case: str | None = None,
    tags: list[str] | None = None,
    max_bytes: int = 1 << 20,
    max_depth: int = 32,
    max_total_bytes: int = 100 << 20,
    minimum: int | None = None,
    maximum: int | None = None,
    bits: int | None = None,
    signed: bool | None = None,
    precision: int | None = None,
    scale: int | None = None,
    numeric_mode: str | None = None,
    timezone: str | None = None,
    platform: str | None = None,
    email_policy: str | None = None,
) -> list[Case]:
    """Build ``count`` cases. A seed makes the list repeatable."""
    count = _ceil(count, HARD_MAX_CASES, "count")
    max_bytes = _ceil(max_bytes, HARD_MAX_BYTES, "max-bytes")
    max_depth = _ceil(max_depth, HARD_MAX_DEPTH, "max-depth")
    max_total_bytes = _ceil(max_total_bytes, HARD_MAX_TOTAL_BYTES, "max-total-bytes")
    chosen = get_profile(profile)
    specs = select_specs(
        profile=chosen, categories=categories, validity=validity, case=case, tags=tags
    )
    actual_seed = seed if seed is not None else random.SystemRandom().randrange(1, 2**31 - 1)
    rng = random.Random(actual_seed)
    order = specs[:]
    rng.shuffle(order)
    options = Options(
        seed=actual_seed,
        profile=profile,
        max_bytes=max_bytes,
        max_depth=max_depth,
        minimum=minimum,
        maximum=maximum,
        bits=bits,
        signed=signed,
        precision=precision,
        scale=scale,
        numeric_mode=numeric_mode,
        timezone=timezone,
        platform=platform,
        email_policy=email_policy,
    )
    cases: list[Case] = []
    total = 0
    for index in range(count):
        spec = order[index % len(order)]
        item = spec.realise(rng, options, case_id(actual_seed, index + 1, spec.identifier))
        item.parameters["variation"] = index // len(order)
        if len(specs) < count and item.parameters["variation"]:
            item.parameters["repeated"] = True
        total += len(item.payload)
        if total > max_total_bytes:
            raise LimitError(
                f"generated payload total would pass {max_total_bytes} bytes at case {index + 1}"
            )
        cases.append(item)
    return cases
