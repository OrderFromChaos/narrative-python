---
name: narrative
description: Write or review Python in the Narrative house style — mixedCase functions, main() first with types last, parse-at-the-boundary dataclasses, no ORM, explicit global on mutation, exhaustive match without a fallback arm, and a verified ruff/pylint/mypy toolchain. Covers multi-module architecture too: which module may import which, when one file becomes several, what a package __init__.py holds, where a shared type lives, and when to take or contain a third-party dependency. Use for any Python written in or for this codebase, when laying out modules or packages, and when reviewing a diff against this style.
---

# Narrative Python

Every rule states its own reason, so read the rule and not the id after it. The ids are provenance:
they resolve in `benchmark/decisions.jsonl` in the source repository,
`github.com/OrderFromChaos/narrative-python`, which does not ship with the skill. **A rule with no
id and no linter behind it does not belong here.**

**This document governs every file, however many there are.** Naming, layout, types, errors and
docstrings apply to each module of a package exactly as they apply to a single-file program.

`architecture.md` adds what happens **between** files: which module may import which, where a shared
type lives, when one file becomes several, and what a third-party dependency may touch. Read it when
the program spans more than one module or imports a third-party package. Skip it for a single-file
program, where none of it applies.

## The principle everything else serves

**0% of reader effort on rote diffing, 100% on design.** (R2b-P0)

Four near-identical lines that differ in one token make the reader compare them token by token, and
every comparison is a chance to miss the difference. One parameterised call removes the comparison.

This is the root of DRY, of one-name-for-one-thing, of consistent ordering, and of the ban on
gratuitous variation. When two rules conflict, the rule that spares the reader diffing wins.

Second principle, for representation choices: **prefer what the type checker and IDE can follow**,
even when a looser form is more flexible. State held in a `dict[str, Any]` needs a `cast()` or a
key lookup at every use to pass `mypy --strict`; typed attributes need neither. (R3-P2-rank)

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

  **No tool checks this. Statement length does not decide it, and no threshold on it works.**
  Place a blank line by these five rules: (`R8-NAR008`, `R8-NAR008-rule`)

  - a body of **8 lines or under takes no internal blanks at all**
  - blanks **recur into nested blocks**, and one loop body can take four
  - **a multi-line statement and the statement that consumes its value are one step**, so
    `executemany` then `commit`, and a constructor then the `return` of it, stay adjacent
  - a blank precedes a `return` when the phase before it is unrelated, and not when the returned
    value was just built
  - **length is not the trigger**, in either direction: a long statement earns no blank after it,
    and a short group of statements still earns one before the next group

- **Label a long or complex block with a short comment.** (`R8-block-comments`) `# parse data`,
  `# execute sql`, `# validate`. A label names a group of statements and pairs with the blank line
  that separates them, so it is not the restatement of a single line that the docstring section
  forbids.

- If a guard grows to three lines because it logs before raising, move the log call into a
  `reject*()` helper that logs and returns the exception. The guards are two lines again and group,
  and the raise-site rule still holds. (R4-05)

- A `def` with >3 **positional** arguments puts each on its own line with a trailing comma, even
  under 120 columns. **Calls are exempt**: a signature is read once and a call site is read
  everywhere, so the same rule applied to calls costs lines without buying clarity. (R2b-B1)

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

*No tool checks this, and the obvious proxy does not work: "used by exactly one function" flags
almost every constant, including the ones that belong at module level. This is review judgement.*

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

  Count names rather than nesting depth or argument width. Depth alone admits
  `Callable[[Callable[[Job], Result]], Callable[[Job], Result]]` and width alone admits
  `tuple[dict[str, str], list[str]]`. One number catches both.

  **The DB-API is the standing exception.** `sqlite3.executemany` takes a sequence per row, so
  `list[tuple[str, str, float, float, int, int]]` names seven things and has no dataclass form —
  passing one raises `ProgrammingError: parameters are of unsupported type`. Give the row shape a
  named alias so it reads, and suppress the finding with that reason. (`R8-D27`)

  The type then decides the fix. **A callable becomes a `Protocol`.** **Anything else — any kind of
  iterable — becomes a dataclass.**

  The reason is comprehension and shared vocabulary, not type safety. A `Point` dataclass does not
  make `mypy --strict` catch swapped coordinates, and neither does `tuple[float, float]`; only
  `NewType` does, which is Q15's job. Expect the dataclass to give the thing a name, not to find a
  bug.

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

**Keep the `match` even when a mapping looks more natural.** The `match` is the only form where
mypy catches a new member. A `dict` lookup and an `IntEnum` both type-check clean and fail at run
time with `KeyError`.

Speed does not change this. A module-level mapping is faster than the `match` by tens of
nanoseconds per call and a function-local dict is several times slower than either, so end to end
the spread between the forms is smaller than run-to-run noise. (R4-03)

`IntEnum` is not a substitute. It makes `json.dumps({'level': LogLevel.INFO})` silently emit `20`
where a plain `Enum` raises `TypeError`, and its `str()` changed across releases. **`StrEnum` is
available at the 3.11 floor and is not a substitute either**, for the same reason: it serialises
silently where a plain `Enum` makes the boundary explicit. Keep the plain `Enum` and the exhaustive
`match`. (R4-03, R7-E07-floor)

## Data at boundaries

- Parse untrusted input into a **frozen dataclass at one boundary gate**, then never validate
  again. The objection to Pydantic/ORMs is *pervasive runtime validation*, not a single gate.
  (Q14, Q17)

- **A parsed record states only what its input carried.** Where one input format carries a field and
  another does not, the field is optional on the shared record, and the check that reads it skips an
  absent value. **Never substitute a plausible default**, because the program then reports a fact
  that the file does not contain. (R9-01)

  A lockfile of `name==version` lines declares no source. Give the record `source: SourceName | None`
  and let the source check pass on `None`. Do not stamp `'pypi'` on every package: under a policy
  that allows only `internal`, an invented source turns every line of every lockfile into a finding
  that the manifest never justified.

  This bites hardest where one shared record serves two formats, which is what `architecture.md`
  asks for. The fix is the optional field, not a second record type.

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

  This creates two traps:

  - **Never splat the remainder into an output record.** `{'source': path, **entry.extra}` lets an
    untrusted log line that carries its own `source` key **forge its provenance in your report**.
    Nest it: `{'source': path, 'extra': dict(entry.extra)}`.

  - `frozen=True` plus a mapping field is **not hashable**. `set(entries)` raises `TypeError` at
    run time with no linter warning. Fine until someone dedupes.

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
  the exception, then `raise rejectLine(...) from exc`. The helper emits the same records as six
  inline log calls and costs fewer lines. (Q23, R4-02)

- **The handle site records what it meant here, but in a degrade-and-report loop it logs the
  aggregate, not the item.** This is the rule that matters. Per-item handle-site logging on a file
  of 10,000 bad lines writes a record per line and megabytes of output. Log the item at DEBUG and a
  per-file tally at WARNING: that is tens of records and kilobytes, and `--verbose` still shows
  every item. (R4-02)

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

**Write for a professional developer who has the file open.** That reader knows the language and the
vocabulary of the trade, so `API`, `idempotent` and `tuple` are the right words and a plain-English
circumlocution around them is worse. One idea per sentence. **One word for one thing, and the word
is the identifier the code uses** — a docstring that says `unassigned` where the code says
`unattributed` sends a reader to grep for something that is not there. (R9-09)

This is the one place in the file where prose quality is load-bearing, and no tool checks it.
It governs docstrings and comments, never code or identifiers.

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

**A sample goes stale and no tool catches it**, which is the cost the `__main__.py` module map
already pays under `R9-02`. Keep it small for that reason, and re-paste it when the output changes.

**Expect it to cost lines.** Measured over five modules of a working program, pasting the sample
took their docstrings from 4, 4, 5, 7 and 12 lines to 20, 8, 7, 10 and 9. Only the one carrying
paraphrase and justification got shorter. The sample buys exactness, not brevity: a reader learns
the column order, the units and the alignment from three rows of a table and cannot learn them from
a sentence that says the table has columns.

This generalises `R3a-11`, which said the same thing for file moves and path manipulation.

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

The summary line is mandatory. **A body is not, and usually does not earn its place.** Applying the
tests below to a working 14-module package cut its docstring prose by 60%, and one module lost its
body entirely. (R9-09)

**Cut a sentence when any of these is true:**

- **It is visible in the file.** `frozen=True` is on the line above. `| None` is in the signature.
  A reader who has the file open does not need either restated.
- **Its negation would be a bug, an absurdity, or an implementation nobody would ship.** Negate the
  sentence and read it back. `it never holds a value that the file did not state` negates to a bug.
  `An empty line holds nothing` negates to an absurdity. `Other files are skipped, so the quota file
  can share the directory` negates to a scanner that dies on a stray file, which nobody would ship.
  All three are free sentences and all three go. **Assume the reader expects competent code, and
  document only the departures.**
- **It explains a language feature.** `Such a field holds None` restates what optional means.
- **It goes stale and nothing checks it**, unless it is a sample you accept that cost for.

**Compress what survives:**

- **Name the property, do not explain it.** `Rows are keyed on team, total and quota, so runs are
  idempotent` replaces three sentences describing idempotence.
- **State an ordering as its sort key.** Prose about a multi-level sort cannot say whether it is one
  composite key or two separate sorts. `Teams sort by (-over, -used, team); the paths inside a team
  sort by (-size, path)` says which, and shows that the tie-break on `team` runs ascending while the
  numbers run descending. Prose cannot carry that without becoming longer than the key.
- **The summary line names what the code produces, by its real name.** `Read the quota file, and
  construct a QuotaPolicy accordingly` beats `Read the quota file, and answer what it states about a
  team and about a path`, which paraphrases a type that already has a name.
- **Stop at the fact.** `The first malformed field stops the read.` is the rule. The sentence after
  it explaining why stopping is right is not functionality. This is `R9-02` one step further in: the
  ban is not only on style-guide justification but on justifying the design at all. Where a reason
  has to survive, it is a `#` comment at the line that needs it.

**A body earns its place for these, and in practice for nothing else:**

- an **ordering or tie-break**, which is invisible without reading a sort key
- a **unit, a nullability or a provenance** that the annotation cannot carry — `Sizes are plain byte
  counts`, `host is null when the report that gave the entry named none`
- **where the leftover, default and failure cases go**. Most awkward docstrings are awkward because
  they circle an unstated default.
- a **sample** of concrete text the module reads or writes
- a **constraint from outside the program** — `the standard formatter of logging discards extra`
- a **guarantee a caller needs** — `The call writes no file, prints nothing, and records nothing`

Seven cuts with no counterweight would drive every docstring to a bare summary line. That list is
the counterweight, and it is what every surviving sentence in the measured package sits on.

- **A function gets a docstring when its contract is complex**: it takes more than three
  parameters, or it exceeds 20 lines. Below both, `#` comments carry the contract. Raising is not a
  trigger, because the style routes raise sites through a `reject*()` helper and every two-line
  guard that calls one contains a `raise`. (Q05, R2-03, R2-05, R5-05, R8-D18-resolved)

  The trigger is contract complexity rather than length alone, which is why the parameter count sits
  beside the line count. A bare line threshold would reward fragmentation: splitting a 21-line
  function into two 12-line ones deletes the obligation without simplifying either contract.

- **The docstring carries a summary and a `Raises:` section. It carries `Args:` and `Returns:` only
  where they say something the signature cannot.** `NAR004` enforces `Raises:`, because an
  exception is the one part of a contract that no annotation carries. (R8-D28-resolved)

  Write `Returns:` for an ordering, a nullability, a unit, or a count whose meaning is not obvious:
  `The number of rows this call added, which is 0 on a repeat run.` Do not write `The parsed policy`
  above `-> Policy`. Write an `Args:` entry for a parameter the body does not consume in the obvious
  way: `manifest: Where the text came from, for the rejection message.` Do not write
  `path: The file to read.`

  A section that duplicates the module docstring is worse than an absent one. A `main()` whose
  module docstring already lists the exit codes does not list them again.

- A docstring must not assert anything the code does not do, and must not state a consequence it
  already implied. (Q05)

- **A docstring says what the code does. It does not say why the code is shaped the way this style
  guide requires.** `Two audits can hold two databases at once` is behaviour and belongs.
  `so this is a class and not a module` argues with the style guide and does not. The reader wants
  the program explained, not the rulebook. (R9-02)

- **A docstring describes its own file.** Do not assert what another module does, do not claim to be
  the only place something happens, and do not count callers. `nothing outside this module imports
  sqlite3` and `this is the one place that builds it` are claims that no tool checks and that the
  next commit falsifies. Name another module only where a reader of *this* file needs the name in
  order to use this file. (R9-02)

- Where semantics vary by implementation (file moves, copies, path manipulation), **show a
  concrete before/after example**, not prose. (R3a-11) That is one case of the general rule above:
  show the thing rather than describe it.

- **Comments carry why the program behaves this way**: the tribal knowledge, the constraint from
  outside, the link to the source. Never restate the line, and never explain why the file conforms
  to a rule in this document. (R9-02)

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
  counts as reachable, because its callers sit in files that this per-file checker never sees.
  (R8-D02)

## Logging

One stable event name plus structured `extra={...}` fields, never an f-string of prose. The
message is a queryable key. (Q08)

**JSONL output is for a service, not for every script. Decide by who reads the logs.** (R5-03,
R8-D23-resolved) A collector that queries them wants JSONL; a person at a terminal does not.

Decide by the reader, not by the line count of either formatter. JSONL logging belongs in an
importable library that every program shares, and then it costs one import.

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
total=10000`, which is the tally an operator acts on and the location that finds the call site.

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

**3.10 reaches end of life in October 2026.** `asyncio.TaskGroup` also arrives at 3.11, and it is
the right tool for supervising several long-lived tasks; hand-rolling its cancellation is what
fails silently.

- `datetime.UTC`, `typing.assert_never`, `enum.StrEnum`, `asyncio.TaskGroup`, `asyncio.timeout()`,
  `typing.Self` and `tomllib` are all available. No workaround is needed for any of them.

- **`except TimeoutError` is correct** around `asyncio.wait_for`. At 3.11 `asyncio.TimeoutError`
  *is* the builtin, so the two are one class. (R3a-06)

- Not available, so out: anything added in 3.12 or later, including the `type` statement and
  PEP 695 generics.

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
absent. **Do not replace it with a loop that greps tool output for findings**: a missing binary or a
missing config then produces empty output, which reads as a pass.

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
