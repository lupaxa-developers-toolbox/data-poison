"""Test-case records. Generators return these and never print them."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from lupaxa.data_poison.version import CATALOGUE_VERSION, __version__

VALIDITIES = frozenset({"valid", "invalid", "malformed", "unknown"})


@dataclass
class Case:
    """One generated or mutated input and the reason it exists."""

    case_id: str
    category: str
    generator: str
    payload: bytes
    encoding: str
    validity: str
    contract: str
    explanation: str
    intended: str
    seed: int | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    profile: str | None = None
    mutations: list[str] = field(default_factory=list)
    schema_ref: str | None = None
    expected: str | None = None
    name: str = ""
    risk: str = "awkward"
    tags: list[str] = field(default_factory=list)
    generator_version: str = __version__
    catalogue_version: str = CATALOGUE_VERSION

    def __post_init__(self) -> None:
        if self.validity not in VALIDITIES:
            raise ValueError(f"unknown validity {self.validity!r}")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    def record(self) -> dict[str, Any]:
        """Machine-readable case. Payload bytes are base64, never lossy text."""
        import base64

        text: str | None
        try:
            text = self.payload.decode("utf-8")
        except UnicodeDecodeError:
            text = None
        return {
            "case_id": self.case_id,
            "category": self.category,
            "generator": self.generator,
            "name": self.name or self.generator,
            "payload_encoding": self.encoding,
            "payload_base64": base64.b64encode(self.payload).decode("ascii"),
            "payload_text": text,
            "payload_hex": self.payload.hex(),
            "payload_length": len(self.payload),
            "payload_sha256": self.sha256,
            "validity": self.validity,
            "contract": self.contract,
            "explanation": self.explanation,
            "intended": self.intended,
            "seed": self.seed,
            "parameters": self.parameters,
            "profile": self.profile,
            "mutations": list(self.mutations),
            "schema": self.schema_ref,
            "expected": self.expected,
            "risk": self.risk,
            "tags": list(self.tags),
            "generator_version": self.generator_version,
            "catalogue_version": self.catalogue_version,
        }
