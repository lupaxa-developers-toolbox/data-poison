"""Case manifests. Payload hashes are SHA-256 of the exact bytes."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from lupaxa.data_poison.errors import InputError, IntegrityError, UsageError
from lupaxa.data_poison.models import Case
from lupaxa.data_poison.version import CATALOGUE_VERSION, __version__

MANIFEST_VERSION = 1


def document(cases: list[Case], *, payload_mode: str = "inline") -> dict[str, object]:
    """A manifest. ``inline`` stores base64. ``file`` stores a sibling name."""
    items = []
    for case in cases:
        item: dict[str, object] = {
            "manifest_version": MANIFEST_VERSION,
            "case_id": case.case_id,
            "generator_version": case.generator_version or __version__,
            "catalogue_version": case.catalogue_version or CATALOGUE_VERSION,
            "seed": case.seed,
            "category": case.category,
            "generator": case.generator,
            "validity": case.validity,
            "contract": case.contract,
            "profile": case.profile,
            "parameters": case.parameters,
            "mutations": case.mutations,
            "payload_encoding": case.encoding,
            "payload_length": len(case.payload),
            "payload_sha256": case.sha256,
            "explanation": case.explanation,
            "intended": case.intended,
        }
        if payload_mode == "file":
            item["payload_file"] = f"{case.case_id}.bin"
        else:
            item["payload_base64"] = base64.b64encode(case.payload).decode("ascii")
        items.append(item)
    return {"manifest_version": MANIFEST_VERSION, "cases": items}


def atomic_write(path: Path, body: bytes, *, force: bool) -> None:
    if path.exists() and not force:
        raise UsageError(f"{path} already exists. Pass --force to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(path)


def write_manifest(
    path: Path, cases: list[Case], *, force: bool, payload_mode: str = "inline"
) -> None:
    body = json.dumps(document(cases, payload_mode=payload_mode), indent=2).encode() + b"\n"
    atomic_write(path, body, force=force)


def write_directory(cases: list[Case], directory: Path, *, force: bool) -> None:
    """One ``.bin`` per case plus ``manifest.json``. Existing files need ``--force``."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    if any((directory / f"{case.case_id}.bin").exists() for case in cases) and not force:
        raise UsageError(f"{directory} already has case files. Pass --force to overwrite them.")
    if manifest_path.exists() and not force:
        raise UsageError(f"{manifest_path} already exists. Pass --force to overwrite it.")
    for case in cases:
        target = directory / f"{case.case_id}.bin"
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_bytes(case.payload)
        temporary.replace(target)
    write_manifest(manifest_path, cases, force=True, payload_mode="file")


def _safe_payload_path(base: Path, relative: str) -> Path:
    if relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
        raise InputError(f"payload path {relative!r} escapes the manifest directory")
    path = (base / relative).resolve()
    base_resolved = base.resolve()
    if path != base_resolved and base_resolved not in path.parents:
        raise InputError(f"payload path {relative!r} escapes the manifest directory")
    return path


def load_manifest(path: Path) -> list[tuple[dict[str, object], bytes]]:
    """Return ``(record, payload)`` pairs. Missing or mismatched bytes are errors."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"could not read manifest {path}: {exc}") from exc
    if isinstance(raw, dict) and "cases" in raw:
        records = raw["cases"]
        base = path.parent
    elif isinstance(raw, dict):
        records = [raw]
        base = path.parent
    else:
        raise InputError("a manifest must be an object")
    if not isinstance(records, list):
        raise InputError("manifest cases must be a list")
    loaded: list[tuple[dict[str, object], bytes]] = []
    for record in records:
        if not isinstance(record, dict):
            raise InputError("a manifest case must be an object")
        if "payload_base64" in record:
            try:
                payload = base64.b64decode(str(record["payload_base64"]), validate=True)
            except Exception as exc:
                raise InputError(f"bad payload_base64 in {record.get('case_id')}") from exc
        elif "payload_file" in record:
            payload_path = _safe_payload_path(base, str(record["payload_file"]))
            try:
                payload = payload_path.read_bytes()
            except OSError as exc:
                raise InputError(f"could not read {payload_path}: {exc}") from exc
        else:
            raise InputError(f"case {record.get('case_id')} has no payload")
        digest = hashlib.sha256(payload).hexdigest()
        claimed = record.get("payload_sha256")
        if claimed and claimed != digest:
            raise IntegrityError(
                f"case {record.get('case_id')} hash is {digest}, manifest says {claimed}"
            )
        loaded.append((record, payload))
    return loaded
