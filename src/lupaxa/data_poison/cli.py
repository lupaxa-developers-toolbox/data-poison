"""The data-poison command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lupaxa.data_poison.catalogue import load, lookup
from lupaxa.data_poison.config import load_config
from lupaxa.data_poison.engine import generate
from lupaxa.data_poison.errors import DataPoisonError, UsageError
from lupaxa.data_poison.manifest import load_manifest, write_manifest
from lupaxa.data_poison.models import Case
from lupaxa.data_poison.mutate import mutate_file
from lupaxa.data_poison.output import write_cases
from lupaxa.data_poison.profiles import PROFILES, get_profile
from lupaxa.data_poison.recipe import execute_recipe, validate_recipe
from lupaxa.data_poison.report import (
    execution_summary,
    failures,
    generation_summary,
    load_report,
    render_report,
)
from lupaxa.data_poison.runner import run_cases
from lupaxa.data_poison.schema_gen import generate_schema_cases, load_schema
from lupaxa.data_poison.shrink import shrink_payload
from lupaxa.data_poison.version import __version__

GENERATORS = (
    "generate",
    "unicode",
    "numbers",
    "dates",
    "urls",
    "emails",
    "filenames",
    "json",
    "csv",
    "xml",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="data-poison")
    parser.add_argument("--version", action="store_true", help="Print the version and exit.")
    parser.add_argument("--config", type=Path, help="TOML settings file.")
    sub = parser.add_subparsers(dest="subcommand")

    for name in GENERATORS:
        add_generation(sub.add_parser(name, help=f"Generate {name} cases."))
    schema = sub.add_parser("schema", help="Generate cases from a JSON Schema document.")
    schema.add_argument("schema_path", type=Path)
    add_generation(schema)
    schema.add_argument(
        "--mode", default="mixed", choices=["valid", "invalid", "boundary", "mixed"]
    )
    schema.add_argument("--permissive", action="store_true")

    mutate = sub.add_parser("mutate", help="Mutate a copy of a file.")
    mutate.add_argument("source", type=Path)
    add_generation(mutate)
    mutate.add_argument(
        "--strategy", default="single", choices=["single", "combined", "systematic", "random"]
    )
    mutate.add_argument("--mode", default="syntax", choices=["semantic", "syntax", "bytes"])

    recipe = sub.add_parser("recipe", help="Validate or run a TOML recipe.")
    recipe.add_argument("recipe_path", type=Path)
    recipe.add_argument("--validate", action="store_true")
    recipe.add_argument("--seed", type=int)
    recipe.add_argument("--count", type=int)
    recipe.add_argument("--force", action="store_true")

    test = sub.add_parser("test", help="Run a local command against generated cases.")
    add_generation(test)
    test.add_argument("--command", required=True)
    test.add_argument("--input-mode", default="stdin", choices=["stdin", "file", "argument"])
    test.add_argument("--timeout", type=float)
    test.add_argument("--report", type=Path)
    test.add_argument("--expect", default=None)

    shrink = sub.add_parser("shrink", help="Reduce a failing payload.")
    shrink.add_argument("source", type=Path)
    shrink.add_argument("--command", required=True)
    shrink.add_argument("--predicate", default="same-exit")
    shrink.add_argument("--output", type=Path)
    shrink.add_argument("--attempts", type=int, default=200)
    shrink.add_argument("--timeout", type=float, default=2.0)
    shrink.add_argument("--force", action="store_true")

    replay = sub.add_parser("replay", help="Replay a saved manifest.")
    replay.add_argument("manifest", type=Path)
    replay.add_argument("--verify", action="store_true")
    replay.add_argument("--format", default="raw")
    replay.add_argument("--output", type=Path)
    replay.add_argument("--force", action="store_true")

    explain = sub.add_parser("explain", help="Explain one catalogue case.")
    explain.add_argument("name")
    catalogue = sub.add_parser("catalogue", help="List catalogue cases.")
    catalogue.add_argument("--category")
    catalogue.add_argument("--validity")
    catalogue.add_argument("--tag")
    catalogue.add_argument("--format", default="text", choices=["text", "json"])
    profiles = sub.add_parser("profiles", help="List generation profiles.")
    profiles.add_argument("action", nargs="?", choices=["show"])
    profiles.add_argument("name", nargs="?")
    inspect = sub.add_parser("inspect", help="Show a manifest without writing payloads.")
    inspect.add_argument("manifest", type=Path)
    report = sub.add_parser("report", help="Summarise a saved JSON report.")
    report.add_argument("path", type=Path)
    report.add_argument("--format", default="text", choices=["text", "json", "markdown"])
    return parser


def add_generation(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--count", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--profile")
    parser.add_argument("--case")
    parser.add_argument("--category")
    parser.add_argument("--validity", default=None)
    parser.add_argument("--format", dest="fmt")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--max-bytes", type=int)
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--max-total-bytes", type=int)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--frame", choices=["length-prefix"])
    parser.add_argument("--minimum", type=int)
    parser.add_argument("--maximum", type=int)
    parser.add_argument("--bits", type=int)
    parser.add_argument("--signed", action=argparse.BooleanOptionalAction)
    parser.add_argument("--precision", type=int)
    parser.add_argument("--scale", type=int)
    parser.add_argument("--numeric-mode", choices=["integer", "float", "decimal", "text", "json"])
    parser.add_argument("--timezone")
    parser.add_argument("--platform", choices=["windows", "posix", "macos"])
    parser.add_argument("--policy", choices=["conservative", "standards", "ascii"])
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--quote", default='"')
    parser.add_argument("--tag")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version and not args.subcommand:
        print(f"data-poison {__version__}")
        return 0
    if args.version:
        print(f"data-poison {__version__}")
        return 0
    if not args.subcommand:
        parser.error("a command is required")
    try:
        if args.subcommand in {
            "explain",
            "catalogue",
            "profiles",
            "inspect",
            "report",
            "replay",
            "recipe",
            "shrink",
        }:
            return dispatch(args, {})
        settings = load_config(getattr(args, "config", None))
        return dispatch(args, settings)
    except DataPoisonError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


def dispatch(args: argparse.Namespace, settings: dict[str, object]) -> int:
    command = args.subcommand
    if command == "explain":
        return explain_case(args.name)
    if command == "catalogue":
        return show_catalogue(args)
    if command == "profiles":
        return show_profiles(args)
    if command == "inspect":
        return show_manifest(args.manifest)
    if command == "report":
        print(render_report(load_report(args.path), args.format), end="")
        return 0
    if command == "recipe":
        return run_recipe(args)
    if command == "replay":
        return run_replay(args)
    if command == "shrink":
        return run_shrink(args)
    if command == "schema":
        return run_schema(args, settings)
    if command == "mutate":
        return run_mutate(args, settings)
    if command == "test":
        return run_test(args, settings)
    return run_generate(args, settings)


def _opt(
    args: argparse.Namespace, settings: dict[str, object], name: str, default: object = None
) -> object:
    value = getattr(args, name, None)
    if value is None:
        return settings.get(name, default)
    return value


def _as_int(value: object, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _as_float(value: object, default: float) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return default


def run_generate(args: argparse.Namespace, settings: dict[str, object]) -> int:
    if args.quiet and args.verbose:
        raise UsageError("--quiet and --verbose cannot be combined")
    if args.numeric_mode == "float" and args.bits:
        raise UsageError("--bits applies to integer mode, not float")
    category = args.category or (None if args.subcommand == "generate" else args.subcommand)
    if args.subcommand == "json":
        category = "json"
    categories = [part.strip() for part in str(category).split(",")] if category else None
    cases = generate(
        count=_as_int(_opt(args, settings, "count", 1), 1),
        seed=args.seed if args.seed is not None else settings.get("seed"),  # type: ignore[arg-type]
        profile=str(_opt(args, settings, "profile", "awkward")),
        categories=categories,
        validity=args.validity or "all",
        case=args.case,
        tags=[args.tag] if args.tag else None,
        max_bytes=_as_int(_opt(args, settings, "max_bytes", 1 << 20), 1 << 20),
        max_depth=_as_int(_opt(args, settings, "max_depth", 32), 32),
        max_total_bytes=_as_int(_opt(args, settings, "max_total_bytes", 100 << 20), 100 << 20),
        minimum=args.minimum,
        maximum=args.maximum,
        bits=args.bits,
        signed=args.signed,
        precision=args.precision,
        scale=args.scale,
        numeric_mode=args.numeric_mode,
        timezone=args.timezone,
        platform=args.platform,
        email_policy=args.policy,
    )
    if args.subcommand == "emails" and args.policy:
        _apply_email_policy(cases, args.policy)
    if args.verbose:
        print(f"generated {len(cases)} case(s)", file=sys.stderr)
    _emit(cases, args, settings)
    return 0


def _apply_email_policy(cases: list[Case], policy: str) -> None:
    for case in cases:
        if policy == "ascii" and any(byte > 127 for byte in case.payload):
            case.validity = "invalid"
            case.contract = "email-ascii"
            case.explanation += " Rejected by the ascii policy."
        if policy == "conservative" and case.generator in {
            "emails.quoted-local",
            "emails.unicode-local",
            "emails.punctuation",
        }:
            case.validity = "invalid"
            case.contract = "email-conservative"


def _emit(cases: list[Case], args: argparse.Namespace, settings: dict[str, object]) -> None:
    fmt = args.fmt or ("jsonl" if (args.count or 1) > 1 else settings.get("format", "text"))
    write_cases(cases, fmt=str(fmt), output=args.output, force=args.force, frame=args.frame)
    if args.manifest:
        mode = "file" if args.output and args.output.is_dir() else "inline"
        write_manifest(args.manifest, cases, force=args.force, payload_mode=mode)


def run_schema(args: argparse.Namespace, settings: dict[str, object]) -> int:
    schema = load_schema(args.schema_path)
    cases = generate_schema_cases(
        schema,
        count=_as_int(_opt(args, settings, "count", 1), 1),
        seed=_as_int(args.seed if args.seed is not None else settings.get("seed"), 1),
        mode=args.mode,
        strict=not args.permissive,
        schema_name=str(args.schema_path),
        max_bytes=_as_int(_opt(args, settings, "max_bytes", 1 << 20), 1 << 20),
    )
    _emit(cases, args, settings)
    return 0


def run_mutate(args: argparse.Namespace, settings: dict[str, object]) -> int:
    before = args.source.read_bytes()
    cases = mutate_file(
        args.source,
        count=_as_int(_opt(args, settings, "count", 1), 1),
        seed=_as_int(args.seed, 1),
        style=args.strategy,
        mode=args.mode,
        strategies=None,
        max_bytes=_as_int(_opt(args, settings, "max_bytes", 1 << 20), 1 << 20),
    )
    if args.source.read_bytes() != before:
        raise UsageError(f"refusing to continue because {args.source} changed")
    _emit(cases, args, settings)
    return 0


def run_test(args: argparse.Namespace, settings: dict[str, object]) -> int:
    category = args.category
    categories = [part.strip() for part in category.split(",")] if category else None
    cases = generate(
        count=_as_int(_opt(args, settings, "count", 1), 1),
        seed=args.seed if args.seed is not None else settings.get("seed"),  # type: ignore[arg-type]
        profile=str(_opt(args, settings, "profile", "awkward")),
        categories=categories,
        validity=args.validity or "all",
        case=args.case,
        max_bytes=_as_int(_opt(args, settings, "max_bytes", 1 << 20), 1 << 20),
        max_depth=_as_int(_opt(args, settings, "max_depth", 32), 32),
        max_total_bytes=_as_int(_opt(args, settings, "max_total_bytes", 100 << 20), 100 << 20),
    )
    timeout = _as_float(
        args.timeout if args.timeout is not None else settings.get("timeout_seconds"),
        5.0,
    )
    results = run_cases(
        cases,
        command=args.command,
        input_mode=args.input_mode,
        timeout=timeout,
        capture_bytes=_as_int(settings.get("capture_bytes"), 1 << 20),
        expect=args.expect or str(settings.get("expect", "by-validity")),
        keep_temporary=bool(settings.get("keep_temporary", False)),
    )
    body = {
        "generation": generation_summary(cases),
        "execution": execution_summary(results),
        "results": [item.record() for item in results],
    }
    rendered = json.dumps(body, indent=2) + "\n"
    if args.report:
        from lupaxa.data_poison.manifest import atomic_write

        atomic_write(args.report, rendered.encode(), force=args.force)
    else:
        sys.stdout.write(rendered)
    return 5 if failures(results) else 0


def run_recipe(args: argparse.Namespace) -> int:
    if args.validate:
        import tomllib

        loaded = tomllib.loads(args.recipe_path.read_text(encoding="utf-8"))
        errors = validate_recipe(loaded, args.recipe_path)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 2
        print("valid")
        return 0
    cases = execute_recipe(args.recipe_path, count=args.count, seed=args.seed)
    import tomllib

    loaded = tomllib.loads(args.recipe_path.read_text(encoding="utf-8"))
    output = loaded.get("output") if isinstance(loaded.get("output"), dict) else {}
    body = json.dumps([case.record() for case in cases]) + "\n"
    path = output.get("path") if isinstance(output, dict) else None
    if isinstance(path, str) and path:
        from lupaxa.data_poison.manifest import atomic_write

        atomic_write((args.recipe_path.parent / path).resolve(), body.encode(), force=args.force)
    else:
        sys.stdout.write(body)
    manifest = output.get("manifest") if isinstance(output, dict) else None
    if isinstance(manifest, str) and manifest:
        write_manifest(
            (args.recipe_path.parent / manifest).resolve(),
            cases,
            force=args.force,
        )
    return 0


def run_replay(args: argparse.Namespace) -> int:
    loaded = load_manifest(args.manifest)
    if args.verify:
        print(f"verified {len(loaded)} payload(s)")
    cases = []
    for record, payload in loaded:
        raw_seed = record.get("seed")
        cases.append(
            Case(
                case_id=str(record.get("case_id")),
                category=str(record.get("category", "")),
                generator=str(record.get("generator", "replay")),
                payload=payload,
                encoding=str(record.get("payload_encoding", "binary")),
                validity=str(record.get("validity", "unknown")),
                contract=str(record.get("contract", "replay")),
                explanation=str(record.get("explanation", "Saved payload.")),
                intended="Replay the saved bytes.",
                seed=raw_seed if isinstance(raw_seed, int) else None,
                generator_version=str(record.get("generator_version", "")),
                catalogue_version=str(record.get("catalogue_version", "")),
            )
        )
    if not args.verify or args.output or args.format:
        write_cases(cases, fmt=args.format, output=args.output, force=args.force, frame=None)
    return 0


def run_shrink(args: argparse.Namespace) -> int:
    original = args.source.read_bytes()
    report = shrink_payload(
        original,
        command=args.command,
        predicate=args.predicate,
        attempts=args.attempts,
        timeout=args.timeout,
    )
    if args.source.read_bytes() != original:
        raise UsageError(f"{args.source} was modified")
    if args.output:
        from lupaxa.data_poison.manifest import atomic_write

        atomic_write(args.output, report.payload, force=args.force)
    print(json.dumps(report.record(), indent=2))
    return 0 if report.consistent else 1


def explain_case(name: str) -> int:
    spec = lookup(name)
    print(f"{spec.identifier}")
    print(f"name: {spec.name}")
    print(f"category: {spec.category}")
    print(f"validity: {spec.validity}")
    print(f"contract: {spec.contract}")
    print(f"risk: {spec.risk}")
    print(f"kind: {spec.kind}")
    print(f"tags: {', '.join(spec.tags)}")
    print(f"why: {spec.explanation}")
    print(f"tests: {spec.intended}")
    return 0


def show_catalogue(args: argparse.Namespace) -> int:
    specs = list(load().values())
    if args.category:
        specs = [spec for spec in specs if spec.category == args.category]
    if args.validity:
        specs = [spec for spec in specs if spec.validity == args.validity]
    if args.tag:
        specs = [spec for spec in specs if args.tag in spec.tags]
    specs.sort(key=lambda spec: spec.identifier)
    if args.format == "json":
        print(
            json.dumps(
                [
                    {
                        "identifier": spec.identifier,
                        "name": spec.name,
                        "category": spec.category,
                        "validity": spec.validity,
                        "contract": spec.contract,
                        "risk": spec.risk,
                        "tags": list(spec.tags),
                        "kind": spec.kind,
                        "explanation": spec.explanation,
                    }
                    for spec in specs
                ]
            )
        )
        return 0
    for spec in specs:
        print(f"{spec.identifier}\t{spec.validity}\t{spec.contract}")
    return 0


def show_profiles(args: argparse.Namespace) -> int:
    if args.action == "show":
        profile = get_profile(args.name or "")
        print(profile.name)
        print(profile.summary)
        print("validities: " + ", ".join(sorted(profile.validities)))
        print("risks: " + ", ".join(sorted(profile.risks)))
        print(f"mutations: {profile.mutation_min}-{profile.mutation_max}")
        return 0
    for profile in PROFILES.values():
        print(f"{profile.name}\t{profile.summary}")
    return 0


def show_manifest(path: Path) -> int:
    loaded = load_manifest(path)
    for record, payload in loaded:
        print(f"{record.get('case_id')}  {len(payload)} bytes  {record.get('payload_sha256')}")
    return 0
