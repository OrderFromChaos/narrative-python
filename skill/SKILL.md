---
name: narrative
description: Write or review Python in the Narrative house style — mixedCase functions, main() first with types last, parse-at-the-boundary dataclasses, no ORM, explicit global on mutation, exhaustive match without a fallback arm, and a verified ruff/pylint/mypy toolchain. Covers multi-module architecture too: which module may import which, when one file becomes several, what a package __init__.py holds, where a shared type lives, and when to take or contain a third-party dependency. Use for any Python written in or for this codebase, when laying out modules or packages, and when reviewing a diff against this style.
---

# Narrative Python

Rules carry the id of the decision that produced them. Those ids resolve in `benchmark/decisions.jsonl`
in the source repository, `github.com/OrderFromChaos/narrative-python`, which is **not installed with
the skill**. Treat a citation as provenance, not as something to look up: every rule states its own
reason. A rule with no id and no linter behind it does not belong here.

**This document governs every file, however many there are.** Naming, layout, types, errors and
docstrings apply to each module of a package exactly as they apply to a single-file program.

`architecture.md` adds what happens **between** files: which module may import which, where a shared
type lives, when one file becomes several, and what a third-party dependency may touch. Read it when
the program spans more than one module or imports a third-party package. Skip it for a single-file
program, where none of it applies.

## The principle everything else serves

**0% of reader effort on rote diffing, 100% on design.** (R2b-P0)

Four near-identical lines that differ in one token, at a 90% per-line detection rate, give the
reader a 0.9⁴ = 66% chance to see the difference. One parameterised call makes it 90%.

This is the root of DRY, of one-name-for-one-thing, of consistent ordering, and of the ban on
gratuitous variation. When two rules conflict, the rule that spares the reader diffing wins.

Second principle, for representation choices: **prefer what the type checker and IDE can follow**,
even when a looser form is more flexible.

Measurement decides this, not aesthetics. A design that holds state in a `dict[str, Any]` instead
of typed attributes cost 6 `cast()` calls and 15 dict lookups to pass `mypy --strict`. Typed
attributes cost zero. (R3-P2-rank)

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

  **No tool checks this.** `NAR008` used to, on any statement of three or more lines that another
  statement followed, and it was removed: measured against twelve functions stripped of every
  internal blank line and marked up by hand, it wanted 12 blank lines where 23 belonged and agreed
  on 5. Precision 42%, recall 22%. (`R8-NAR008`)

  What the markup showed instead: (`R8-NAR008-rule`)

  - blanks **recur into nested blocks** — one loop body took four
  - **length is not the trigger**, in either direction
  - **a multi-line statement and the statement that consumes its value are one step**, so
    `executemany` then `commit`, and a constructor then the `return` of it, stay adjacent
  - a body of **8 lines or under takes no internal blanks at all**
  - a blank precedes a `return` when the phase before it is unrelated, not when the value was just
    built

- **Label a long or complex block with a short comment.** (`R8-block-comments`) `# parse data`,
  `# execute sql`, `# validate`. This is not the line comment the rule below forbids: a label names
  a group of statements and pairs with the blank line that separates them.

- If a guard grows to three lines because it logs before raising, move the log call into a
  `reject*()` helper that logs and returns the exception. The guards are two lines again and group,
  and the raise-site rule still holds. (R4-05)

- A `def` with >3 **positional** arguments puts each on its own line with a trailing comma, even
  under 120 columns. **Calls are exempt**, because the same rule applied to calls costs +19% lines.
  (R2b-B1)

- **Keyword-only parameters do not count**, so a function may carry as many as it needs. That is
  also the escape hatch at exactly four: put `*` before the optional ones and they stop counting,
  which documents them as optional anyway. Note `NAR004` counts *every* parameter, because each one
  is part of the contract even when the caller may omit it. (R5-06)

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

- If extraction would need 5+ parameters, that is a **missing owner**, not a reason to leave the
  code inline. Find what owns the values. That owner is a **class** when the program could hold two
  of it, and a **module** otherwise. A frozen record is the answer only when nothing has behaviour
  over the values. If a general name for the group is hard to pick, it is not a real grouping.
  (R7-C05-resolved, R7-C05-naming)

- Always collapse duplicated-but-drifting code, even when the shared version needs a parameter. To
  localise the difference is the whole point. (R2b-E4)

- Mixed `and`/`or` parenthesises each group explicitly. Never `A and B or C and D`. Ruff cannot
  produce this form, so `SIM114` is disabled and `NAR007` enforces it. (R2b-B4)

- Merge branches that share a body **only where the type checker keeps its narrowing.** If you
  merge two `isinstance` branches, even with parentheses, mypy widens the subject back to a union
  and loses the narrowing. Two explicit branches beat one clever condition. (R2b-B5)

- If it names a path, its type is `Path`, not `str`. (R3a-10)

- Collection literals get one item per line **wherever `ruff format` explodes them**, which is any
  literal it cannot fit on one line. This describes the formatter rather than adding a rule: a short
  literal it leaves packed is already correct. A word-list-shaped literal may use a `# fmt: off` /
  `# fmt: on` fence to stay packed. (R2b-B2)

## Naming

- Module filenames `snake_case`. Functions and methods `mixedCase`. Classes and types
  `PascalCase`. Variables and arguments `snake_case`. Module constants `ALL_CAPS`. **In a
  `snake_case` codebase that you did not write, match local convention.** Detect before you write.

- Spell names out. No `img_arr`, `cfg`, `idx`. (Q11)

- Never restate the type in a parameter name: `config: RebinConfig`, not
  `rebin_config: RebinConfig`. (Q11)

- Predicates are bare adjectives: `readyForScan`, not `isReadyForScan`. (Q12)

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

*This is not lintable. The test "used by exactly one function" flags 14 of 16 constants, including
the ones that should stay out. This is review judgement.*

## Types

- Annotate every parameter and return. `mypy strict = true`, `disallow_any_explicit` left **off**
  so a written `Any` is a visible, greppable admission. (R2-11)

- Annotate the true requirement, not a habitual container: a body that only iterates takes
  `Iterable`, not `list`. (Q13)

- `NewType` for domain primitives (`ScanId`, `SampleRef`), so a bare `int` is a type error. (Q15)

- `Enum` for closed sets, `.value` at serialisation boundaries. Not `Literal`, not `StrEnum`. (R2-08)

- `Protocol` for a seam with more than one real implementation. Never `ABC`, because that is
  inheritance. (R2-01)

- **An annotation you cannot say out loud needs a name.** The test is conversational: could you
  refer to this type in a normal discussion with another programmer? `park(car: Car)` reads and
  discusses. `park(car: dict[str, list[tuple[float, float]]])` does neither. (NAR005, R8-D27-resolved)

  **One measure: how many things it names, below the outermost.** `Car` names none.
  `dict[str, list[tuple[float, float]]]` names five, and above four the annotation wants a name.
  A callable becomes a `Protocol`; anything else becomes a dataclass. (`NAR005`, `R8-D27`)

  Depth and width were two proxies for that one question and each missed what the other saw. Depth
  let `Callable[[Callable[[Job], Result]], Callable[[Job], Result]]` through; width let
  `tuple[dict[str, str], list[str]]` through. Counting names catches both, misses nothing either
  caught, and needs one number rather than two.

  **The DB-API is the standing exception.** `sqlite3.executemany` takes a sequence per row, so
  `list[tuple[str, str, float, float, int, int]]` names seven things and has no dataclass form —
  passing one raises `ProgrammingError: parameters are of unsupported type`. Give the row shape a
  named alias so it reads, and suppress the finding with that reason. (`R8-D27`)

  The type then decides the fix. **A callable becomes a `Protocol`.** **Anything else — any kind of
  iterable — becomes a dataclass.**

  The reason is comprehension and shared vocabulary, not type safety. Measured: neither
  `tuple[float, float]` nor a `Point` dataclass makes `mypy --strict` catch swapped coordinates.
  Only `NewType` does that, and it is a separate rule (Q15). Do not expect the dataclass to find a
  bug. Expect it to give the thing a name.

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

When you omit `case _`, mypy catches a new variant. **A `case _: raise RuntimeError(...)`
one-liner looks equivalent and is not. It type-checks clean and silently accepts the missing
case.** No helper, no `assert_never`. (Q18, R3a-07)

Limitation: this works only when the match returns a value. A side-effecting `-> None` dispatch
gets no protection. Restructure it to return something.

**Keep the `match` even when a mapping looks more natural.** Measured on an ordering lookup, the
`match` is the *only* form where mypy catches a new member. A `dict` lookup and an `IntEnum` both
type-check clean and fail at runtime with `KeyError`.

The performance objection does not survive measurement either. The mapping is 15% faster per call
(119.8 vs 141.7 ns), and a function-local dict is **6.4× slower**. End-to-end, the spread between
forms is smaller than run-to-run noise. (R4-03)

`IntEnum` is not a substitute. It makes `json.dumps({'level': LogLevel.INFO})` silently emit `20`
where a plain `Enum` raises `TypeError`, and its `str()` changed across releases. **`StrEnum` is
available at the 3.11 floor and is not a substitute either**, for the same reason: it serialises
silently where a plain `Enum` makes the boundary explicit. Keep the plain `Enum` and the exhaustive
`match`. (R4-03, R7-E07-floor)

## Data at boundaries

- Parse untrusted input into a **frozen dataclass at one boundary gate**, then never validate
  again. The objection to Pydantic/ORMs is *pervasive runtime validation*, not a single gate.
  (Q14, Q17)

- The config enforces that **more bluntly than the rationale**. `TID251` bans the `pydantic` import
  outright, because a linter cannot see whether a model is used once at a gate or on every request.
  A genuine single-gate use is therefore a per-module `# ruff: noqa: TID251` with the gate named in
  the module docstring. Writing that suppression twice in one program means the validation is no
  longer at one gate. (R8-D10)

- **`frozen=True` is the default for every dataclass.** It has nothing to do with boundaries: a
  record built and consumed inside one function is frozen for the same reason a parsed one is.
  (R8-D11-resolved)

- Drop to mutable only when a **field holds a mutable value**, and treat that as a smell rather than
  a decision. Reach for a `tuple` where you would write a `list`. A frozen wrapper around mutable
  contents is a half-guarantee: `dataclasses` will not stop you writing through it, so the bug grows
  quietly and surfaces at run time with nothing to catch it. The standing exception is the
  schemaless remainder below, where a `Mapping` field is the prescribed shape and its cost is
  already recorded.

- A dataclass, never a dict of parsed fields. (Q02) That rule is about **what holds the record**,
  not about what type a field may have. A mapping-typed *field* is fine.

- **Genuinely schemaless input**: promote the fields the program actually computes on to typed
  attributes, and put the remainder in one `Mapping[str, object]` field. To flatten it to a JSON
  string costs a second `json.loads` downstream, makes it unaddressable by `jq`, and forces the
  reader back through `Any`. (R4-04)

  This creates two traps, both verified:

  - **Never splat the remainder into an output record.** `{'source': path, **entry.extra}` lets an
    untrusted log line that carries its own `source` key **forge its provenance in your report**.
    Nest it: `{'source': path, 'extra': dict(entry.extra)}`.

  - `frozen=True` plus a mapping field is **not hashable**. `set(entries)` raises `TypeError` at
    runtime with no linter warning. Fine until someone dedupes.

- **No ORM on a hot path.** A request handler that returns database values must not pay run-time
  validation for information the database and Python both already know. Use `sqlite3` and SQL.
  (Q17, R6-03)
- **An ORM is a fine tool off the hot path.** A healing script, a migration or a one-off backfill
  runs once, so developer time outweighs per-request cost. **The module that needs the exception
  declares it**, with a file-level `# ruff: noqa: TID251`. There is no `per-file-ignores` list: an
  exception is a property of the module, not of a glob that drifts from the tree it describes.
  Conformance owes no explanation, so the suppression stands bare. (R6-07, R7-D04,
  R7-D04-generalised)

## Errors

- Custom exception types subclassing `RuntimeError`, not `Exception`. (Q20)
- **The name ends in `Error`.** Ruff `N818` enforces this and rejects `SourceRejected`. Use
  `RejectedSourceError`.

- Handle each failure mode narrowly and separately. Never one `try` around the whole operation with
  a tuple of unrelated exception types. (Q19)

- **Related means the handling is the same, not that the classes share a base.** Where two failures
  genuinely produce one outcome, one `except (A, B)` arm is correct and two identical arms are the
  rote diffing the top principle forbids. But check the premise first: two arms that look identical
  usually should not be. A timeout and an unreachable host are different facts and deserve different
  words, and writing the same string twice is how that gets lost. (R8-D24-resolved)

- `raise NewError(...) from exc`, **and** log it. Both. (Q21)

- **The raise site records the generic fact once, however you factor that.** A parser with six
  raise sites does not get six log statements. Route them through a helper that logs and returns
  the exception, then `raise rejectLine(...) from exc`. Verified: the helper and six inline logs
  emit byte-identical records, and the helper costs 13 fewer lines. (Q23, R4-02)

- **The handle site records what it meant here, but in a degrade-and-report loop it logs the
  aggregate, not the item.** This is the rule that matters. Per-item handle-site logging on a file
  with 10,000 bad lines emitted **10,023 records / 3.2 MB**. To log the item at DEBUG and a
  per-file tally at WARNING gave **24 records / 1.2 KB** with nothing lost under `--verbose`. (R4-02)

- **Level follows from what an operator can act on**: a per-item failure is DEBUG, the tally is
  WARNING. An operator cannot act on line 4,812 of one file. An operator can act on "4,812 of
  10,000 lines rejected". (R4-02)

- LBYL over EAFP: you know your own invariants, you do not know every exception an implementation
  can raise. (Q22)

- Degrade and report: process the whole batch, collect failures, log a summary, exit nonzero. Never
  abort on the first bad item. (Q24)

- **The config gate is the exception.** (R8-D25-resolved) `Q24` governs the batch a program processes, not
  the configuration telling it what to process. A half-valid config means the program does not know
  what it was asked to do, so the gate raises on the first malformed entry and the program exits.
  Degrading there would run the job the operator did not ask for.

## Module state

- **`global` marks a side effect, not a dependency.** Declare it when a function *mutates* module
  state. A read is exempt. (R2b-G1)

- Python already forces `global` to rebind. Python does not police in-place mutation, and no linter
  catches it: `CONFIG.clear()`, `CONFIG['k'] = v`, `CONFIG.attr = v`. That is `NAR001`.

- **The check goes further than those three forms.** It also matches any method whose name *starts
  with* a configuration verb: `set`, `add`, `remove`, `register`, `unregister`, `reset`, `delete`,
  `insert`, `enable`, `disable`, `configure`, `install`, `attach`, `detach`, `bind`, `unbind`,
  `truncate`, `flush`, `commit`, `rollback`, `execute`, `close`. So `LOG.addHandler(...)` is a
  mutation, and a function that configures a module-level logger declares `global LOG` even though
  it never rebinds it. The check under-reports rather than crying wolf: a domain method can mutate
  without saying so in its name. (V-03)

- Every attribute declared in `__init__`. `hasattr(self, ...)` is a red flag. (Q04)

## The module docstring

**Every module opens with a docstring. Anything runnable shows how to run it.** A reader meets it
first, before `main()`, so it carries what the program is *for*, not how it works. (R5-02, NAR009)

Write it in **STE** (ASD-STE100): one idea per sentence, active voice, one word for one thing, no
synonyms. Use the `ste-writing` skill in **STE-flavored** mode if it is installed. Check with
`python3 ~/.claude/skills/ste-writing/ste-lint.py <file>`.

This is the one place in the file where prose quality is load-bearing. STE governs docstrings and
comments, never code or identifiers.

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

- A function gets a full structured docstring (summary, Args, Returns, Raises) when its **contract
  is complex**: it takes more than three parameters, or exceeds 20 lines. Below both, `#` comments
  carry the contract. (Q05, R2-03, R2-05, R5-05)

- **Raising is not a trigger.** It was, and it fired hardest on the simplest functions: the style
  routes raise sites through a `reject*()` helper, so every two-line guard that calls one contains a
  `raise`. Measured at +61 lines of docstring in one 124-line module, most of it restating the
  signature. (R8-D18-resolved)

- Of the four sections, `NAR004` enforces **`Raises:` only**, and only on a function the trigger
  already caught. `Args:` and `Returns:` restate what the signature says; a raise names something no
  annotation carries. Write the other sections where they earn their place. (R8-D28-resolved)

  A bare line threshold is gameable in the wrong direction. To split a 21-line function into two
  12-line ones would delete the obligation, so the rule would reward fragmentation. Contract
  complexity does not shrink when you split: the pieces still raise, and they still take their
  parameters.

- A docstring must not assert anything the code does not do, and must not state a consequence it
  already implied. (Q05)

- Where semantics vary by implementation (file moves, copies, path manipulation), **show a
  concrete before/after example**, not prose. (R3a-11)

- Comments carry the why, the tribal knowledge, the link to the source. Never restate the line.

- **`TODO:` marks deferred work.** It never blocks a merge.

- **`FIXME:` means one of two things, and only one of them may merge.** (R6-12, NAR010)
  - In code that runs, a `FIXME` is a **merge blocker**. `NAR010` fails the gate on it.
  - In code that nothing calls, a `FIXME` is a **danger sign**. It marks a known correctness
    problem parked in an orphaned section, for whoever next considers wiring that section into the
    hot loop. This use is allowed, and it is the reason the marker exists.

  Reachability separates the two, so `NAR010` walks the call graph from `main` and from module
  level. It over-approximates reachability on purpose. The check would rather call an orphan live
  than let a running `FIXME` through.

  **A module with no `main` and no `__main__` block is a library module**, and every function in it
  counts as reachable, because its callers sit in files this per-file checker never sees. Without
  that, splitting a program was what switched the check off: a helper called only from
  `__main__.py` looked orphaned in its own file and a live marker passed the gate. (R8-D02)

## Logging

One stable event name plus structured `extra={...}` fields, never an f-string of prose. The
message is a queryable key. (Q08)

**JSONL output is for a service, not for every script. Decide by who reads the logs.** (R5-03,
R8-D23-resolved) A collector that queries them wants JSONL; a person at a terminal does not.

The line-count argument that used to justify this is dropped. It compared a hand-rolled
`JsonlFormatter` against a field formatter, and both numbers have already moved once. The
hand-rolling is temporary in any case: JSONL logging belongs in an importable library that every
program shares, and then it costs one import.

- **A service, or any program whose logs someone collects**: JSONL, from a shared module. In a
  monorepo each program imports it and never re-pastes it. That is what makes it worth having.

- **A single-file tool run by hand**: a 9-line formatter that renders the fields.

**Do not use `basicConfig(format='%(levelname)s %(message)s')`.** The standard formatter discards
everything in `extra`. `LOG.warning('merge.rejected', extra={'rejected': 4812, 'total': 10000})`
then prints `WARNING merge.rejected`, and the operator never sees the number the tally rule exists
to give them. A cold-start reader followed both rules as written and shipped worse logs than an
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
total=10000`, in 9 lines against the 21 that the
JSONL formatter costs.

## Configuration

Most explicit first:

1. **A config file tracked in the repo**, parsed into a frozen dataclass. This is the default for
   anything that describes a deployment. Infrastructure becomes code-defined and diffable. (R3a-02)

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
  conventional `test_parse_header_roundtrips` fails the `mixedCase` gate this style mandates.
  The camelCase spelling passes pylint, *and* the pytest default `python_functions = test*` still
  collects it. Both verified.

- Tests live in their own module, not in the program file. A `from hypothesis import given` at
  module scope makes the program unable to start without the test library installed. Verified: the
  program raises `ModuleNotFoundError` before it reaches `main()`.

  Where a single file is genuinely required, put the tests behind `### tests` before the
  `### vocabulary` divider and import hypothesis lazily.

## Python 3.11 floor

`ruff` targets `py311`. Check with `vermin -t=3.11- --violations`. (R7-E07-floor)

The floor moved from 3.10 for two reasons, and the second is the stronger. `asyncio.TaskGroup` is the
right tool for supervising several long-lived tasks and hand-rolling its cancellation is what fails
silently — and **3.10 reaches end of life in October 2026**, which is sufficient on its own.

- `datetime.UTC`, `typing.assert_never`, `enum.StrEnum`, `asyncio.TaskGroup`, `asyncio.timeout()`,
  `typing.Self` and `tomllib` are all available. No workaround is needed for any of them.

- **`typing.assert_never` being available does not change the dispatch rule.** Omitting `case _` is
  still the only form where mypy reports a new member; verified. Keep omitting it. (Q18, R3a-07)

- **`except TimeoutError` is now correct** around `asyncio.wait_for`. At 3.11 `asyncio.TimeoutError`
  *is* the builtin, so the two are one class and the old warning no longer applies. Verified.
  (R3a-06, superseded)

- Not yet available, so still out: anything added in 3.12 or later, including the `type` statement
  and PEP 695 generics.

## Avoid the usual traps

Bare `except:`. Mutable default arguments. See `wtfpython` for the rest.

## Verify

Run `verify.py`. Do not call the tools by hand.

```
python3 verify.py .
```

Give it any path. It sorts Python files from prose and runs the right checks on each, so nothing
has to decide a workflow at run time. There is one command, not a sequence to remember.

It resolves every tool to an absolute path and exits 2 if one is missing or if `pyproject.toml` is
absent. A hand-rolled loop counts findings by grepping tool output, so a missing binary or a
missing config produces empty output and reads as a pass. That mistake has happened twice in this
project.

It runs, in the order that converges: `ruff check --fix`, `ruff format`, `pylint`, `mypy --strict`,
`checks.py`, `vermin`.

| exit | meaning |
|---|---|
| 0 | every tool passed |
| 1 | at least one tool reported a finding |
| 2 | the toolchain or the config is missing, so nothing was checked |

`tooling.md` explains what each layer owns and documents the gotchas. A tool default silently
undoes several rules here. `ruff check --fix` collapses blank lines after imports, and `SIM114`
merges branches in a way that loses type narrowing. Read `tooling.md` before you change config.
