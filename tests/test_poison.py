"""Catalogue, determinism, formats, schema, mutation, runner, and shrink."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from defusedxml import ElementTree
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from lupaxa.data_poison.catalogue import load
from lupaxa.data_poison.cli import main
from lupaxa.data_poison.config import read_toml
from lupaxa.data_poison.engine import generate
from lupaxa.data_poison.errors import InputError, LimitError, UsageError
from lupaxa.data_poison.manifest import load_manifest, write_manifest
from lupaxa.data_poison.schema_gen import generate_schema_cases


def test_every_catalogue_case_has_a_purpose() -> None:
    specs = load()
    assert len(specs) >= 100
    for spec in specs.values():
        case = spec.realise(__import__("random").Random(1), _options(), "case-0001")
        assert case.payload is not None
        assert case.explanation
        assert case.intended
        assert case.contract
        assert case.validity in {"valid", "invalid", "malformed", "unknown"}


def _options():
    from lupaxa.data_poison.catalogue import Options

    return Options(seed=1, max_bytes=4096, max_depth=8)


def test_same_seed_is_the_same_payload() -> None:
    first = generate(count=5, seed=12345, profile="nightmare", categories=["unicode"])
    second = generate(count=5, seed=12345, profile="nightmare", categories=["unicode"])
    assert [case.payload for case in first] == [case.payload for case in second]
    assert [case.case_id for case in first] == [case.case_id for case in second]


def test_valid_json_parses_and_malformed_does_not() -> None:
    valid = generate(count=20, seed=1, categories=["json"], validity="valid")
    malformed = generate(count=20, seed=1, categories=["json"], validity="malformed")
    assert valid and malformed
    for case in valid:
        if case.encoding == "binary":
            continue
        json.loads(case.payload.decode("utf-8"))
    for case in malformed:
        with pytest.raises((json.JSONDecodeError, UnicodeDecodeError)):
            json.loads(case.payload.decode("utf-8"))


def test_valid_xml_parses_and_malformed_does_not() -> None:
    valid = generate(count=10, seed=1, categories=["xml"], validity="valid")
    malformed = generate(count=5, seed=1, categories=["xml"], validity="malformed")
    for case in valid:
        if case.encoding == "binary":
            continue
        ElementTree.fromstring(case.payload)
    for case in malformed:
        with pytest.raises(ElementTree.ParseError):
            ElementTree.fromstring(case.payload)


def test_unicode_combining_case_contains_the_mark() -> None:
    cases = generate(count=1, seed=1, case="unicode.combining")
    assert "\u0301" in cases[0].payload.decode("utf-8")


def test_manifest_round_trip(tmp_path: Path) -> None:
    cases = generate(count=2, seed=7, categories=["numbers"], validity="valid")
    path = tmp_path / "cases.json"
    write_manifest(path, cases, force=False)
    loaded = load_manifest(path)
    assert loaded[0][1] == cases[0].payload
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(cases[0].sha256, "0" * 64), encoding="utf-8")
    with pytest.raises(Exception, match="hash"):
        load_manifest(path)


def test_mutate_leaves_the_original(tmp_path: Path) -> None:
    source = tmp_path / "customer.json"
    source.write_text('{"name":"ada"}', encoding="utf-8")
    assert main(["mutate", str(source), "--count", "3", "--seed", "1", "--strategy", "single"]) == 0
    assert source.read_text(encoding="utf-8") == '{"name":"ada"}'


def test_recipe_validation(tmp_path: Path) -> None:
    recipe = tmp_path / "customer.toml"
    recipe.write_text(
        "\n".join(
            [
                "[recipe]",
                'name = "Customer"',
                "count = 2",
                "seed = 5",
                "[fields.age]",
                'type = "integer"',
                "minimum = 0",
                "maximum = 120",
                'poison = ["boundaries", "null"]',
                "[output]",
                'format = "jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    assert main(["recipe", str(recipe), "--validate"]) == 0
    assert main(["recipe", str(recipe)]) == 0


def test_schema_valid_and_invalid(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 8},
            "age": {"type": "integer", "minimum": 0, "maximum": 120},
        },
        "required": ["name", "age"],
        "additionalProperties": False,
    }
    path = tmp_path / "customer.schema.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    valid = generate_schema_cases(
        schema, count=4, seed=1, mode="valid", strict=True, schema_name=str(path), max_bytes=10000
    )
    invalid = generate_schema_cases(
        schema, count=4, seed=1, mode="invalid", strict=True, schema_name=str(path), max_bytes=10000
    )
    validator = Draft202012Validator(schema)
    for case in valid:
        validator.validate(json.loads(case.payload))
        assert case.validity == "valid"
    for case in invalid:
        with pytest.raises(ValidationError):
            validator.validate(json.loads(case.payload))
        assert case.validity == "invalid"


def test_schema_rejects_remote_ref() -> None:
    schema = {"$ref": "https://example.com/schema.json"}
    with pytest.raises(InputError, match="unsupported"):
        generate_schema_cases(
            schema, count=1, seed=1, mode="valid", strict=True, schema_name="remote", max_bytes=1000
        )


def test_runner_classifies_accept_and_reject(tmp_path: Path) -> None:
    program = tmp_path / "check.py"
    program.write_text(
        "import sys\ndata = sys.stdin.buffer.read()\nsys.exit(0 if data.startswith(b'{') else 1)\n",
        encoding="utf-8",
    )
    code = main(
        [
            "test",
            "--command",
            f"python3 {program}",
            "--category",
            "json",
            "--case",
            "json.empty-object",
            "--count",
            "1",
            "--seed",
            "1",
        ]
    )
    assert code == 0


def test_shrink_preserves_failure_and_original(tmp_path: Path) -> None:
    source = tmp_path / "fail.bin"
    source.write_bytes(b"KEEP" + b"x" * 40)
    program = tmp_path / "need.py"
    program.write_text(
        "import sys\ndata = sys.stdin.buffer.read()\nsys.exit(1 if b'KEEP' in data else 0)\n",
        encoding="utf-8",
    )
    out = tmp_path / "small.bin"
    code = main(
        [
            "shrink",
            str(source),
            "--command",
            f"python3 {program}",
            "--predicate",
            "nonzero",
            "--output",
            str(out),
            "--attempts",
            "80",
        ]
    )
    assert code == 0
    assert source.read_bytes().startswith(b"KEEP")
    assert out.read_bytes().startswith(b"KEEP") or b"KEEP" in out.read_bytes()
    assert len(out.read_bytes()) < len(source.read_bytes())


def test_raw_multiple_cases_need_a_directory(tmp_path: Path) -> None:
    code = main(["unicode", "--count", "2", "--seed", "1", "--format", "raw"])
    assert code == 2
    directory = tmp_path / "out"
    assert (
        main(
            [
                "unicode",
                "--count",
                "2",
                "--seed",
                "1",
                "--format",
                "raw",
                "--output",
                str(directory),
            ]
        )
        == 0
    )
    assert (directory / "manifest.json").is_file()


def test_unknown_config_key(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("mystery = 1\n", encoding="utf-8")
    with pytest.raises(UsageError):
        read_toml(path)


def test_hard_ceiling() -> None:
    with pytest.raises(LimitError):
        generate(count=1, max_bytes=2**30)


def test_cli_version() -> None:
    assert main(["--version"]) == 0


def test_explain_and_catalogue() -> None:
    assert main(["explain", "unicode.zero-width"]) == 0
    assert main(["catalogue", "--category", "dates"]) == 0
    assert main(["profiles", "show", "nightmare"]) == 0
