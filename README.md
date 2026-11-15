<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Developers Toolbox" />
  </a>
</p>

<h1 align="center">Data Poison</h1>

Generate, mutate, explain, test, and minimise difficult or malformed data.
Every case says what it is, why it is unusual, and which behaviour it is
meant to expose. The same seed produces the same bytes.

The PyPI name is `lupaxa-data-poison`. The import path is
`lupaxa.data_poison`. The console script is `data-poison`. `lupaxa` is a
namespace package — there is no `lupaxa/__init__.py`.

Public names: `generate`, `mutate_payload`, `Case`, `__version__`,
`get_version()`.

## Install

```bash
pip install lupaxa-data-poison
```

Requires Python 3.11 or newer. Runtime dependencies are `jsonschema` and
`defusedxml`. The tool does not use the network.

```bash
python -m lupaxa.data_poison --version
```

## Quick Start

```bash
data-poison unicode --count 5 --seed 12345
data-poison explain unicode.zero-width
data-poison catalogue --category json --validity malformed
```

## What it Does

A case is a payload plus metadata: identifier, category, generator,
encoding, validity, contract, explanation, intended behaviour, seed, and
the generator and catalogue versions. Payloads may be text or raw bytes.

Generation reads a built-in catalogue. Profiles choose which risks and
validity classes are in play. `--case` asks for one named case. Mutation
changes a copy of a file. A recipe repeats a job from TOML. `test` runs a
program you name. `shrink` shortens a payload that still fails the same
way. `replay` returns saved bytes and checks their SHA-256.

> **Note:** Shrinking is a heuristic. A smaller payload is not a proof
> that no smaller one exists. URL and email checks are syntax policies.
> They do not mean a host or a mailbox exists.

## Validity

| Class       | Meaning                                                              |
| ----------- | -------------------------------------------------------------------- |
| `valid`     | Allowed by the named contract, and still a likely surprise.          |
| `invalid`   | Representable, but it breaks a declared rule in that contract.       |
| `malformed` | It breaks the syntax or encoding of that contract.                   |
| `unknown`   | The tool will not guess. This is a qualification, not a fourth mode. |

The contract is part of the case. A newline can be valid text and invalid
for one field. JSON `NaN` is malformed JSON and a normal IEEE-754 value
when the contract is a Python float.

## Command Line

| Command     | Purpose                                      |
| ----------- | -------------------------------------------- |
| `generate`  | Cases from the whole catalogue               |
| `unicode`   | Text and encoding edges                      |
| `numbers`   | Integers, floats, decimals, and JSON numbers |
| `dates`     | Calendar and timezone edges                  |
| `urls`      | URL syntax, with no DNS                      |
| `emails`    | Address syntax, with no SMTP                 |
| `filenames` | Name strings, never created on disk          |
| `json`      | Valid and malformed JSON documents           |
| `csv`       | One strict comma dialect                     |
| `xml`       | XML with entity expansion disabled           |
| `schema`    | A documented JSON Schema subset              |
| `mutate`    | A copy of an existing file                   |
| `recipe`    | A TOML job                                   |
| `test`      | A local program, not a sandbox               |
| `shrink`    | A smaller payload with the same failure      |
| `replay`    | Saved bytes and a hash check                 |
| `explain`   | One catalogue entry                          |
| `catalogue` | Filter the catalogue                         |
| `profiles`  | The five profiles                            |
| `inspect`   | A manifest, without dumping payloads         |
| `report`    | A saved test report                          |

`--help` works on the root command and on every subcommand. `--version`
prints `data-poison x.y.z`.

| Flag                    | Default                                  | Meaning                                                                   |
| ----------------------- | ---------------------------------------- | ------------------------------------------------------------------------- |
| `--count`               | `1`                                      | How many cases.                                                           |
| `--seed`                | chosen and stored                        | Repeatable selection.                                                     |
| `--profile`             | `awkward`                                | `mild`, `awkward`, `hostile`, `nightmare`, or `apocalypse`.               |
| `--case`                |                                          | One catalogue identifier or a unique suffix.                              |
| `--category`            | the command name                         | Comma-separated categories for `generate` and `test`.                     |
| `--validity`            | profile                                  | `valid`, `invalid`, `malformed`, or `all`.                                |
| `--format`              | `text`, or `jsonl` when count is above 1 | `text`, `json`, `jsonl`, `raw`, `hex`, `base64`.                          |
| `--output`              | stdout                                   | File or directory.                                                        |
| `--manifest`            |                                          | JSON manifest path.                                                       |
| `--max-bytes`           | 1 MiB                                    | Per-case ceiling, hard stop 32 MiB.                                       |
| `--max-depth`           | 32                                       | Nesting ceiling, hard stop 128.                                           |
| `--max-total-bytes`     | 100 MiB                                  | Run ceiling, hard stop 512 MiB.                                           |
| `--quiet` / `--verbose` | quiet                                    | Errors still go to stderr.                                                |
| `--force`               | off                                      | Overwrite an existing output file.                                        |
| `--frame length-prefix` |                                          | Several raw payloads on one stream: 4-byte big-endian length, then bytes. |

A single `--format raw` write is the payload bytes only. No newline and no
label. Several raw cases need a directory or `--frame length-prefix`.

| Exit  | Meaning                                                    |
| ----- | ---------------------------------------------------------- |
| `0`   | Finished.                                                  |
| `1`   | Operational error, or shrink could not keep the failure.   |
| `2`   | Bad arguments or configuration.                            |
| `3`   | Input, parse, or validation error.                         |
| `4`   | A safety ceiling.                                          |
| `5`   | The test run found a crash, timeout, or unexpected result. |
| `6`   | Replay hash or integrity failure.                          |
| `130` | Interrupted.                                               |

Expected invalid data does not make generation fail. A non-zero program
exit is a rejection, not a crash. A crash is a signal.

## Profiles

`mild` is empty values, whitespace, and small boundaries. `awkward` is
valid input that still surprises. `hostile` is invalid and malformed.
`nightmare` mixes those and stacks mutations in the profile description.
`apocalypse` pushes size and depth up to the ceilings you set, never past
the hard caps.

```bash
data-poison profiles
data-poison profiles show nightmare
data-poison generate --profile apocalypse --count 10 --seed 1
```

## Catalogue

Identifiers stay put until the meaning changes. `unicode.zero-width` is
the stable name. Fixed cases return the same bytes every time.
Parameterised cases may use the seed and the limits.

```bash
data-poison catalogue
data-poison catalogue --category unicode
data-poison catalogue --validity malformed
data-poison catalogue --tag boundary
data-poison explain unicode.normalisation.nfc-nfd
```

Text and JSON catalogue output are both supported.

## Unicode

The catalogue includes empty strings, whitespace, newlines, non-breaking
and zero-width characters, joiners, combining marks, NFC/NFD and
NFKC/NFKD samples, bidi controls, right-to-left text, confusables, emoji
sequences, skin tones, regional indicators, variation selectors,
supplementary-plane characters, a noncharacter, long strings, NUL and
ASCII controls, line and paragraph separators, Turkish I, sharp S, mixed
scripts, and invalid, truncated, and surrogate UTF-8.

Confusable characters are not treated as the same character. Normalisation
form names are NFC, NFD, NFKC, and NFKD. Explanations name code points
when Python knows the name.

```bash
data-poison unicode --count 20 --seed 1
data-poison unicode --case zero-width
data-poison unicode --profile nightmare --count 5
```

## Numbers

Modes are integer, float, decimal, text, and JSON. `--bits` and
`--signed` / `--no-signed` apply to integer bounds. `--minimum` and
`--maximum` apply to the outside-range case. `--precision` and `--scale`
are accepted for decimal work and ignored by cases that do not use them.
`--bits` with `--numeric-mode float` is an error.

JSON number cases never emit `NaN` or `Infinity`. Those tokens exist as
malformed JSON and, separately, as IEEE-754 text.

```bash
data-poison numbers --case float-precision
data-poison numbers --case integer-bounds --bits 32 --signed
data-poison numbers --case outside-range --minimum 0 --maximum 100
data-poison numbers --case json-overflow
```

## Dates

Leap day, non-leap 29 February, month and year boundaries, midnight, hour
24, offsets, fractional seconds, ISO and RFC 3339 samples, epoch values,
date-only and time-only values, and naive versus aware timestamps are in
the catalogue.

`--timezone` selects an IANA zone for `dates.dst-gap` and
`dates.dst-overlap`. The gap and overlap come from that zone's 2024
transitions. The defaults are `Europe/London` and `America/New_York`. A
zone with no such transition, or a machine without timezone data, is an
error rather than a made-up clock change.

```bash
data-poison dates --case leap-year
data-poison dates --case dst-gap --timezone Europe/London
data-poison dates --case dst-overlap --timezone America/New_York
```

## URLs

No DNS and no HTTP. The contracts are `absolute-url`,
`relative-reference`, and `url-syntax`. A syntactically absolute URL can
still be one an application should reject, such as `javascript:`.

```bash
data-poison urls --count 10 --seed 1
data-poison urls --case percent-encoding
data-poison urls --case ipv6
```

## Emails

Policies are `conservative` (everyday ASCII, plus-tags allowed),
`standards` (a documented subset that allows a quoted local part and
Unicode), and `ascii` (non-ASCII is invalid). None of them send mail.

```bash
data-poison emails --profile hostile --count 5 --seed 1
data-poison emails --case unicode-local --policy ascii
data-poison emails --case quoted-local --policy standards
```

## Filenames

Cases are strings. They are not created, and they are not used as the
`--output` path. Contracts cover POSIX names, POSIX paths, Windows names,
Windows paths, and macOS normalisation. `--platform` is `posix`,
`windows`, or `macos`.

```bash
data-poison filenames --platform windows --case reserved-name
data-poison filenames --case unicode-collision
```

## JSON, CSV, and XML

Valid JSON is parsed by the standard library. Malformed JSON is emitted
as raw text and is not repaired. Duplicate keys are valid syntax and an
interoperability hazard, not a syntax error.

CSV uses comma, double quote, and LF. A header is part of that contract.
Values that start with `=`, `+`, `-`, or `@` are flagged because a
spreadsheet may treat them as formulas. This tool does not open them.

XML parsing uses `defusedxml`. External entities and expansion are not
resolved. The entity-expansion fixture is a few characters, not a large
bomb. Deep nesting stops at `--max-depth`.

```bash
data-poison json --validity valid --count 10 --seed 1
data-poison json --validity malformed --count 5 --seed 1
data-poison json --case duplicate-keys
data-poison csv --case embedded-newline
data-poison xml --case mismatched-tags
data-poison xml --case entity-expansion
```

## Schema

`schema` reads a local JSON Schema document. The supported Draft 2020-12
subset is `type`, `properties`, `required`, boolean `additionalProperties`,
`items`, size and length bounds, `minimum` and `maximum` including the
exclusive forms, `multipleOf`, `enum`, `const`, a short `pattern`,
`format` of `email`, `date-time`, `uri`, `uuid`, `ipv4`, and `ipv6`,
property counts, `uniqueItems`, and local `$defs` / `$ref`.

Anything else that would change validation is an error in the default
strict mode. `--permissive` still generates and marks validity `unknown`.
Remote `$ref` is never fetched.

Modes are `valid`, `invalid`, `boundary`, and `mixed`. Invalid cases aim
at one constraint. Each case records the expected result, the validator
result, and the constraint name.

```bash
data-poison schema customer.schema.json --count 20 --seed 1
data-poison schema customer.schema.json --mode boundary
```

## Recipes

Paths in a recipe are relative to the recipe file. Unknown keys, bad
types, a minimum above a maximum, and a missing schema path fail
validation. `--count` and `--seed` on the command replace the recipe.

```toml
[recipe]
name = "Customer Registration"
description = "Difficult customer fields"
count = 20
seed = 12345
profile = "nightmare"

[fields.username]
type = "string"
poison = ["unicode", "whitespace", "length"]

[fields.age]
type = "integer"
minimum = 0
maximum = 120
poison = ["boundaries", "wrong-type", "null"]

[fields.email]
type = "email"
poison = ["format"]

[output]
format = "jsonl"
```

```bash
data-poison recipe customer.toml --validate
data-poison recipe customer.toml --seed 999
```

Field poison values are `unicode`, `whitespace`, `length`, `boundaries`,
`wrong-type`, `null`, and `format`.

## Mutation

`mutate` reads a file and writes new payloads. It does not open the
source for writing. Modes are `semantic` (JSON shape kept, then
re-serialised), `syntax` (deliberately broken), and `bytes`. Strategies
are `single`, `combined`, `systematic`, and `random`.

The strategy names include character and byte edits, whitespace and
controls, Unicode substitution, truncation, field removal and
duplication, type and null swaps, numeric and length changes, array
edits, nesting, and delimiter, quote, escape, and encoding corruption.

```bash
data-poison mutate customer.json --strategy single --count 10 --seed 1
data-poison mutate customer.json --mode syntax --output mutations/
data-poison mutate input.bin --mode bytes --count 5 --seed 1
```

## Test Runner

You name the command. The default delivery is stdin. `--input-mode file`
writes a temporary file and deletes it afterwards. `{input}` is replaced
as one argument. The command is split with `shlex` and run with
`shell` left off, so the payload is not a shell script.

A timeout, a captured-output cap, and the case limit apply. A non-zero
exit is `rejected_expected` when the case is invalid or malformed, and
`unexpected_rejection` when the case is valid. Exit 0 on invalid input is
`unexpected_acceptance`. A signal is `crash`. Expiry is `timeout`. A
missing program is `execution_error`. Anything the oracle cannot judge is
`inconclusive`.

```bash
data-poison test --command "./validate-customer" --category json --count 20 --seed 1
data-poison test --command "./parser {input}" --input-mode file --count 5 --seed 1
```

> **Note:** The runner is not a security sandbox. It runs the command you
> typed, with your user privileges.

## Shrinking

`shrink` keeps a predicate: `same-exit`, `same-signal`, `timeout`, or
`nonzero`. It deletes byte ranges, caches candidates by SHA-256, and
stops at `--attempts`. The original file is only read. The report gives
the old size, the new size, the reduction, and the attempt count, and it
says the result is not mathematically minimal.

```bash
data-poison shrink failing.bin --command "./validate-json" --predicate same-exit --output minimal.bin
```

## Replay and Manifests

A manifest records version, case id, seed, category, generator, validity,
contract, mutations, encoding, length, and SHA-256. Payloads are inline
base64 or a sibling `.bin` whose path cannot leave the manifest
directory. `replay --verify` checks the hash. Saved bytes stay replayable
even if a later generator changes. A hash mismatch exits `6`.

```bash
data-poison replay cases/manifest.json --verify --format raw --output reproduced.bin
data-poison inspect cases/manifest.json
```

## Reports

`test` can write `--report results.json`. `report` prints text, JSON, or
Markdown: counts by validity and by result class, durations, and total
bytes. There is no single quality score.

```bash
data-poison report results.json --format markdown
```

## Output Formats

`text` escapes control characters. `json` and `jsonl` carry base64 plus
hex so binary payloads are not replaced with U+FFFD. `hex` and `base64`
are one payload per line. `raw` is the exact bytes.

## Safety Limits

Defaults are one case, profile `awkward`, 1 MiB per payload, depth 32,
and 100 MiB in total. You can raise them. The hard ceilings are 100,000
cases, 32 MiB per payload, depth 128, and 512 MiB in total. Existing
files are not overwritten without `--force`. Mutation inputs are not
modified. Manifests and reports are written by replacing a temporary
file. Temporary command inputs are removed unless
`keep_temporary` is set in the config.

## Configuration

TOML. Precedence is the command line, then the recipe, then `--config`,
then `~/.config/data-poison/config.toml`, then built-in defaults. Unknown
keys are an error.

```toml
profile = "awkward"
count = 1
format = "text"
max_bytes = 1048576
timeout_seconds = 5
expect = "by-validity"
```

`expect` may be `by-validity`, `accept`, or `reject`.

## Platform Differences

Filename contracts differ for Windows, POSIX, and macOS. They describe
operating-system name rules, not one vendor's filesystem. Timezone cases
need IANA data; if it is missing, the command says so. Process signals
and process-tree kill behaviour follow the host. The tool does not claim
identical signal numbers on Windows.

## Python API

```python
from lupaxa.data_poison import generate

cases = generate(count=3, seed=12345, categories=["unicode"], profile="awkward")
print(cases[0].explanation)
print(cases[0].payload)
```

Generators return `Case` values. They do not print. `mutate_payload`
works on bytes the same way.

## Troubleshooting

`unknown case` means the identifier or suffix matched nothing, or matched
more than one entry. Use `catalogue` and the full identifier. `unsupported
schema keyword` means strict mode refused a feature outside the subset.
`timezone ... is not available` means the IANA database has no such zone.
`already exists` means pass `--force`. A hash error on replay means the
payload bytes and the manifest disagree; the bytes were not rewritten to
match.

## Examples

Difficult usernames:

```bash
data-poison unicode --profile nightmare --count 20 --seed 12345 --format jsonl --output usernames.jsonl
```

Numeric boundaries:

```bash
data-poison numbers --case outside-range --minimum 0 --maximum 100 --seed 1
```

Malformed JSON, one file per case:

```bash
data-poison json --validity malformed --count 10 --seed 1 --format raw --output malformed-cases/
```

Schema boundaries:

```bash
data-poison schema customer.schema.json --mode boundary --count 20 --seed 1 --manifest cases.manifest.json
```

Mutate a JSON file:

```bash
data-poison mutate customer.json --strategy single --count 20 --seed 1 --output mutations/
```

Run a local checker:

```bash
data-poison test --command "./validate-json" --category json --profile hostile --count 50 --seed 12345 --report results.json
```

Replay:

```bash
data-poison replay cases/manifest.json --verify --format raw --output reproduced.bin
```

Shrink:

```bash
data-poison shrink failing.bin --command "./validate-json" --predicate nonzero --output minimal.bin
```

A recipe:

```bash
data-poison recipe customer.toml --validate
data-poison recipe customer.toml --seed 12345
```

A Markdown report:

```bash
data-poison report results.json --format markdown
```

## Development

```bash
make init
make python-install-dev
make python-check
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
