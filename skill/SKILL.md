---
name: narrative
description: Write or review Python in the Narrative house style — mixedCase functions, main() first with types last, parse-at-the-boundary dataclasses, no ORM, explicit global on mutation, exhaustive match without a fallback arm, and a verified ruff/pylint/mypy toolchain. Use for any Python written in or for this codebase, and when reviewing a diff against this style.
---

# Narrative Python

Rules cite the benchmark decision behind them (`benchmark/decisions.jsonl`). A rule with no
citation and no linter behind it does not belong here.

## The principle everything else serves

**0% of the reader's effort on rote diffing, 100% on design.** (R2b-P0)

Four near-identical lines differing in one token, at a 90% per-line detection rate, give the reader
a 0.9⁴ = 66% chance of spotting the difference. One parameterised call makes it 90%. This is the
root of DRY, of one-name-for-one-thing, of consistent ordering, and of the ban on gratuitous
variation. When two rules conflict, the one that spares the reader diffing wins.

Second principle, for representation choices: **prefer what the type checker and IDE can follow**,
even when a looser form is more flexible. Measured, not aesthetic — holding state in a
`dict[str, Any]` instead of typed attributes cost 6 `cast()` calls and 15 dict lookups to pass
`mypy --strict`, versus zero. (R3-P2-rank)

## File layout

```python
from __future__ import annotations   # mandatory: makes types-last legal

import struct                        # plain imports, alphabetised
import sys
from pathlib import Path             # then `from` imports, alphabetised
from typing import NewType
                                     # TWO blank lines
                                     
LOG_PATH = Path('jsonl_logs/app.jsonl')     # tunable constants, grouped BY CONCERN
DEFAULT_DB_PATH = Path('app.db')
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
                                     # one blank line
LOG = logging.getLogger('app')       # globals baked into the design sit apart


def main() -> int:                   # FIRST. The beating heart; where a reader goes first.
    ...


def stepOne(...) -> ...:             # workflow, in first-call order
def stepTwo(...) -> ...:
def leafHelper(...) -> ...:


### vocabulary #########################################################################

ScanId = NewType('ScanId', int)      # types LAST: the specifics of what main() passes
class Outcome(Enum): ...             # around come after grokking the high-level design
class ConfigError(RuntimeError): ...
@dataclass(frozen=True)
class ScanHeader: ...
```

- `main()` returns an exit code; `sys.exit(main())`. All executable code lives in `main()`. (Q10)
- Caller before callee throughout. Nothing may be *called or subclassed at module level* before its
  definition — watch for a constant whose **value** references an Enum member or class. Annotations
  are safe; the future import makes them lazy. (R2-10, R3a-03)
- That is an **ordering** rule, not a placement ban. A constant whose value names an Enum member is
  perfectly legal in `### vocabulary` immediately after that Enum — and that is its only legal
  module-level home. Do not contort around it. (R4-03)
- Order constants by concern — the things a dev would go looking for at the same moment. All the
  `_S` durations adjacent, then non-duration limits, then hosts, then wire literals. Type usually
  correlates; concern decides. No blank lines inside the block. (R3a-16, R3a-15)
- 120 columns. Absolute imports only. Single quotes (docstrings and multiline: double).
- Separate logically self-contained blocks inside a function with **one blank line** — that is its
  only meaning here. Deliberately grouped short guards stay grouped; two adjacent two-line
  `if ...: raise` checks belong together. No blank line after a docstring. (R3a-01)
- If a guard grows to three lines because it logs before raising, `NAR008` will force a blank line
  and break the grouping. **That is a signal, not a conflict**: move the logging into a
  `reject*()` helper that logs and returns the exception. The guards are two lines again, they
  group, `NAR008` is silent, and the raise-site rule is still honoured. Neither rule yields.
  (R4-05)
- A `def` with >3 **positional** arguments puts each on its own line with a trailing comma, even
  under 120 columns. **Calls are exempt** — applying it to calls costs +19% lines. (R2b-B1)
- **Keyword-only parameters do not count**, so a function may carry as many as it needs. That is
  also the escape hatch at exactly four: put `*` before the optional ones and they stop counting,
  which documents them as optional anyway. Note `NAR004` counts *every* parameter — each one is
  part of the contract even when the caller may omit it. (R5-06)
- Long strings: implicit concatenation in parens. Never `"""` for data — its whitespace ends up in
  the value. (Q03)

## Structure inside a function

- Guard clauses and early return over nesting. (Q06)
- Comprehensions may have any number of `if` clauses at a single level. Any **nesting** becomes an
  explicit loop. (Q07)
- **Extract a block when you can foresee reusing or testing it separately** — not merely because it
  has a name. `computeChecksum` extracts because it could be used in many places; the two halves of
  `openDatabase` do not, even though each is nameable. A one-line helper called once is residue.
  (R2-09, R2b-E1, R2b-E2)
- If extraction would need 5+ parameters, that is a **missing state dataclass**, not a reason to
  leave the code inline. (R2b-E3)
- Duplicated-but-drifting code is always collapsed, even when the shared version needs a parameter.
  Localising the difference is the whole point. (R2b-E4)
- Mixed `and`/`or` parenthesises each group explicitly. Never `A and B or C and D`. Ruff cannot
  produce this form, so `SIM114` is disabled and `NAR007` enforces it. (R2b-B4)
- Merge branches that share a body **only where the type checker keeps its narrowing.** Merging two
  `isinstance` branches — even parenthesised — widens the subject back to a union and loses the
  narrowing. Two explicit branches beat one clever condition. (R2b-B5)
- If it names a path, its type is `Path`, not `str`. (R3a-10)
- Collection literals get one item per line, because `ruff format` gives you no choice. A
  word-list-shaped literal may use a `# fmt: off` / `# fmt: on` fence to stay packed. (R2b-B2)

## Naming

- Functions and methods `mixedCase`. Classes and types `PascalCase`. Variables and arguments
  `snake_case`. Module constants `ALL_CAPS`. **In someone else's `snake_case` codebase, match
  local convention** — detect before writing.
- Spell names out. No `img_arr`, `cfg`, `idx`. (Q11)
- Never restate the type in a parameter name: `config: RebinConfig`, not
  `rebin_config: RebinConfig`. (Q11)
- Predicates are bare adjectives: `readyForScan`, not `isReadyForScan`. (Q12)
- `from pathlib import Path`, not `pathlib.Path`. Avoid fully qualified names — but keep the module
  where it carries meaning (`struct.unpack`, `json.loads`, `asyncio.wait_for`). Import the class,
  keep the verb qualified. (R3a-08)

## Where a constant lives

Name every magic number. (Q09) Then place it by this test:

> Could someone change this value safely knowing only what the program **does**, or would they need
> to understand the function's **implementation**?

The latter is an implementation detail and belongs **inside** the function, still `ALL_CAPS`.
`MAGIC`, `HEADER_FORMAT`, a padding byte, a derived size, a checksum mask, and a function's own SQL
all go inside. A log path, an archive directory, a glob, exit codes and operator-tunable timeouts
stay at module level. (R3a-12)

*Not lintable — "used by exactly one function" flags 14 of 16 constants including the ones that
should stay out. This is review judgement.*

## Types

- Annotate every parameter and return. `mypy strict = true`, `disallow_any_explicit` left **off**
  so a written `Any` is a visible, greppable admission. (R2-11)
- Annotate the true requirement, not a habitual container: a body that only iterates takes
  `Iterable`, not `list`. (Q13)
- `NewType` for domain primitives — `ScanId`, `SampleRef` — so a bare `int` is a type error. (Q15)
- `Enum` for closed sets, `.value` at serialisation boundaries. Not `Literal`, not `StrEnum`. (R2-08)
- `Protocol` for a seam with more than one real implementation. Never `ABC` — that is inheritance.
  (R2-01)
- Annotations nest at most 2 deep. Deeper means a dataclass is missing. (NAR005)
- Composition over inheritance, always.

### Exhaustive dispatch — no fallback arm

```python
def severityFor(outcome: Outcome) -> LogLevel:
    match outcome:
        case Outcome.INGESTED:
            return LogLevel.INFO
        case Outcome.REJECTED:
            return LogLevel.WARNING
        # no `case _`. Adding a member now gives: error: Missing return statement
```

Omitting `case _` is what makes mypy catch a new variant. **A `case _: raise RuntimeError(...)`
one-liner looks equivalent and is not — it type-checks clean and silently accepts the missing
case.** No helper, no `assert_never`. (Q18, R3a-07)

Limitation: only works when the match returns a value. A side-effecting `-> None` dispatch gets no
protection — restructure it to return something.

**Keep the `match` even when a mapping looks more natural.** Measured on an ordering lookup: the
`match` is the *only* form where adding a member is caught — a `dict` lookup and an `IntEnum` both
type-check clean and fail at runtime with `KeyError`. The performance objection does not survive
measurement either: the mapping is 15% faster per call (119.8 vs 141.7 ns), a function-local dict
is **6.4× slower**, and end-to-end the spread between forms is smaller than run-to-run noise.
(R4-03)

`IntEnum` is not a substitute. It makes `json.dumps({'level': LogLevel.INFO})` silently emit `20`
where a plain `Enum` raises `TypeError`, and `str()` differs between 3.10 and 3.12. (R4-03)

## Data at boundaries

- Parse untrusted input into a **frozen dataclass at one boundary gate**, then never validate
  again. The objection to Pydantic/ORMs is *pervasive runtime validation*, not a single gate.
  (Q14, Q17)
- `frozen=True` for data crossing a boundary — parsed input, config, returned values. Objects
  modelling something that genuinely changes over time stay mutable. Not a blanket default. (R2-07)
- A dataclass, never a dict of parsed fields. (Q02) That rule is about **what holds the record**,
  not about what type a field may have — a mapping-typed *field* is fine.
- **Genuinely schemaless input**: promote the fields the program actually computes on to typed
  attributes, and put the remainder in one `Mapping[str, object]` field. Flattening it to a JSON
  string costs a second `json.loads` downstream, makes it unaddressable by `jq`, and forces the
  reader back through `Any`. (R4-04)

  Two traps this creates, both verified:
  - **Never splat the remainder into an output record.** `{'source': path, **entry.extra}` lets an
    untrusted log line carrying its own `source` key **forge its provenance in your report**. Nest
    it: `{'source': path, 'extra': dict(entry.extra)}`.
  - `frozen=True` plus a mapping field is **not hashable** — `set(entries)` raises `TypeError` at
    runtime with no linter warning. Fine until someone dedupes.
- No ORM. SQL directly.

## Errors

- Custom exception types subclassing `RuntimeError`, not `Exception`. (Q20)
- Handle each failure mode narrowly and separately. Never one `try` around the whole operation with
  a tuple of unrelated exception types. (Q19)
- `raise NewError(...) from exc`, **and** log it. Both. (Q21)
- **The raise site records the generic fact once — however you factor that.** A parser with six
  raise sites does not get six log statements; route them through a helper that logs and returns
  the exception, then `raise rejectLine(...) from exc`. Verified: the helper and six inline logs
  emit byte-identical records, and the helper costs 13 fewer lines. (Q23, R4-02)
- **The handle site records what it meant here — but in a degrade-and-report loop it logs the
  aggregate, not the item.** This is the rule that matters. Per-item handle-site logging on a file
  with 10,000 bad lines emitted **10,023 records / 3.2 MB**; logging the item at DEBUG and a
  per-file tally at WARNING gave **24 records / 1.2 KB** with nothing lost under `--verbose`.
  (R4-02)
- **Level follows from what an operator can act on**: a per-item failure is DEBUG, the tally is
  WARNING. An operator cannot act on line 4,812 of one file; they can act on "4,812 of 10,000 lines
  rejected". (R4-02)
- LBYL over EAFP: you know your own invariants, you do not know every exception an implementation
  can raise. (Q22)
- Degrade and report: process the whole batch, collect failures, log a summary, exit nonzero. Never
  abort on the first bad item. (Q24)

## Module state

- **`global` marks a side effect, not a dependency.** Declare it when a function *mutates* module
  state. Reading is exempt. (R2b-G1)
- Python already forces `global` to rebind. What it does not police — and no linter catches — is
  in-place mutation: `CONFIG.clear()`, `CONFIG['k'] = v`, `CONFIG.attr = v`. That is `NAR001`.
- Every attribute declared in `__init__`. `hasattr(self, ...)` is a red flag. (Q04)

## The module docstring

**Every module opens with a docstring. Anything runnable shows how to run it.** It is the first
thing a reader meets — before `main()` — so it carries what the program is *for*, not how it works.
(R5-02, NAR009)

Write it in **STE**: one idea per sentence, active voice, one word for one thing, no synonyms. It
is the one place in the file where prose quality is load-bearing.

```python
"""Load a CSV file into a SQLite table.

Each column is typed from its values as INTEGER, REAL or TEXT. A row that does not fit the
inferred types is skipped and reported. The program does not modify an existing table.

Usage:
    $ python3 loadCsv.py readings.csv readings.db measurements
    $ python3 loadCsv.py readings.csv readings.db measurements --sample-rows 200

Exit codes:
    0  every row loaded
    1  one or more rows skipped
    2  the file, the database or the arguments were unusable
"""
```

Required: what it does; an example invocation per meaningful mode; exit codes when there are more
than two; the shape of input and output where it is not obvious from the arguments. `NAR009`
enforces the docstring and, for a module with a `__main__` block, the presence of an example.

- A function gets a full structured docstring (summary, Args, Returns, Raises) when its **contract
  is complex**: it raises, or takes more than three parameters, or exceeds 20 lines. Below all
  three, `#` comments carry the contract. (Q05, R2-03, R2-05, R5-05)

  A bare line threshold is gameable in the wrong direction — splitting a 21-line function into two
  12-line ones would delete the obligation, so the rule would reward fragmentation. Contract
  complexity does not shrink when you split: the pieces still raise, and still take their
  parameters.
- A docstring must not assert anything the code does not do, and must not state a consequence it
  already implied. (Q05)
- Where semantics vary by implementation — file moves, copies, path manipulation — **show a
  concrete before/after example**, not prose. (R3a-11)
- Comments carry the why, the tribal knowledge, the link to the source. Never restate the line.
- `FIXME:` for a failure to meet standards; `TODO:` for non-urgent debt.

## Logging

One stable event name plus structured `extra={...}` fields — never an f-string of prose. The
message is a queryable key. (Q08)

**JSONL output is for a service, not for every script.** The stdlib has no JSONL formatter, so a
self-contained program hand-rolls `JsonlFormatter` + `configureLogging` — measured at **21 lines
per file, byte-identical every time, 8% of a four-program sample** — so that a one-shot CLI emits
machine-parseable stderr no machine will read. Decide by who reads the logs: (R5-03)

- **A service, or anything whose logs are collected** — JSONL, from a shared module. In a monorepo
  it is imported, never re-pasted; that is what makes it worth having.
- **A single-file tool run by hand** — `logging.basicConfig(format=...)` and one line. The event
  name and `extra` discipline still applies; only the formatter goes.

## Configuration

Most explicit first:

1. **A config file tracked in the repo**, parsed into a frozen dataclass — the default for anything
   describing a deployment. Infrastructure becomes code-defined and diffable. (R3a-02)
2. **CLI arguments** for the inputs of a batch tool invoked by hand. `argparse`.
3. **Environment** for secrets and DB URLs, via `python-decouple`, not `os.environ`. (R2-06)
4. **`ALL_CAPS` constants** for tuning knobs that do not vary by deployment.

## Concurrency

asyncio is the default for I/O-bound work. (R2-04)

## Testing

- **Real dependencies**: a real socket on loopback, a real temp SQLite file, a real temp directory.
  A test double is a last resort for something you genuinely cannot run, and is flagged as a known
  gap. A fake transport produces tests that pass while production fails. (R2-02, Q16)
- **Property-based tests (hypothesis) wherever there is an invariant** — round-trips, ordering,
  conservation, numeric range. Example-based tests cover specific regressions on top. A very slow
  stateful property test may be opt-in rather than run in CI. (R2-12)
- **Test functions are `testSomethingDescriptive`** — camelCase, `test` prefix. The conventional
  `test_parse_header_roundtrips` fails the `mixedCase` gate this style mandates; the camelCase
  spelling passes pylint *and* is still collected by pytest's default `python_functions = test*`.
  Both verified.
- Tests live in their own module, not in the program file. A `from hypothesis import given` at
  module scope makes the program unable to start without the test library installed — verified:
  `ModuleNotFoundError` before `main()` is reached. Where a single file is genuinely required, put
  the tests behind `### tests` before the `### vocabulary` divider and import hypothesis lazily.

## Python 3.10 floor

`ruff` targets `py310`; check with `vermin -t=3.10- --violations`.

- `datetime.UTC` is 3.11+ → `datetime.timezone.utc`.
- `typing.assert_never` is 3.11+ → not needed; omit the fallback arm instead (above).
- **`except asyncio.TimeoutError`, never the builtin `TimeoutError`**, around `asyncio.wait_for`.
  On 3.10 they are different classes and the builtin handler catches nothing — verified on 3.10.18.
  `vermin` does **not** catch this. (R3a-06)
- Also unavailable: `enum.StrEnum`, `asyncio.TaskGroup`, `asyncio.timeout()`, `typing.Self`,
  `tomllib` (use `tomli`). `match`, `X | Y` and `dataclass(slots=True)` are fine.

## Avoid the usual traps

Bare `except:`. Mutable default arguments. See `wtfpython` for the rest.

## Verify

Never claim conformance without running these. Config: `pyproject-snippet.toml`.

```
ruff check --fix    &&  ruff format    # order matters
pylint --rcfile=pyproject.toml         # the only thing that enforces mixedCase
mypy --strict
python3 checks.py <paths>              # NAR001-NAR008, which no other tool implements
vermin --no-tips -t=3.10- --violations
```

`tooling.md` explains what each layer owns and documents the gotchas — several rules here are
silently undone by a tool's default (`ruff check --fix` collapsing blank lines after imports;
`SIM114` merging branches in a way that loses type narrowing). Read it before changing config.
