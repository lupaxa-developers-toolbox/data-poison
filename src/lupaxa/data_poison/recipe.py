"""TOML recipes. Paths are relative to the recipe file. CLI flags win."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from lupaxa.data_poison.engine import generate
from lupaxa.data_poison.errors import InputError, UsageError
from lupaxa.data_poison.models import Case

RECIPE_KEYS = {"name", "description", "count", "seed", "profile"}
FIELD_KEYS = {"type", "poison", "minimum", "maximum"}
OUTPUT_KEYS = {"format", "path", "manifest"}
POISONS = {"unicode", "whitespace", "length", "boundaries", "wrong-type", "null", "format"}


def load_recipe(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"could not read {path}: {exc}") from exc
    try:
        loaded = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise InputError(f"invalid TOML in {path}: {exc}") from exc
    errors = validate_recipe(loaded, path)
    if errors:
        raise UsageError("; ".join(errors))
    return loaded


def validate_recipe(loaded: dict[str, Any], path: Path) -> list[str]:
    """Return human-readable problems. An empty list means the recipe can run."""
    errors: list[str] = []
    recipe = loaded.get("recipe")
    if not isinstance(recipe, dict):
        return ["[recipe] table is required"]
    unknown = sorted(set(recipe) - RECIPE_KEYS)
    if unknown:
        errors.append(f"unknown recipe key {unknown[0]!r}")
    if "count" in recipe and (not isinstance(recipe["count"], int) or recipe["count"] < 1):
        errors.append("count must be an integer >= 1")
    if "seed" in recipe and not isinstance(recipe["seed"], int):
        errors.append("seed must be an integer")
    fields = loaded.get("fields", {})
    if fields is not None and not isinstance(fields, dict):
        errors.append("fields must be a table")
        fields = {}
    for name, field in fields.items():
        if not isinstance(field, dict):
            errors.append(f"fields.{name} must be a table")
            continue
        extra = sorted(set(field) - FIELD_KEYS)
        if extra:
            errors.append(f"unknown key fields.{name}.{extra[0]}")
        poison = field.get("poison", [])
        if isinstance(poison, str):
            poison = [poison]
        if not isinstance(poison, list) or any(item not in POISONS for item in poison):
            errors.append(f"fields.{name}.poison has an unsupported strategy")
        if "minimum" in field and "maximum" in field and field["minimum"] > field["maximum"]:
            errors.append(f"fields.{name} minimum is above maximum")
    output = loaded.get("output", {})
    if output:
        if not isinstance(output, dict):
            errors.append("output must be a table")
        else:
            extra = sorted(set(output) - OUTPUT_KEYS)
            if extra:
                errors.append(f"unknown output key {extra[0]!r}")
            for key in ("path", "manifest"):
                if key in output and not isinstance(output[key], str):
                    errors.append(f"output.{key} must be a string")
                elif (
                    key in output
                    and Path(output[key]).is_absolute()
                    and ".." in Path(output[key]).parts
                ):
                    errors.append(f"output.{key} is not a usable path")
    schema = loaded.get("schema")
    if isinstance(schema, str):
        target = (path.parent / schema).resolve()
        if not target.is_file():
            errors.append(f"missing schema {schema}")
    elif schema is not None:
        errors.append("schema must be a path string")
    return errors


def _field_value(name: str, field: dict[str, Any], index: int) -> tuple[Any, str]:
    kind = str(field.get("type", "string"))
    poison = field.get("poison", [])
    if isinstance(poison, str):
        poison = [poison]
    choice = poison[index % len(poison)] if poison else "plain"
    if choice == "null":
        return None, "null"
    if choice == "wrong-type":
        return "not-a-number" if kind == "integer" else 1, "wrong-type"
    if choice == "boundaries" and kind == "integer":
        return int(field.get("minimum", 0)) - 1, "boundaries"
    if choice == "unicode":
        return f"{name}\u200b", "unicode"
    if choice == "whitespace":
        return f" {name} ", "whitespace"
    if choice == "length":
        return "a" * 80, "length"
    if choice == "format":
        return "not-an-email", "format"
    if kind == "integer":
        return int(field.get("minimum", 0)), "plain"
    if kind == "email":
        return f"{name}@example.com", "plain"
    return name, "plain"


def execute_recipe(path: Path, *, count: int | None = None, seed: int | None = None) -> list[Case]:
    """Run a recipe. ``count`` and ``seed`` replace the recipe values when set."""
    loaded = load_recipe(path)
    recipe = loaded["recipe"]
    total = count if count is not None else int(recipe.get("count", 1))
    chosen_seed = seed if seed is not None else int(recipe.get("seed", 1))
    profile = str(recipe.get("profile", "awkward"))
    fields = loaded.get("fields") or {}
    cases: list[Case] = []
    if fields:
        for index in range(total):
            body: dict[str, Any] = {}
            notes: list[str] = []
            invalid = False
            for name, field in fields.items():
                value, how = _field_value(str(name), field, index)
                body[str(name)] = value
                notes.append(f"{name}:{how}")
                if how in {"wrong-type", "boundaries", "null", "format"}:
                    invalid = True
            raw = json.dumps(body).encode()
            cases.append(
                Case(
                    case_id=f"recipe-{index + 1:04d}",
                    category="recipe",
                    generator=str(recipe.get("name", path.stem)),
                    payload=raw,
                    encoding="utf-8",
                    validity="invalid" if invalid else "valid",
                    contract="recipe-fields",
                    explanation=recipe.get("description", "") + " " + ", ".join(notes),
                    intended="Field values follow the recipe poison list, one emphasis per case.",
                    seed=chosen_seed,
                    profile=profile,
                    parameters={"index": index},
                    name=str(recipe.get("name", path.name)),
                )
            )
        return cases
    categories = loaded.get("categories")
    if isinstance(categories, str):
        categories = [categories]
    return generate(
        count=total,
        seed=chosen_seed,
        profile=profile,
        categories=categories if isinstance(categories, list) else None,
        validity=str(loaded.get("validity", "all")),
    )
