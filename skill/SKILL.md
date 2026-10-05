---
name: narrative
description: Write or review Python in the Narrative house style — mixedCase functions, main() first with types last, parse-at-the-boundary dataclasses, no ORM that re-validates what the database checks, explicit global on mutation, exhaustive match without a fallback arm, and a verified ruff/pylint/mypy toolchain. Covers multi-module architecture too: which module may import which, when one file becomes several, what a package __init__.py holds, where a shared type lives, and when to take or contain a third-party dependency. Use for any Python written in or for this codebase, when laying out modules or packages, and when reviewing a diff against this style.
---

# Narrative Python

**0% of reader effort on rote diffing, 100% on design.** (R2b-P0) Every rule below is a case of
that, or of the second principle: prefer what the type checker and IDE can follow.

Four near-identical lines that differ in one token make the reader compare them token by token, and
every comparison is a chance to miss the difference. One parameterised call removes the comparison.

This is the root of DRY, of one-name-for-one-thing, of consistent ordering, and of the ban on
gratuitous variation. When two rules conflict, the rule that spares the reader diffing wins.

Second principle, for representation choices: **prefer what the type checker and IDE can follow**,
even when a looser form is more flexible. State in a `dict[str, Any]` passes `mypy --strict` only
with a `cast()` or a key lookup at every use. Typed attributes pass with neither. (R3-P2-rank)

**This document governs every file, however many there are.** Naming, layout, types, errors and
docstrings apply to each module of a package exactly as they apply to a single-file program.

`architecture.md` adds what happens **between** files: which module may import which, where a shared
type lives, when one file becomes several, and what a third-party dependency may touch. Read it when
the program spans more than one module or imports a third-party package. Skip it for a single-file
program, where none of it applies.

The reason for each rule is in its text, so read the rule and not the id after it. The ids are
provenance: they resolve in `benchmark/decisions.jsonl` in the source repository,
`github.com/OrderFromChaos/narrative-python`, which does not ship with the skill. **A rule with no
id and no linter behind it does not belong here.**

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
LOG = logging.getLogger(__name__)    # globals baked into the design sit apart


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

- `main()` returns an exit code. Call it as `sys.exit(main())`. All executable code lives in
  `main()`. (Q10)

- Caller before callee throughout. At module level, do not *call or subclass* anything before its
  definition. Watch for a constant whose **value** references an Enum member or class. Annotations
  are safe, because the future import makes them lazy. (R2-10, R3a-03)

- That is an **ordering** rule, not a placement ban. A constant whose value names an Enum member is
  perfectly legal in `### vocabulary` immediately after that Enum, and that is its only legal
  module-level home. Do not contort around it. (R4-03)

- Order constants by concern: the things a dev would look for at the same moment. All the `_S`
  durations adjacent, then non-duration limits, then hosts, then wire literals. Type usually
  correlates, and concern decides. No blank lines inside the block. (R3a-16, R3a-15)

- 120 columns. Absolute imports only. Single quotes (docstrings and multiline: double).

- Separate logically self-contained blocks inside a function with **one blank line**. That is its
  only meaning here. Deliberately grouped short guards stay grouped, and two adjacent two-line
  `if ...: raise` checks belong together. No blank line after a docstring. (R3a-01)

  **No tool checks this.**
  Place a blank line by these five rules: (`R8-NAR008`, `R8-NAR008-rule`)

  - a body of **8 lines or under takes no internal blanks at all**
  - blanks **recur into nested blocks**, and one loop body can take four
  - **a multi-line statement and the statement that consumes its value are one step**, so
    `executemany` then `commit`, and a constructor then the `return` of it, stay adjacent
  - a blank precedes a `return` when the phase before it is unrelated, and not when the returned
    value was just built
  - **length is not the trigger**, in either direction: a long statement earns no blank after it,
    and a short group of statements still earns one before the next group

- If a guard grows to three lines because it logs before raising, move the log call into a
  `reject*()` helper that logs and returns the exception. The guards are two lines again and group,
  and the raise-site rule still holds. (R4-05)

- A `def` with >3 **positional** arguments puts each on its own line with a trailing comma, even
  under 120 columns. **Calls are exempt**: a signature is read once and a call site is read
  everywhere, so the same rule applied to calls costs lines without buying clarity. (R2b-B1)

- **Keyword-only parameters do not count**, so a function may take any number of them. That is also
  the escape hatch at exactly four: put `*` before the optional ones and they stop counting, and
  they read as optional in the signature anyway. Note `NAR004` counts *every* parameter, because
  each one is part of the contract even when the caller may omit it. (R5-06)

- Long strings: implicit concatenation in parens. Never `"""` for data, because its whitespace
  becomes part of the value. (Q03)

## Structure inside a function

- Guard clauses and early return over nesting. (Q06)

- Comprehensions may have any number of `if` clauses at a single level. Any **nesting** becomes an
  explicit loop. (Q07)

- **Extract a block when you can foresee reusing or testing it separately**, not merely because it
  has a name. `computeChecksum` extracts because many places could call it. The two halves of
  `openDatabase` do not extract, even though each is nameable. A one-line helper called once is
  residue. (R2-09, R2b-E1, R2b-E2)

- If an extracted function would take 5+ parameters, that is a **missing owner**, not a reason to
  leave the code inline. Find where the values belong. That owner is a **class** when two of it can
  exist at once, and a **module** otherwise. A frozen record is the answer only when nothing has
  behaviour over the values. If a general name for the group is hard to pick, it is not a real
  grouping. (R7-C05-resolved, R7-C05-naming)

- Always collapse duplicated-but-drifting code, even when the shared version takes an extra
  parameter. To localise the difference is the whole point. (R2b-E4)

- Mixed `and`/`or` parenthesises each group explicitly. Never `A and B or C and D`. Ruff cannot
  produce this form, so `SIM114` is disabled and `NAR007` enforces it. (R2b-B4)

- Merge branches that share a body **only where the type checker's narrowing survives the merge.**
  If you merge two `isinstance` branches, even with parentheses, mypy widens the subject back to a
  union and loses the narrowing. Two explicit branches beat one clever condition. (R2b-B5)

- Collection literals get one item per line **wherever `ruff format` explodes them**, which is any
  literal it cannot fit on one line. This is how the formatter behaves, not a further rule: a short
  literal it leaves packed is already correct. A word-list-shaped literal may use a `# fmt: off` /
  `# fmt: on` fence to stay packed. (R2b-B2)

## Naming

- Module filenames `snake_case`. Functions and methods `mixedCase`. Classes and types
  `PascalCase`. Variables and arguments `snake_case`. Module constants `ALL_CAPS`. **In a
  `snake_case` codebase that you did not write, match local convention.** Detect before you write.

- Spell names out. No `img_arr`, `cfg`, `idx`. (Q11)

- **A function name leads with a verb, and the verb's object names what the function returns.**
  `parsePolicy`, `readManifest`, `extractPackagesFromLockfileText`, `computeDeletionCutoff`. Not
  `policyIn`, not `cutoffFor`: a name built from a preposition points at what the function takes.
  (R9-03)

- **A name stands alone**, and the module qualifier does not count toward it. A reader who has
  never opened the module must understand the name. `requirements_lock.packagesIn` reads at the call
  site and says nothing at the definition, and nothing stops a second module declaring a second
  `packagesIn`. **Two functions in one package do not share a name.** (R9-03, R7-B06)

  **Length is not the defect.** Where the clear name is the longer one, write the longer one.

- Predicates are bare adjectives, and take no verb: `readyForScan`, not `isReadyForScan`, and
  `belowMinimum`, not `checkBelowMinimum`. A predicate returns the answer to a question. (Q12)
  Dunder and protocol methods are named by the language.

- **Do not restate a domain type in a parameter name**: `config: RebinConfig`, not
  `rebin_config: RebinConfig`. The type already names the thing, so the prefix adds nothing. (Q11)

- **A generic type names no thing, so the parameter name must.** `Path`, `str`, `int`, `bytes`,
  `dict` and `object` give a value's shape and never say which value it is. Write
  `policy_json_path: Path`, not `path: Path`, and `manifest_text: str`, not `text: str`. The rule
  above bans a redundant prefix, not an informative one.

- **Raw and parsed forms get different names.** Prefix the raw form with `raw_`: `raw_at: str` from
  the file, `at: DateTime` once parsed. Never `at` beside `parsed.at`. (R10-raw-names)

- **Restate the type where the bare name would shadow an import.** A program that imports a
  first-party module by name burns that identifier at module scope, so the local becomes
  `results_store: Store`. (R8-B06-Q11)

- `from pathlib import Path`, not `pathlib.Path`. Avoid fully qualified names, but keep the module
  where it carries meaning (`struct.unpack`, `json.loads`, `asyncio.wait_for`). Import the class,
  keep the verb qualified. (R3a-08)

## Where a constant lives

Name every magic number. (Q09) Then place it by this test:

> Could someone change this value safely knowing only what the program **does**, or would they need
> to understand how the function **works**?

The latter is an implementation detail and belongs **inside** the function, still `ALL_CAPS`. Put
`MAGIC`, `HEADER_FORMAT`, a padding byte, a derived size, a checksum mask, and the SQL of a single
function inside. A log path, an archive directory, a glob, exit codes and operator-tunable timeouts
stay at module level. (R3a-12)

*No tool checks this. This is review judgement.*

## Types

- Annotate every parameter and return. `mypy strict = true`, `disallow_any_explicit` left **off**
  so a written `Any` is a visible, greppable admission. (R2-11)

- Annotate the true requirement, not a habitual container: a body that only iterates takes
  `Iterable`, not `list`. (Q13)

- `NewType` for domain primitives (`ScanId`, `SampleRef`), so a bare `int` is a type error. (Q15)

- **A file path is a `Path`** from the boundary inward. A `str` path only where an outside API
  requires one, or for an argument echoed exactly as typed, named `raw_…`: `raw_input_dir`.
  (R3a-10, R10-path-type)

- **Money is integer cents**, named `…_cents`: parse to `int` at the input, format at the output.
  A computation that yields fractions of a cent, such as rate × minutes × multiplier, stays in
  integers or `Fraction` and rounds once, with the rounding mode explicit. No `float` or `Decimal`
  arithmetic on amounts. (R10-money-cents)

- **Dates and times use `pendulum`**, unless `datetime` is tightly integrated with the repository,
  so that removing it would be hard. Replace a small `datetime` use with `pendulum`. A library that
  returns `datetime` values, such as `tomllib`, `sqlite3` or a JSON decoder, is a boundary: convert
  each value to pendulum where it enters. (R10-pendulum, R10-pendulum-boundary)

- `Enum` for closed sets, `.value` at serialisation boundaries. Not `Literal`, not `StrEnum`. (R2-08)

- `Protocol` for a seam with more than one real implementation. Never `ABC`, because that is
  inheritance. (R2-01)

- **An annotation you cannot say out loud needs a name.** The test is conversational: could you
  refer to this type in a normal discussion with another programmer? `park(car: Car)` reads and
  discusses. `park(car: dict[str, list[tuple[float, float]]])` does neither. (NAR005, R8-D27-resolved)

  **One measure: how many names it contains, below the outermost.** `Car` contains none.
  `dict[str, list[tuple[float, float]]]` contains five, and above four, give the annotation a name.
  A callable becomes a `Protocol`; anything else becomes a dataclass. (`NAR005`, `R8-D27`)

  **The DB-API is the standing exception.** `sqlite3.executemany` takes a sequence per row and
  raises `ProgrammingError: parameters are of unsupported type` on a dataclass. Instead, use a
  `NamedTuple` for rows: it is a tuple, so `executemany` takes it, and its fields have names. Use
  `?` placeholders, and say why in a comment. (`R8-D27`, `R10-namedtuple-rows`)

  ```python
  # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
  class FindingRow(NamedTuple):
      path: str
      line: int
      code: str
      detail: str


  def storeFindings(connection: sqlite3.Connection, rows: list[FindingRow]) -> None:
      connection.executemany('INSERT INTO findings VALUES (?, ?, ?, ?)', rows)
      connection.commit()
  ```

  The reason is a shared name, not type safety: only `NewType` makes swapped coordinates a type
  error (Q15).

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

**A `case _: raise RuntimeError(...)`
one-liner looks equivalent and is not. It type-checks clean and silently accepts the missing
case.** No helper, no `assert_never`. (Q18, R3a-07)

Limitation: this works only when the match returns a value. A side-effecting `-> None` dispatch
gets no protection. Restructure it to return something.

**Keep the `match` even when a mapping looks more natural.** Only a `match` fails mypy when a new
member goes unhandled. A `dict` lookup and an `IntEnum` both type-check clean and fail at run time
with `KeyError`.

Speed does not change this: the difference between the forms is below run-to-run noise. (R4-03)

`IntEnum` is not a substitute. It makes `json.dumps({'level': LogLevel.INFO})` silently emit `20`
where a plain `Enum` raises `TypeError`, and its `str()` changed across releases. **`StrEnum` is
available at the 3.11 floor and is not a substitute either**, for the same reason: it serialises
silently where a plain `Enum` makes the boundary explicit. Keep the plain `Enum` and the exhaustive
`match`. (R4-03, R7-E07-floor)

## Data at boundaries

- Parse untrusted input into a **frozen dataclass at one boundary gate**, then never validate
  again. The objection to Pydantic/ORMs is *pervasive runtime validation*, not a single gate.
  (Q02, Q14, Q17)

- **A parsed record contains only what its input contained.** Where one input format has a field and
  another does not, the field is optional on the shared record, and the check that reads it skips an
  absent value. **Never substitute a plausible default**, because the output then contains a fact
  that the file does not. (R9-01)

  A lockfile of `name==version` lines has no source. Give the record `source: SourceName | None`
  and let the source check pass on `None`. Do not stamp `'pypi'` on every package: under a policy
  that allows only `internal`, an invented source turns every line of every lockfile into a finding
  that the manifest never justified.

- **Pydantic can be used for standardizing user input, at the boundary gate, and nowhere else.**
  `TID251` bans the import, so declare `# ruff: noqa: TID251` in the gate module, and name the gate
  function in its module docstring. A second suppression in one program means validation is no
  longer at one gate. (R8-D10, R10-pydantic)

- **No framework should validate output.** FastAPI makes a route's return annotation its response
  model, so every response is validated at run time. Pass `response_model=None` in the route
  decorator, and keep the annotation for mypy. (R10-pydantic)

- **`frozen=True` is the default for every dataclass.** It has nothing to do with boundaries: a
  record built and consumed inside one function is frozen for the same reason a parsed one is.
  (R8-D11-resolved)

- Drop to mutable only when a **field's value is mutable**, and treat that as a smell rather than
  a decision. Reach for a `tuple` where you would write a `list`. A frozen wrapper around mutable
  contents is a half-guarantee: `dataclasses` will not stop you writing through it, so the bug grows
  quietly and surfaces at run time with nothing to catch it. The standing exception is the
  schemaless remainder below, where a `Mapping` field is the prescribed shape.

- **Genuinely schemaless input**: promote the fields the program actually computes on to typed
  attributes, and put the remainder in one `Mapping[str, object]` field. To flatten it to a JSON
  string costs a second `json.loads` downstream, makes it unaddressable by `jq`, and forces the
  reader back through `Any`. (R4-04)

  This creates two traps:

  - **Never splat the remainder into an output record.** `{'source': path, **entry.extra}` lets an
    untrusted log line that carries its own `source` key **forge its provenance in your report**.
    Nest it: `{'source': path, 'extra': dict(entry.extra)}`.

  - `frozen=True` plus a mapping field is **not hashable**. `set(entries)` raises `TypeError` at
    run time with no linter warning. Fine until someone dedupes.

- **An ORM is fine where it makes database work easier, as long as it adds no run-time validation
  that the database already does.** The cost is per row and per request, and worst on a hot path,
  such as an endpoint that returns database values. SQLAlchemy, peewee, Piccolo and Django models
  run no validation on write or on read. `TID251` bans the ORMs that do: SQLModel, ormar, Tortoise,
  Pony and SQLObject. A migration, a healing script or a one-off backfill can still use one:
  declare `# ruff: noqa: TID251` in that module. There is no `per-file-ignores` list: an exception
  is a property of the module, not of a glob that drifts from the tree it matches. Conformance owes
  no explanation, so the suppression stands bare. (Q17, R6-03, R6-07, R7-D04, R7-D04-generalised,
  R10-orm-validation)

## Errors

- Custom exception types subclassing `RuntimeError`, not `Exception`. (Q20)
- **The name ends in `Error`.** Ruff `N818` enforces this and rejects `SourceRejected`. Use
  `RejectedSourceError`.

- Handle each failure mode narrowly and separately. Never one `try` around the whole operation with
  a tuple of unrelated exception types. (Q19)

- **Related means the handling is the same, not that the classes share a base.** Where two failures
  genuinely produce one outcome, one `except (A, B)` arm is correct and two identical arms are the
  rote diffing banned by the top principle. But check the premise first: two arms that look
  identical usually should not be. A timeout and an unreachable host are different facts and deserve
  different words, and writing the same string twice is how that gets lost. (R8-D24-resolved)

- `raise NewError(...) from exc`, **and** log it. Both. (Q21)

- **Log the generic fact once at the raise site, however you factor that.** A parser with six
  raise sites does not get six log statements. Route them through a helper that logs and returns
  the exception, then `raise rejectLine(...) from exc`. The helper emits the same records as six
  inline log calls and costs fewer lines. (Q23, R4-02)

- **At the handle site, log what the failure meant there, but in a degrade-and-report loop log the
  aggregate, not the item.** This is the rule that matters. Per-item handle-site logging on a file
  of 10,000 bad lines writes a record per line and megabytes of output. Log the item at DEBUG and a
  per-file tally at WARNING: that is tens of records and kilobytes, and every item still appears
  under `--verbose`. (R4-02)

- **Level follows from what an operator can act on**: a per-item failure is DEBUG, the tally is
  WARNING. An operator cannot act on line 4,812 of one file. An operator can act on "4,812 of
  10,000 lines rejected". (R4-02)

- LBYL over EAFP: you know your own invariants, you do not know every exception an implementation
  can raise. (Q22)

- Degrade and report: process the whole batch, collect failures, log a summary, exit nonzero. Never
  abort on the first bad item. (Q24)

- **The config gate is the exception.** (R8-D25-resolved) `Q24` governs the batch a program
  processes, not the configuration telling it what to process. With a half-valid config, what the
  program was asked to do is unknown, so the gate raises on the first malformed entry and the
  program exits. Degrading there would run the job the operator did not ask for.

## Module state

- **`global` marks a side effect, not a dependency.** Declare it when a function *mutates* module
  state. A read is exempt. (R2b-G1)

- Python already forces `global` to rebind. Python does not police in-place mutation, and no linter
  catches it: `CONFIG.clear()`, `CONFIG['k'] = v`, `CONFIG.attr = v`. That is `NAR001`.

- `NAR001` also counts a call to a method whose name starts with a configuration verb, such as
  `set`, `add`, `register` or `close`. So a function that calls `LOG.addHandler(...)` declares
  `global LOG` even though it never rebinds it. (V-03)

- Every attribute declared in `__init__`. `hasattr(self, ...)` is a red flag. (Q04)

## The module docstring

**Every module opens with a docstring. Anything runnable has a usage example.** A reader meets it
first, before `main()`, so it carries what the program is *for*, not how it works. (R5-02, NAR009)

**Write for a professional developer who has the file open.** That reader knows the language and the
vocabulary of the trade, so `API`, `idempotent` and `tuple` are the right words and a plain-English
circumlocution around them is worse. One idea per sentence. **One word for one thing, and the word
is the identifier the code uses** — `unassigned` in a docstring where the code has `unattributed`
sends a reader to grep for something that is not there. (R9-09)

The prose rules for comments and docstrings are in **Comments**.

```python
"""Load a CSV file into a SQLite table.

Each column is typed from its values as INTEGER, REAL or TEXT. A row that does not fit the
inferred types is skipped and reported. The program does not modify an existing table.

Usage:
    $ python3 load_csv.py readings.csv readings.db measurements
    $ python3 load_csv.py readings.csv readings.db measurements --sample-rows 200

Exit codes:
    0  every row loaded
    1  one or more rows skipped
    2  the file, the database or the arguments were unusable
"""
```

Required:

- what it does
- an example invocation per meaningful mode
- exit codes when there are more than two
- the shape of input and output where it is not obvious from the arguments

`NAR009` enforces the docstring. For a module with a `__main__` block, `NAR009` also enforces the
example.

### Show the thing, do not describe it

**Where a module reads or writes concrete text, paste a real sample of that text.** A rendered
table, a log line, a report, a converted value, an input format. **Delete the prose the sample
replaces** rather than keeping both. (R9-08)

**Never invent a sample.** Run the program and paste what it printed, or paste the `repr` of what
the function returned. A format that appears nowhere in the program is a lie in the shape of
documentation, and it is worse than the prose it replaced, because a reader cannot tell an invented
sample from a real one. This is the docstring case of the boundary rule above: **do not state what
you did not observe.** A module that computes records rather than rendering text pastes the records.

**Show one line of each shape, not the whole output.** One team row, one over-quota line, one file
outcome, and no repeats. The reader needs every shape the module can emit and needs no volume.

**A sample goes stale and no tool checks it.** Keep it small, and re-paste it when the output
changes.

**Expect it to cost lines.** The sample buys exactness, not brevity: a reader learns
the column order, the units and the alignment from three rows of a table and cannot learn them from
a sentence about the table having columns.

```python
"""Format the result of a reconciliation as a table for a terminal.

    TEAM              USED     QUOTA   OVERAGE
    platform        550.0G    500.0G     50.0G
    archive         120.0G    100.0G     20.0G
    search            1.2T      2.0T         -

Teams over quota come first, worst first. A team within its quota shows `-`.
"""
```

**Keep at least one line of the body at column 0**, as the last line above does. `ruff format`
strips the common leading indent from a docstring body, so a docstring whose body is *entirely*
indented gets flattened and the sample loses its alignment. One unindented line anchors it.
`tooling.md` records the check.

Not this, which is the same table said slowly:

```python
"""Format the result of a reconciliation as a table for a terminal.

The table holds one row for each team, then the largest paths of each team above its quota, then
the bytes that no team owns, then the outcome of every file. Every size carries a unit suffix.
"""
```

A conversion takes a table of cases rather than a sentence per case:

```python
"""Convert a size with a unit suffix to a count of bytes, and back.

    4096   ->          4096
    12K    ->         12288
    1.5G   ->    1610612736
    2T     -> 2199023255552

A unit is a power of 1024. A number with no suffix is a count of bytes.
"""
```

### What a body may say, and what it may not

The summary line is mandatory. **A body is not, and usually does not earn its place.** (R9-09)

**Cut a sentence when any of these is true:**

- **It is visible in the file.** `frozen=True` is on the line above. `| None` is in the signature.
  A reader who has the file open does not need either restated.
- **Its negation would be a bug, an absurdity, or an implementation nobody would ship.** Negate the
  sentence and read it back. `it never holds a value that the file did not state` negates to a bug.
  `An empty line holds nothing` negates to an absurdity. `Other files are skipped, so the quota file
  can share the directory` negates to a scanner that dies on a stray file, which nobody would ship.
  All three are free sentences and all three go. **Assume the reader expects competent code, and
  document only the departures.**
- **It is a language feature, explained.** `Such a field holds None` repeats what optional means.
- **It goes stale and nothing checks it**, unless it is a sample you accept that cost for.

**Compress what survives:**

- **Name the property, do not explain it.** `Rows are keyed on team, total and quota, so runs are
  idempotent` replaces three sentences describing idempotence.
- **State an ordering as its sort key.** Prose about a multi-level sort cannot say whether it is one
  composite key or two separate sorts. `Teams sort by (-over, -used, team); the paths inside a team
  sort by (-size, path)` says which, and shows that the tie-break on `team` runs ascending while the
  numbers run descending. In prose, the same information is longer than the key.
- **In the summary line, call what the code produces by its real name.** `Read the quota file, and
  construct a QuotaPolicy accordingly` beats `Read the quota file, and answer what it states about a
  team and about a path`, a paraphrase of a type that already has a name.
- **Stop at the fact.** `The first malformed field stops the read.` is the rule. A following
  sentence on why stopping is right is not functionality. This is `R9-02` one step further in: the
  ban is not only on style-guide justification but on justifying the design at all. Where a reason
  has to survive, it is a `#` comment at the line it concerns.

**A body earns its place for these, and in practice for nothing else:**

- an **ordering or tie-break**, which is invisible without reading a sort key
- a **unit, a nullability or a provenance** absent from the annotation — `Sizes are plain byte
  counts`, `host is null when the entry's report has no host`
- **where the leftover, default and failure cases go**. Most awkward docstrings are awkward because
  they circle an unstated default.
- a **sample** of concrete text the module reads or writes
- a **constraint from outside the program** — `the standard formatter of logging discards extra`
- a **guarantee a caller needs** — `The call writes no file, prints nothing, and records nothing`

- **A function gets a docstring when its contract is complex**: it takes more than three parameters,
  or it exceeds 20 lines. Below both, the contract goes in `#` comments. Raising is not a trigger,
  because the style routes raise sites through a `reject*()` helper and every two-line guard that
  calls one contains a `raise`. (Q05, R2-03, R2-05, R5-05, R8-D18-resolved)

  The trigger is contract complexity rather than length alone, which is why the parameter count sits
  beside the line count. A bare line threshold would reward fragmentation: splitting a 21-line
  function into two 12-line ones deletes the obligation without simplifying either contract.

- **The docstring has a summary and a `Raises:` section. It has `Args:` and `Returns:` only where
  they give a fact absent from the signature.** `NAR004` enforces `Raises:`, because an exception is
  the one part of a contract absent from every annotation. (R8-D28-resolved)

  Write `Returns:` for an ordering, a nullability, a unit, or a count whose meaning is not obvious:
  `The number of rows this call added, which is 0 on a repeat run.` Do not write `The parsed policy`
  above `-> Policy`. Write an `Args:` entry for a parameter the body does not consume in the obvious
  way: `manifest: Where the text came from, for the rejection message.` Do not write
  `path: The file to read.`

  A section that duplicates the module docstring is worse than an absent one. When the exit codes
  are already in the module docstring, leave them out of the docstring of `main()`.

- Write nothing in a docstring that the code does not do, and no consequence that an earlier
  sentence already implies. (Q05)

- **A docstring is about its file alone.** Do not assert what another module does, do not claim to
  be the only place something happens, and do not count callers.
  `nothing outside this module imports sqlite3` and `this is the one place that builds it` are
  claims that no tool checks and that the next commit falsifies. Name another module only where a
  reader of *this* file needs the name in order to use this file. (R9-02)

- Where semantics vary by implementation (file moves, copies, path manipulation), **show a
  concrete before/after example**, not prose. (R3a-11)

## Comments

**Test: what information does this comment provide over the code itself?** (R10-Q25)

These rules cover docstring prose too. (R10-docstrings)

**Comments are not thinking traces.** While writing, you reasoned through edge cases, alternatives
and spec gaps. That reasoning is a thinking trace: it belongs in your report to the user, not in
the code. (R10-stance)

**Cut a comment whose content a smart reader would get from the code below it (including variable
names), no matter how the comment is phrased or what rule category it seems to fit.**
(R10-restatement-gate)

Before writing or rewording a comment, in order:

1. **Rename first.** If the information fits in a name or a type, rename and write no comment:
   `over_quota: ByteCount`, `total_cents`, `rollingMeanSignedError`. (R10-Q25, R10-Q27, R10-Q16)
2. **Guarantee it in code.** Establish a cheap precondition, such as sorted input, upstream in the
   call flow, and write no comment. Not in the function that depends on it: an index lookup doesn't
   sort its input. A comment warning of a trap the code could remove: remove the trap instead. If
   explaining how the code works takes more than one plain clause, rewrite the code instead: name
   the step, or use the obvious construct. A `dict` filled with `setdefault()` and sliced by
   insertion order becomes an explicit loop that counts periods. (R10-Q19, R10-footgun,
   R10-hard-comment)
3. **Match a kind.** Write a comment only if it is one of the four **Comment kinds**, passes that
   kind's test, and is not under **Never**. Deleting is a valid outcome of a rewrite.
4. **Set the depth and sentence form** by **Depth** and **Sentence form**.

**When shortening an existing comment, rewrite the sentence. Do not delete words from it until it
fits.** (R10-cleanup-rewrite)

**Comment kinds:** (R10-topic-lists, R10-fp-fn, R10-kinds)

- **Source**: a fact or requirement from outside the code. Test: it would still be true if the code
  were deleted, and a smart reader wouldn't already know it.
  (R10-Q10, R10-Q14, R10-Q23, R10-Q34, R10-Q43, R10-Q48, R10-Q51, R10-business-case, R10-audience)
  - `# vendor closes idle sockets at 60 s`
  - `# finance signs off each team's bill separately, so one file per team`
  - `# databases written before 2025/04/03 lack the account_id column`
  - `WARN_THRESHOLD = 1.6  # calibration spec CAL-7, section 3`
  - `# handles millions of rows`, at the top of the function
- **Fence**: code that looks unusual, where the obvious simplification silently breaks it. Test: name
  the simplification a smart, experienced developer would make, and the defect it causes: a wrong
  result, a crash, a security hole or a performance collapse. A cosmetic difference doesn't count,
  and neither does adding a feature. Say what the fact forces in the code.
  (R10-Q20, R10-Q42, R10-Q44, R10-Q45, R10-Q50, R10-Q53, R10-Q55, R10-fence-consequence)
  - `# without the bool test, JSON true passes as 1`, not `# JSON true is a Python int`
  - `# constant-time comparison to avoid timing attacks`
  - `# walk backwards so deleting an item doesn't shift the indexes still to visit`
  - `# migrate before load: load reads the account_id column`
  - not `# file can change between calls, so not cached`: a cache is a feature, not a simplification
- **Decoding aid**: a line a smart reader would need docs or a worked example to read. Test: you'd
  look it up. State the intent, not the mechanism. (R10-Q42, R10-Q46)
  - `SIZE_PATTERN = re.compile(...)  # number, then an optional binary unit suffix`
  - `# fsum() for accurate floating point math`
- **Marker**: no test needed. (R10-candor, R10-Q03, R10-Q05, R10-Q36, R10-Q38, R6-12, R8-block-comments)
  - `FIXME:` incorrect behaviour, or behaviour that breaks soon after deploy. In reachable code it
    blocks the merge (`NAR010`). In code nothing calls, it is a warning to whoever wires that code
    in. Every function of a module with no `main` and no `__main__` block counts as reachable.
    (R8-D02)
  - `TODO:` tech debt, future improvement
  - a stated assumption: `# vendor documents no encoding, UTF-8 assumed`
  - a label on a block of at least 4 lines, ideally 6 or more: `# parse data` (R10-block-label-size)
  - a rule a developer must enforce, with capitals scaled to the cost of breaking it:
    `# read-only: NEVER write to the audited readings`

**Never, even when a kind's test passes:**
- what the next line or a single call does (R10-Q01, R10-Q06, R10-Q39, R10-Q47, R10-Q54)
- standard library or language behaviour the reader knows: `<=`, case sensitivity, `None` (R10-Q19, R10-Q21, R10-Q26, R10-Q49)
- why the file follows this style guide: `so this is a class and not a module` (R9-02, R10-Q01)
- decision ids such as `(Q08)` (R7-D04-comments, `NAR012`)
- changelog: an earlier state of the code, or a fixed bug with nothing left of it (R10-Q04, R10-Q08, R10-Q52, `NAR015`)
- alternatives never in the code (`rather than`, `instead of`), except in architecture discussion (R10-Q07, R10-rather-than)
- risks far outside the task's scale, and decisions too inconsequential for a later reader to reconsider (R10-Q13, R10-rating)
- future needs nobody has documented or planned (R10-Q15)
- reassurance that a weakness is fine; `deliberately`, `on purpose` (R10-candor, R10-Q20, `NAR014`)
- guarantees about other modules. Put them in the project's architecture document. (R10-Q24, R10-Q11, R10-other-modules)
- how one function uses a type, written on the type: `member order is the order plan.json lists a
  snapshot's rules` belongs with the function that writes plan.json, or nowhere if the order is
  already plain in that function (R10-usage-placement)
- illustrations of a decision just discussed in the session (R10-Q21)
- a function's return contract. State it in the docstring, and only if the return type doesn't make it obvious. (R10-return-contract, `NAR019`)

**Depth:** in proportion to the idea's difficulty for the reader. `# signed error` on a rolling
mean, more on a novel method. When the reader needs the consequence or the action as well as the
fact, write a second sentence, as a block of full sentences:
```python
# The vendor API returns at most 100 rows per page and no total count.
# Keep requesting until a page comes back short.
while len(page := fetchPage(cursor)) == PAGE_SIZE:
```
A one-line comment stays one clause. (R10-Q16, R10-seed-2, R10-depth-sentences, R10-depth-example)

**Sentence form:**
- a one-line `#` comment: lowercase start, no period. Several lines, and every docstring: sentences. (R10-Q26, R10-Q35, R10-docstrings)
- terse: drop articles where nothing is lost, never the subject or the verb (R10-seed-10, R10-terse-narrow)
- every clause has a subject and a verb. A label naming the thing is fine: `# least recently used
  first`, `Exact, case-sensitive comparison.` A predicate with its subject cut is not:
  `Bound to one machine` → `The modifier is bound to one machine`, and
  `Named, so a recreated container gets it back` → `The volume is named, so a recreated container
  gets it back`. (R10-subject-verb, `NAR020`)
- possessives and noun compounds over relative clauses: `the archive's collections`, `in read order` (R10-seed-1, R10-seed-9, R10-Q32)
- trade terms over paraphrase: `has no side effects`. Modifiers before the noun: `JSONL logs`. (R10-seed-3, R10-seed-4)
- the conclusion, not the derivation: state what the code means, not how it gets there.
  `None when malformed`, not `None when a malformed line names no customer as a string`. Cut a
  clause about an internal check, structure or attribute unless the reader needs it to act.
  (R10-conclusion)
- no intensifiers: drop a word that only stresses, such as `exactly`, `always`, `precisely` or
  `simply`. Keep it when the sentence means something else without it: `exactly two decimal places`.
  (R10-intensifiers)
- the full term when a short form is ambiguous: `timezone`, not `zone` (R10-clipped-terms)
- contractions; imperative; no `we` (R10-Q28, R10-Q29)
- callables as `name()`; no article before an identifier (R10-Q30, R10-Q35)
- only names the reader can resolve from the comment's position (R10-Q22, R10-Q21)
- with code or an abstract noun as the subject, only verbs for what code literally does: `returns`,
  `raises`, `reads`, `writes`, `calls`, `skips`. Never agency or containment: `finds`, `knows`,
  `holds`, `carries`, `keeps its`, `costs`. Write `a module has one function`, not
  `a module holding one function`. These words are examples; the test is whether the subject can
  perform the verb. (R10-Q31, R10-Q39, R10-seed-1, R10-seed-6, R10-seed-15, R10-skill-gaps)
- no `is what`, no `its own` (R10-Q40, R10-Q41, `NAR018`)
- the general case: `records are separated by blank lines`, not `two records` (R10-Q40)
- a worked example matches what the code does for every case in it: not `with a->b and b->c,
  a and c compare unequal` when a and b also compare unequal (R10-worked-example)
- no semicolon and no dash: write two sentences (R10-no-semicolon, `NAR013`)
- a Fence as what the simpler code would do wrong: `# without the bool test, JSON true passes as 1`,
  `# isdigit() alone admits non-ASCII digits such as '²'`. Code the file doesn't run takes `would`:
  `# read_text() would translate newlines, which alters a newline quoted inside a CSV field` (R10-fence-form)
- directly above the statement it concerns, not above its enclosing block: inside `try:`, above the
  call it concerns, not above `try:`. A comment on an argument goes above the call that passes it:
  above `pendulum.parse(raw_at, tz=None)`, not below the `try` block. End-of-line for a short note.
  (R10-Q34, R10-locality, R10-fence-form, R10-argument-placement)

`NAR012` to `NAR016` and `NAR018` flag six wording faults in comments and docstrings, and a clean run is no
evidence about the rest of these lists. Check every comment and docstring you write or touch against
them. A dash after a list-item term is allowed. `NAR015` also flags `no longer` about data; such a
sentence usually gives data an agent verb, so reword it. Silence a false positive with
`# noqa: NARxxx`. (R10-lint, R10-skill-gaps, R10-list-dash, R10-nar015-scope, R10-nar016, R10-nar018)

`NAR017` is an agent verb on a subject that cannot act: a noun that is not a person, with a verb for
something only a mind does (`a period ranks`, `the report names it`, `a policy can judge`).
Documents get no exception: write `named in the report`. It comes from `agentverbs.py`, the seventh
check in `verify.py`. The check parses each sentence, and some noun compounds and participles are
flagged by mistake. Silence those with `# noqa: NAR017`. (R10-agentverb-check)

`NAR020`, from the same check, is a clause with no subject before `, so`: `Named, so a recreated
container gets it back`. It flags only that form. Check every other clause against the subject and
verb rule in **Sentence form** by hand. (R10-subject-verb, R10-nar020)

**Before you finish, read the list `verify.py` prints after a passing run**: every comment and
docstring summary in the code. For each one, name the subject and the verb and ask whether that
subject can perform that verb. Then test the sentence against **Sentence form** and the comment
against the restatement gate. Fix what fails and run `verify.py` again. (R10-prose-inventory)

## Logging

One stable event name plus structured `extra={...}` fields, never an f-string of prose. The
message is a queryable key. (Q08)

**Get each module's logger with `logging.getLogger(__name__)`.** In a package used as a library, add
`logging.NullHandler()` to the package logger once, in its top-level `__init__.py`. Without it, the
last-resort handler prints the package's warnings to stderr in a program that configures no logging.
In a program, configure logging once, in `main()`, and add no NullHandler. (R10-nullhandler)

**JSONL output is for a service, not for every script. Decide by who reads the logs.** (R5-03,
R8-D23-resolved) A collector that queries them wants JSONL; a person at a terminal does not.

- **A service, or any program whose logs someone collects**: JSONL, from a shared module. In a
  monorepo each program imports it and never re-pastes it. That is what makes it worth having.

- **A single-file tool run by hand**: the short field formatter below.

**Do not use `basicConfig(format='%(levelname)s %(message)s')`.** The standard formatter discards
everything in `extra`. `LOG.warning('merge.rejected', extra={'rejected': 4812, 'total': 10000})`
then prints `WARNING merge.rejected`, and the operator never sees the number that the tally rule
exists to give them. Follow the event-name rule with that formatter and the logs are worse than an
f-string. (R5-09)

```python
_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')


class FieldFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD}
        located = {key: getattr(record, key) for key in _LOCATION}
        fields = ' '.join(f'{k}={v}' for k, v in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'
```

That prints `WARNING merge.rejected funcName=merge lineno=88 module=loader rejected=4812
total=10000`, which is the tally an operator acts on and the location of the call site.

## Configuration

Most explicit first:

1. **A config file tracked in the repo**, parsed into a frozen dataclass. This is the default for
   any deployment setting. Infrastructure becomes code-defined and diffable. (R3a-02)

2. **CLI arguments** for the inputs of a batch tool invoked by hand. `argparse`.

3. **Environment** for secrets and DB URLs, via `python-decouple`, not `os.environ`. (R2-06)

4. **`ALL_CAPS` constants** for tuning knobs that do not vary by deployment.

## Concurrency

asyncio is the default for I/O-bound work. (R2-04)

## Testing

- **Real dependencies**: a real socket on loopback, a real temp SQLite file, a real temp directory.
  A test double is a last resort for something you genuinely cannot run. Flag each one as a known
  gap. A fake transport produces tests that pass while production fails. (R2-02, Q16)

- **Property-based tests (hypothesis) wherever there is an invariant**: round-trips, ordering,
  conservation, numeric range. Example-based tests cover specific regressions on top. A very slow
  stateful property test may be opt-in rather than run in CI. (R2-12)

- **Test functions are `testSomethingDescriptive`**, in camelCase with a `test` prefix. The
  conventional `test_parse_header_roundtrips` fails the `mixedCase` gate this style mandates. The
  camelCase spelling passes pylint, *and* the pytest default `python_functions = test*` still
  collects it.

- Tests live in their own module, not in the program file. A `from hypothesis import given` at
  module scope makes the program raise `ModuleNotFoundError` before it reaches `main()` on any
  machine without the test library.

  Where a single file is genuinely required, put the tests behind `### tests` before the
  `### vocabulary` divider and import hypothesis lazily.

## Python 3.11 floor

`ruff` targets `py311`. Check with `vermin -t=3.11- --violations`. (R7-E07-floor)

Supervise several long-lived tasks with `asyncio.TaskGroup`. Hand-rolled cancellation fails
silently.

- **`except TimeoutError` is correct** around `asyncio.wait_for`. At 3.11 `asyncio.TimeoutError`
  *is* the builtin, so the two are one class. (R3a-06)

- Not available, so out: anything added in 3.12 or later, including the `type` statement and
  PEP 695 generics.

## Verify

Run `verify.py`. Do not call the tools by hand.

```
python3 verify.py .
```

Give it any path, and every Python file below it is checked.

It resolves every tool to an absolute path and exits 2 if one is missing or if `pyproject.toml` is
absent. **Do not replace it with a loop that greps tool output for findings**: a missing binary or a
missing config then produces empty output, which reads as a pass.

It runs, in the order that converges: `ruff check --fix`, `ruff format`, `pylint`, `mypy --strict`,
`checks.py`, `vermin`, `agentverbs.py`. A passing run ends with a list of every comment and
docstring summary (**Comments**).

| exit | meaning |
|---|---|
| 0 | every tool passed |
| 1 | at least one tool reported a finding |
| 2 | the toolchain or the config is missing, so nothing was checked |

The job of each layer and the gotchas are in `tooling.md`. A tool default silently
undoes several rules here. `ruff check --fix` collapses blank lines after imports, and `SIM114`
merges branches in a way that loses type narrowing. Read `tooling.md` before you change config.
