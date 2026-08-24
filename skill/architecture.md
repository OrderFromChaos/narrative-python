# Narrative Python — architecture

`SKILL.md` governs one file. This governs several.

Read this when the program spans more than one module, or imports a third-party package. Do not read
it for a single-file program: none of it applies, and it is pure context cost.

Every rule carries the id of the decision that produced it. Those ids resolve in
`benchmark/decisions.jsonl` in the source repository, which is **not installed with the skill**, so
every rule states its own reason and the id is provenance only. Rules that no tool can check say so.

## The measure

**A change of a given kind lands at exactly one abstraction level, and the kind of the change names
which level.** (`R7-M01`)

"The vendor revised the frame format" must have one destination, and the person making the change
must know which one before reading the program.

**Measure what an edit must know, not how many files it touches.** (`R7-A05-measure`)

Two designs can touch the same number of files and not be the same design. One writes a wire format
and magic bytes into the entry point. The other writes a module name twice. A reviewer of the second
diff does not need to know what the device is.

**The exchange rate**, dearest first (`R7-M02`):

1. a parameter threaded through functions that do not use it
2. one more file
3. one more named type, which is free when the field belongs to the thing it describes

Spend a named type or a file to delete a threaded parameter. Never the reverse.

## Where a fact lives

**A fact lives in the module that is about the thing the fact is a property of.**
(`R7-A05-property`)

A per-vendor retry cap does not belong in a generic backoff module, because the recovery time is a
property of the manufacturer's networking stack. This one rule decides four questions that look
unrelated:

- **Do not make a caller pass what the callee can derive from what it already has.**
  (`R7-A01-revised`) A store module may import a config module rather than push a lookup onto every
  caller. **This outranks dependency direction.** The two rules collide often.

- **An exception type lives in the shared vocabulary, not in the module that raises it.**
  (`R7-A04-revised`) Any module may catch it, so no module owns it. The alternative pays for a
  circular import.

- **A type centralises once it appears in a signature.** (`R7-B07`, `R7-B07-bound`) A shape built and
  consumed inside one function is a step, not a type. The three values a `struct.unpack` produces
  stay unnamed.

  **This means what it says.** (`R8-D19-resolved`) A config record built in one module and read in three
  crosses, so it centralises. A round report built in one module and returned to the entry point
  crosses, so it centralises. The modules then hold functions and constants, and the glossary holds
  every type they pass between them. A module that holds only types needs **no `### vocabulary`
  divider**: the divider separates types from the code above them, and there is no code.

- **A log field set belongs to whatever emits the record**, not to the formatter. A flat shared list
  is fine while one module produces the records, and is a smell once two producers need different
  keys. (`R7-E02-fields`)

**Two participants that must agree on a byte layout share one module, beside them.** (`R7-A05`) A
copy on each side is the worst option, because drift between the copies is a bug that no type checker
and no linter reports.

## Which module imports which

**There is no layer table and no directory rule. This is review judgement, not a check.**
(`R7-A05-levels`)

`io/reader.py` importing `io/checksum.py` is correct, because a checksum is below a reader whatever
the directory says. Directory depth is not the level. A declared layer order fails for a
different reason: layers inferred from current imports make every existing edge legal by
construction.

**A cycle is a wrong cut, not an import problem.** (`R7-A02`) Break it with a shared vocabulary
module. Do not reach for `if TYPE_CHECKING`, which is cheap only because the future import is
mandatory. Do not dissolve the shared type into primitives: **a callee that takes primitives
pushes its own destructuring decision onto every caller.**

**Call a first-party module by name.** `from collector import store`, then `store.insertReading`.
(`R7-B06`) `R3a-08` governs this too: import the class, keep the verb qualified.

## Where the cuts go

**A coherent concern earns a module. Line count is not the criterion.** (`R7-B01-B03-criterion`)
Twenty-eight lines earned a file. Three hundred and forty became six. Neither answer referred to a
number.

**The test is whether you can name it without saying "and".** (`R8-D12-resolved`) `retention.py` is retention.
`store.py` is storage. A `protocol.py` that also holds `crc32Of` is "the wire format **and**
checksums", so the checksum leaves and gets its own module. This is `R7-C05-naming` one level up: a
group you cannot name is not a real grouping.

**Split.** (`R7-B01`) Six modules of 40 to 90 lines beat one file of 340, because the modules are
buckets a reader can put groups of functions into. Splitting only when a second program needs the
code is triage, not the best version.

**There is no fixed split axis.** (`R7-B02`) Cut by technical role when the program has one of
everything. Cut by subject when it has several vendors, several formats, or several sites. Apply the
measure directly: cut on the axis the expected changes land in more cleanly.

**Naming a concept and crossing a boundary are one test.** (`R7-B04`) A helper that leaves the
package must be findable by someone who did not write it, which forces it to name a concept. A
checksum earns `checksum.py`. A byte formatter and a batcher that never leave can share one module.
*No program tests the claim that the two tests never disagree.*

**Shared code inside one system starts as one `common.py`, scoped to that system's directory.**
(`R7-A05-growth`) Split it when it grows: definitions first, then implementation. This is never a
project-wide `utils.py`.

## Package surface

**A leading underscore marks any module-level name that is internal:** functions, constants,
classes, and type aliases. (`R7-B08`, `R7-B08-scope`) A module filename does not take one. The underscore
states a present fact, not a forecast: if a name ends up called in many places, it was public.
A module nothing can import has no public surface to mark, so the rule does not reach `__main__.py`.
Its names stay bare.

**`__all__` declares a package's exports.** (`R7-B05`) A library's `__init__.py` is a re-export façade
with `__all__`, holding no state and no constants. An application package's `__init__.py` is empty.

**`__main__.py` holds `main`.** (`R7-B09`) Users type `python3 -m collector` and never see the dunder.
Split the workflow out only when `main` grows long.

**The entry point knows which modules exist and nothing about any of them.** (`R7-A05-entry`) Two
files is the floor for adding a new subject: the new module, and the one line that names it.

**The reading order lives in `__main__.py`.** (`R7-B01-map`) Its docstring says what the program is
for and lists the modules in reading order. What every other module owes is `SKILL.md`'s rule, not a
second one stated here. Known cost, accepted: a reader arriving at one module from a stack trace sees
that module and no map.

**`main()`-first generalises to a library.** (`R7-E05`) The public entry takes the position `main()`
holds, callees follow in first-call order, types last under the divider. It does not replace the
module docstring.

## What earns a class, a Protocol, a bundle

**Values that could differ between instances earn a class.** (`R7-C01-C02-revised`) Two
connections can coexist, so a store is a class (`R7-C02`). A frame format is the same everywhere,
so the parser is a module. Neither lifetime ownership nor shared state is the test: shared state would make every
file a class.

`SKILL.md` already governs when a `Protocol` is earned. The two tests look alike and are not the
same: refusing the `Protocol` and keeping the object is not a contradiction.

**One coordinator, not a chain.** (`R7-C03`) Stages that nothing reuses separately do not each call
the next. One function calls them in turn and holds the intermediates.

**A pure core earns its place by the amount of decision it holds.** (`R7-C06`, `R7-C07`) Four routing rules and
three effects: compute a plan, then apply it. One f-string: build the line where you emit it.

**One module names every case of a closed set, in an exhaustive `match`.** (`R7-A06`) A decorator
that registers each handler at import inverts the import arrows and puts the dispatch table beyond
the type checker's reach. Adding a member must fail the type check, not fail at runtime.

**Centralise a type before anything shares it. Do not generalise behaviour before you need it.**
(`R7-B07-preemption`) Moving a type later is a mechanical edit that a type checker verifies.
Removing a wrongly general dispatch is not. This is a deliberate asymmetry.

## Resources, state and config

**A resource is opened at the scope whose lifetime it matches**, and the reader finds the open at the
top of that scope. (`R7-A03`)

**Idle time is not the variable. What the handle costs on the far side is.** (`R7-A03-idle`) A local
file handle is free to hold open. A network connection, a device socket or a licensed SDK seat has a
timeout, a limit or a seat count, and an idle hold can fail where the program cannot see it.

**A module-level singleton is fine for anything that never needs closing.** (`R7-E01`) A logger is a
global. A connection is not. An operator-tunable default is not either. It belongs in the config
file.

**One program-scoped config object reaches every module.** (`R7-E03`) Per-module slices make consumers
re-derive a local version, which is new surface. A config object is the one bundle that needs no
owner with behaviour, because the program owns it.

**It travels as a module-level singleton, not as a parameter.** (`R8-D09-resolved`) Parse it once at import
into a frozen record and import that name where it is needed. This needs no exception to the rule
above: a frozen config has nothing to close, so it is already the shape that rule permits. What that
rule excludes is a *hardcoded default* invented in a module, which belongs in the config file. Note
the singleton is **assigned once and never rebound** — a function that reassigns it is mutating
module state and owes a `global`, which is the shape `NAR001` exists to catch.

**Leaf modules import the constants they need**, when those constants exist at import time.
(`R7-A07`) Thread the config object instead when the program resolves it at run time. *Weak: both
forms passed.*

**A flag stops at the level that can act on it.** (`R7-C04`) It may travel further inside a named
config.

**The clock goes inside the function that needs it.** (`R7-E04`) Test through the real clock and
assert on ordering and bounds, not on an instant. Inject it only for a measured speedup on a hot
loop, and then justify it.

## Third-party code

Two steps, often mistaken for one.

**Take the dependency when it is simpler at the call site.** (`R7-D02`) **The dependency must buy
something there**: `json`, `struct`, `sqlite3`, `pathlib` and `dataclasses` already read well and
nothing replaces them. At equal ergonomics the standard library wins by costing nothing to install.
(`R7-D02-stdlib`)

**Then contain it.** (`R7-D03`, `R7-D01`) One module names the library. Everything downstream sees
a domain type.

**Contain handles, not values.** (`R7-D01-D03-containment`) **A handle is a thing that must be
closed:** a connection, a client, a socket, an open file. (`R7-D01-D03-handle`) `datetime`,
`Decimal` and an array cross freely, because wrapping them buys nothing and costs a conversion at
every boundary.

**Depend rather than vendor or reimplement**, weighted by adoption: downloads, age, dependents.
(`R7-D05`, `R7-D05-trust`) Reimplement when you must change the thing wholesale. Vendor only when one
frozen version fits and needs no changes. *Adoption cannot see a package that is popular and bad.*

**A pin is a property of the deployment, never of the library.** (`R7-D06`) A library states a floor. The
repository pins the exact set in one lock file. A library that pins exact makes its constraint
everyone's.

## Service, library, monorepo

**One shared logger from one logs module.** (`R7-E02`) A shared logger makes `record.name` constant,
so the formatter emits `module`, `lineno` and `funcName` to locate the record instead.
(`R7-E02-fields`)

**Shared code goes in the shared library**, not in whichever program needed it first. (`R7-E06`)

**The source pushes and the service follows**, when the source supports it. (`R7-E07`) A poll loop is
the fallback, not the shape. This was decided for instruments on a socket, and it reaches anything
that can notify — a queue, a filesystem watch, a webhook. It does **not** reach a source that can only
be asked, such as an HTTP endpoint you do not control; there, polling is the shape and not a defeat.

Without rounds there is no natural batch, so the reporting unit becomes a **time window**: `Q24` then
aggregates over a window rather than over a batch.

## Two `SKILL.md` rules were re-tested at module scale

Degrade-and-report (`Q24`, `R7-A08`) and real dependencies in tests (`R2-02`, `R7-C08`) both hold
unchanged across a module boundary. `SKILL.md` states them; this note only records that the move did
not alter them. In degrade-and-report the split is the obvious one: the module doing the work
collects per-item failures, the module above logs the aggregate.

## Comments

**Never write a decision citation into code you write for another project.** (`R7-D04-comments`,
`R7-D04-comments-scope`) A file the skill generates is user code wherever it sits. `(Q08)` is
unlookupable outside the benchmark, and a comment that a future reader cannot follow is negotiation
residue, not documentation. Keep the reason. The reason is the comment.

One exception, and it is narrow: a program may name a rule it **implements**. `checks.py` says
"that case is `NAR006`'s, not this one's", where `NAR006` is its own identifier rather than a
cross-reference. Naming your own code is not a citation.

## Not architecture, learned alongside

**Name what a function produces, not what it takes.** (`R7-naming-result`) `cutoffFor` should be
`deleteBefore`. Verbosity is the symptom. A name for the result is the cure.

**The last return names its value.** (`R7-return-naming`) At the end of a long function the name says
what comes out, and the reader does not scroll to the signature. Early returns and guard exits are exempt.
A name on those produces near-identical pairs and manufactures the rote diffing `R2b-P0` forbids.
`RET504` stays disabled, so this form is legal. *No size threshold exists yet.*

**Order module constants by who changes the value.** (`R7-A05-ordering`) Operator-tunable first,
developer-only bindings last. Where execution order forces a constant later in the block, it joins
the block rather than leading it. Do not contort around it (`R4-03`).

**Signature indentation is `ruff format`'s, not a preference.** (`R7-indent`, `R7-indent-resolved`) A
hanging double indent reads better and PEP 8 allows it. `ruff format` rewrites it and has no setting
for it. Accept the constraint rather than work around it.

## What no tool can check

Stated plainly, as `SKILL.md` does for constant placement.

- **Dependency direction.** No layer table, no directory rule. (`R7-A05-levels`)
- **Where a fact belongs.** Ownership is a judgement about meaning. (`R7-A05-property`)
- **The split axis, and whether a concern is coherent.** (`R7-B02`, `R7-B01-B03-criterion`)
- **Whether a bundle names a real thing.** (`R7-C05-naming`)

What a tool *can* check, once built: import cycles, a cross-module import of an underscore-prefixed
name, an `__all__` naming an undefined name, and a handle type in a signature outside its owning
module.

## Pending, and not yet in force

Recorded, measured where possible, **not shipped**. Do not follow these yet.

- `NAR009` exempting a module with exactly one def (`R7-B10`, `R7-B10-scope`) and exempting an empty
  `__init__.py` (`R7-B01-init`).

- `per-file-ignores` emptying, with every lint exception declared in its own file.
  (`R7-D04-generalised`)

- The field formatter emitting `module`, `lineno` and `funcName`, at 9 lines against 7.
  (`R7-E02-fields`)

- The Python floor moving to 3.11. (`R7-E07-floor`) `SKILL.md` still documents 3.10 and its
  workarounds, and that is still what the toolchain enforces.
