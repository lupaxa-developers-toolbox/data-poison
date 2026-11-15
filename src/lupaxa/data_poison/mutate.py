"""Change a copy of an input. The original file is never opened for writing."""

from __future__ import annotations

import json
import random
from pathlib import Path

from lupaxa.data_poison.errors import InputError, UsageError
from lupaxa.data_poison.models import Case

STRATEGIES = (
    "insert-char",
    "delete-char",
    "replace-char",
    "duplicate-char",
    "insert-whitespace",
    "insert-control",
    "unicode-sub",
    "insert-byte",
    "delete-byte",
    "replace-byte",
    "truncate",
    "remove-field",
    "duplicate-field",
    "type-swap",
    "null-swap",
    "numeric-boundary",
    "string-length",
    "array-insert",
    "array-remove",
    "nest",
    "delimiter",
    "quote",
    "escape",
    "encoding",
)

MODES = ("semantic", "syntax", "bytes")
STYLES = ("single", "combined", "systematic", "random")


def _clip(data: bytes, limit: int) -> bytes:
    return data[:limit]


def apply_one(payload: bytes, name: str, rng: random.Random, mode: str) -> bytes:
    """Apply one named mutation. Syntax and byte modes may break the format."""
    if name not in STRATEGIES:
        raise UsageError(f"unknown mutation {name!r}")
    if name == "insert-char":
        return _text(payload, lambda text: text[:1] + "X" + text[1:])
    if name == "delete-char":
        return _text(payload, lambda text: text[1:] if text else text)
    if name == "replace-char":
        return _text(payload, lambda text: ("Y" + text[1:]) if text else "Y")
    if name == "duplicate-char":
        return _text(payload, lambda text: (text[0] + text) if text else text)
    if name == "insert-whitespace":
        return _text(payload, lambda text: " \n" + text)
    if name == "insert-control":
        return _text(payload, lambda text: "\x01" + text)
    if name == "unicode-sub":
        return _text(
            payload, lambda text: text.replace("a", "\u0430") if "a" in text else text + "\u200b"
        )
    if name == "insert-byte":
        return b"\xff" + payload
    if name == "delete-byte":
        return payload[1:]
    if name == "replace-byte":
        return (b"\xfe" + payload[1:]) if payload else b"\xfe"
    if name == "truncate":
        return payload[: max(0, len(payload) // 2)]
    if name in {
        "remove-field",
        "duplicate-field",
        "type-swap",
        "null-swap",
        "numeric-boundary",
        "string-length",
        "array-insert",
        "array-remove",
        "nest",
    }:
        return _structured(payload, name, mode)
    if name == "delimiter":
        return payload.replace(b",", b"|", 1) if b"," in payload else payload + b","
    if name == "quote":
        return payload.replace(b'"', b"'", 1) if b'"' in payload else payload + b'"'
    if name == "escape":
        return payload.replace(b"\\", b"\\q", 1) if b"\\" in payload else payload + b"\\q"
    if name == "encoding":
        return payload + b"\xff"
    raise UsageError(f"unknown mutation {name!r}")


def _text(payload: bytes, edit) -> bytes:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return b"\xff" + payload
    return edit(text).encode("utf-8")


def _structured(payload: bytes, name: str, mode: str) -> bytes:
    if mode == "bytes":
        return apply_one(payload, "replace-byte", random.Random(0), "bytes")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        if mode == "semantic":
            raise InputError(
                "semantic mutation needs JSON text. Use --mode syntax or --mode bytes."
            ) from exc
        return payload + b"}"
    changed = _edit_json(value, name)
    if mode == "syntax":
        rendered = json.dumps(changed).encode()
        return rendered[:-1] if rendered.endswith(b"}") else rendered + b","
    return json.dumps(changed).encode()


def _leaf(value: object, name: str) -> object:
    if name == "null-swap":
        return None
    if name == "type-swap":
        return 1 if isinstance(value, str) else "x"
    if name == "nest":
        return {"nested": value}
    if name == "string-length":
        return f"{value}xxxx"
    if name == "numeric-boundary":
        return 10**6
    return {"changed": name}


def _edit_json(value: object, name: str) -> object:
    if name == "remove-field" and isinstance(value, dict) and value:
        key = next(iter(value))
        return {item: value[item] for item in value if item != key}
    if name == "duplicate-field" and isinstance(value, dict) and value:
        return json.loads(json.dumps(value))
    if name == "type-swap":
        return "not-the-original-type" if not isinstance(value, str) else 1
    if name == "null-swap":
        return None
    if name == "numeric-boundary" and isinstance(value, int) and not isinstance(value, bool):
        return value + 10**6
    if name == "string-length" and isinstance(value, str):
        return value + ("x" * 32)
    if name == "array-insert" and isinstance(value, list):
        return [None, *value]
    if name == "array-remove" and isinstance(value, list):
        return value[1:]
    if name == "nest":
        return {"nested": value}
    if isinstance(value, dict) and value:
        copy = dict(value)
        key = next(iter(copy))
        copy[key] = _leaf(copy[key], name)
        return copy
    if isinstance(value, list) and value:
        return [_leaf(value[0], name), *value[1:]]
    return _leaf(value, name)


def mutate_payload(
    payload: bytes,
    *,
    count: int,
    seed: int,
    style: str,
    mode: str,
    strategies: list[str] | None,
    max_bytes: int,
    source_name: str,
) -> list[Case]:
    """Return new cases. ``payload`` is the untouched original."""
    if style not in STYLES:
        raise UsageError(f"strategy must be one of: {', '.join(STYLES)}")
    if mode not in MODES:
        raise UsageError(f"mode must be one of: {', '.join(MODES)}")
    names = list(strategies or STRATEGIES)
    unknown = [name for name in names if name not in STRATEGIES]
    if unknown:
        raise UsageError(f"unknown mutation {unknown[0]!r}")
    rng = random.Random(seed)
    cases: list[Case] = []
    for index in range(count):
        chosen = _pick(names, style, rng, index)
        current = payload
        applied: list[str] = []
        for name in chosen:
            current = _clip(apply_one(current, name, rng, mode), max_bytes)
            applied.append(name)
        validity = "malformed" if mode in {"syntax", "bytes"} else "unknown"
        cases.append(
            Case(
                case_id=f"mut-{index + 1:04d}",
                category="mutation",
                generator="mutate",
                payload=current,
                encoding="binary" if mode == "bytes" else "utf-8",
                validity=validity,
                contract=f"mutation-{mode}",
                explanation=f"Applied {', '.join(applied)} to a copy of {source_name}.",
                intended="The original file is unchanged. Compare this payload with it.",
                seed=seed,
                parameters={"style": style, "mode": mode, "index": index},
                mutations=applied,
                name=source_name,
            )
        )
    return cases


def _pick(names: list[str], style: str, rng: random.Random, index: int) -> list[str]:
    if style == "single":
        return [names[index % len(names)] if style == "systematic" else rng.choice(names)]
    if style == "systematic":
        return [names[index % len(names)]]
    if style == "combined":
        width = 2 + (index % 2)
        return [rng.choice(names) for _ in range(width)]
    return [rng.choice(names)]


def mutate_file(
    path: Path,
    *,
    count: int,
    seed: int,
    style: str,
    mode: str,
    strategies: list[str] | None,
    max_bytes: int,
) -> list[Case]:
    before = path.stat().st_mtime_ns
    payload = path.read_bytes()
    cases = mutate_payload(
        payload,
        count=count,
        seed=seed,
        style=style,
        mode=mode,
        strategies=strategies,
        max_bytes=max_bytes,
        source_name=path.name,
    )
    if path.stat().st_mtime_ns != before or path.read_bytes() != payload:
        raise InputError(f"{path} changed during mutation")
    return cases
