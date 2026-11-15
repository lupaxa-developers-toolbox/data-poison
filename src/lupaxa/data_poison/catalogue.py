"""Built-in poison catalogue.

A case identifier stays stable until its meaning changes. Fixed cases return
the same bytes every time. Parameterised cases may use the seed and limits.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from lupaxa.data_poison.models import Case


@dataclass(frozen=True)
class Options:
    """Knobs a generator may read. Unused knobs stay at their defaults."""

    seed: int | None = None
    profile: str = "awkward"
    max_bytes: int = 1 << 20
    max_depth: int = 32
    minimum: int | None = None
    maximum: int | None = None
    bits: int | None = None
    signed: bool | None = None
    precision: int | None = None
    scale: int | None = None
    numeric_mode: str | None = None
    timezone: str | None = None
    platform: str | None = None
    email_policy: str | None = None
    delimiter: str = ","
    quote: str = '"'
    escape: str | None = None
    lineterminator: str = "\n"
    header: bool = True
    columns: int | None = None
    encoding: str = "utf-8"


Builder = Callable[[random.Random, Options], bytes]


@dataclass(frozen=True)
class Spec:
    """One catalogue entry."""

    identifier: str
    category: str
    name: str
    description: str
    validity: str
    contract: str
    risk: str
    tags: tuple[str, ...]
    explanation: str
    intended: str
    kind: str
    encoding: str
    build: Builder

    def realise(self, rng: random.Random, options: Options, case_id: str) -> Case:
        payload = self.build(rng, options)
        if len(payload) > options.max_bytes:
            payload = payload[: options.max_bytes]
        return Case(
            case_id=case_id,
            category=self.category,
            generator=self.identifier,
            payload=payload,
            encoding=self.encoding,
            validity=self.validity,
            contract=self.contract,
            explanation=self.explanation,
            intended=self.intended,
            seed=options.seed,
            parameters={"kind": self.kind, "max_bytes": options.max_bytes},
            profile=options.profile,
            name=self.name,
            risk=self.risk,
            tags=list(self.tags),
        )


REGISTRY: dict[str, Spec] = {}


def register(spec: Spec) -> Spec:
    """Add a case. Repeating an identifier is a programming error."""
    if spec.identifier in REGISTRY:
        raise RuntimeError(f"duplicate catalogue id {spec.identifier}")
    REGISTRY[spec.identifier] = spec
    return spec


def fixed(
    identifier: str,
    *,
    category: str,
    name: str,
    payload: str | bytes,
    validity: str,
    contract: str,
    risk: str,
    tags: tuple[str, ...],
    explanation: str,
    intended: str,
    encoding: str = "utf-8",
) -> Spec:
    raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")

    def build(_rng: random.Random, _options: Options) -> bytes:
        return raw

    return register(
        Spec(
            identifier=identifier,
            category=category,
            name=name,
            description=explanation,
            validity=validity,
            contract=contract,
            risk=risk,
            tags=tags,
            explanation=explanation,
            intended=intended,
            kind="fixed",
            encoding=encoding,
            build=build,
        )
    )


def parameterised(
    identifier: str,
    *,
    category: str,
    name: str,
    build: Builder,
    validity: str,
    contract: str,
    risk: str,
    tags: tuple[str, ...],
    explanation: str,
    intended: str,
    encoding: str = "utf-8",
) -> Spec:
    return register(
        Spec(
            identifier=identifier,
            category=category,
            name=name,
            description=explanation,
            validity=validity,
            contract=contract,
            risk=risk,
            tags=tags,
            explanation=explanation,
            intended=intended,
            kind="parameterised",
            encoding=encoding,
            build=build,
        )
    )


def load() -> dict[str, Spec]:
    """Import every category module once and return the registry."""
    from lupaxa.data_poison.categories import load_categories

    load_categories()
    return REGISTRY


def lookup(name: str) -> Spec:
    """Resolve a full identifier or a unique suffix such as ``zero-width``."""
    specs = load()
    if name in specs:
        return specs[name]
    matches = [
        spec for key, spec in specs.items() if key.endswith("." + name) or key.endswith(name)
    ]
    exact = [spec for spec in matches if spec.identifier.split(".")[-1] == name]
    chosen = exact or matches
    if len(chosen) == 1:
        return chosen[0]
    if not chosen:
        from lupaxa.data_poison.errors import UsageError

        raise UsageError(f"unknown case {name!r}")
    names = ", ".join(sorted(spec.identifier for spec in chosen))
    from lupaxa.data_poison.errors import UsageError

    raise UsageError(f"case {name!r} is ambiguous: {names}")
