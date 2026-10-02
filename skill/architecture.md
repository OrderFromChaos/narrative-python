# Narrative Python — architecture

`SKILL.md` governs one file. This governs several.

Read this when the program spans more than one module, or imports a third-party package. Do not read
it for a single-file program: none of it applies, and it is pure context cost.

Every rule states its own reason. The ids are provenance and resolve in
`benchmark/decisions.jsonl` in the source repository, which does not ship with the skill. Rules that
no tool can check say so.

## The measure

**Name the change before you make it, and the name must give you one file to open.** (`R7-M01`)

Say what the change is in the words a colleague would use: "the vendor revised the frame format",
"the retention window moved to 90 days", "we added a third lockfile format". A design passes when
each of those sentences has exactly one destination, and when the person making the change knows
which destination before they read the program. It fails when the answer is "it depends" or "three
places".

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

**Ask whose property the fact is, and put it in that thing's module.** (`R7-A05-property`)

A per-vendor retry cap is a property of the manufacturer's networking stack, so it lives with the
vendor and not in a generic backoff module. A retention window is a property of the data, not of
the scheduler that applies it. This one rule decides four questions that look unrelated:

- **Do not make a caller pass what the callee can derive from what it already has.**
  (`R7-A01-revised`) A store module may import a config module rather than push a lookup onto every
  caller. **This outranks dependency direction.** The two rules collide often.

- **An exception type lives in the shared vocabulary, not in the module that raises it.**
  (`R7-A04-revised`) Any module may catch it, so no module owns it. The alternative pays for a
  circular import.

- **A type centralises once it appears in a signature.** (`R7-B07`, `R7-B07-bound`) A shape built and
  consumed inside one function is a step, not a type. The three values a `struct.unpack` produces
  stay unnamed.

  **Every type in a signature that leaves the module centralises**, with no exception for a type
  that only one other module reads. (`R8-D19-resolved`) A config record built in one module and read
  in three crosses. A round report built in one module and returned to the entry point crosses. The
  modules then hold functions and constants, and the glossary holds every type they pass between
  them. A module that holds only types needs **no `### vocabulary` divider**, because the divider
  separates types from the code above them and there is no code.

- **A log field set belongs to whatever emits the record**, not to the formatter. A flat shared list
  is fine while one module produces the records, and is a smell once two producers need different
  keys. (`R7-E02-fields`)

- **A one-line body earns its name when the expression encodes a domain decision.** It does not when
  the expression is a plain language or stdlib operation. (`R9-12`)

  ```python
  # No. A dict lookup with a default is not a concept.
  def canonicaliseRegion(region: RegionName, reconcile_rules: ReconcileRules) -> RegionName:
      return reconcile_rules.region_aliases.get(region, region)

  # Yes. The pattern and the fold are the PEP 503 rule, and the name is what states it.
  def normalizeName(name: PackageName) -> PackageName:
      return _NAME_SEPARATORS.sub('-', name.strip().lower())
  ```

  These two settle the boundary, because only one token separates them:

  ```python
  sorted(path for path in directory.iterdir() if path.is_file())                    # inline it
  sorted(path for path in directory.iterdir() if path.is_file() and isReport(path))  # name it
  ```

  The first is three `Path` calls. The second composes `isReport`, which is a concept from the
  problem, and the name of the whole is what tells a reader the two conditions belong together.

  This is judgement and no tool checks it. Measured over eight packages, seven functions forwarded to
  a single expression and only one was the defect, so a mechanical threshold would be six false
  positives in seven.

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

**The qualifier is not part of the function name.** `store.insertReading` reads well because
`insertReading` reads well on its own. A module-qualified call invites a shorter and vaguer
function name, and `SKILL.md`'s naming rules refuse it: the name must carry its meaning to a reader
who has never opened the module. Note also that the import burns the identifier `store` at module
scope, so a local of that type becomes `results_store: Store`. (`R9-03`, `R8-B06-Q11`)

## Where the cuts go

**A coherent concern earns a module. Line count is not the criterion**, in either direction: a
28-line concern earns its own file, and a 340-line file with six concerns in it becomes six.
(`R7-B01-B03-criterion`)

**The test is whether you can name it without saying "and".** (`R8-D12-resolved`) `retention.py` is
retention. `store.py` is storage. A `protocol.py` that also holds `crc32Of` is "the wire format
**and** checksums", so the checksum leaves and gets its own module. This is `R7-C05-naming` one
level up: a group that needs "and" to describe it is two groups.

**Split.** (`R7-B01`) Six modules of 40 to 90 lines beat one file of 340, because each module is a
bucket a reader can put a group of functions into. Do not wait until a second program needs the
code.

**There is no fixed split axis.** (`R7-B02`) Cut by technical role when the program has one of
everything. Cut by subject when it has several vendors, several formats, or several sites. Apply the
measure directly: cut on the axis the expected changes land in more cleanly.

**Naming a concept and crossing a boundary are two tests, and they can disagree.** (`R7-B04`,
`R8-D39`) A helper that leaves the package must be findable by someone who did not write it, which
forces it to name a concept: a checksum earns `checksum.py`. A byte formatter and a batcher that
never leave can share one module. But a version comparator can name a concept cleanly and still be
imported by one module and cross nothing. Where the two tests disagree, no order between them is
settled — treat it as a question for review, not a rule.

**Shared code inside one system starts as one `common.py`, scoped to that system's directory.**
(`R7-A05-growth`) Split it when it grows: definitions first, then implementation. This is never a
project-wide `utils.py`.

## Package surface

**A leading underscore marks any module-level name that is internal:** functions, constants,
classes, and type aliases. (`R7-B08`, `R7-B08-scope`) A module filename does not take one.

Decide by the callers the name has now, not by the callers you expect: **a name that nothing outside
this module calls today takes the underscore.** When a later change needs it elsewhere, drop the
underscore in that change. A module nothing can import has no public surface to mark, so the rule
does not reach `__main__.py`, whose names stay bare.

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

**This is the one docstring that names other modules, and it is the only exception to the rule that
a docstring describes its own file.** The entry point is the file whose subject *is* the module
list. Every other module docstring says what that module does and stops there. (`R9-02`)

**`main()`-first generalises to a library.** (`R7-E05`) The public entry takes the position `main()`
holds, callees follow in first-call order, types last under the divider. It does not replace the
module docstring.

## What earns a class, a Protocol, a bundle

**Values that could differ between instances earn a class.** (`R7-C01-C02-revised`) Two
connections can coexist, so a store is a class (`R7-C02`). A frame format is the same everywhere, so
the parser is a module. The test is neither lifetime ownership nor shared state, because shared
state would make every file a class.

`SKILL.md` governs when a `Protocol` is earned, and that is a different question from this one. A
seam needs a `Protocol` once it has more than one real implementation; a thing needs a class once
the program could hold two of it. One object, one implementation, and a class is the right answer.

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

**One program-scoped config object reaches every module.** (`R7-E03`) Per-module slices make
consumers re-derive a local version, which is new surface. The program owns the config, so unlike
every other bundle it needs no class with behaviour to hold it.

**It travels as a module-level singleton, not as a parameter.** (`R8-D09-resolved`) Parse it once at
import into a frozen record and import that name where it is needed. A frozen config has nothing to
close, so the singleton rule above already permits it. That rule excludes a *hardcoded default*
invented in a module, which belongs in the config file instead. The singleton is **assigned once and
never rebound**: a function that reassigns it mutates module state and owes a `global`, which is
what `NAR001` catches.

**Leaf modules import the constants they need**, when those constants exist at import time.
(`R7-A07`) Thread the config object instead when the program resolves it at run time. *No tool
checks this, and both forms work.*

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

## Where degrade-and-report splits

**The module doing the work collects per-item failures, and the module above logs the aggregate.**
(`Q24`, `R7-A08`) `SKILL.md` states the rule; this is the only thing a module boundary adds to it.
Real dependencies in tests (`R2-02`, `R7-C08`) need no adjustment at module scale at all.

## Comments

The comment rules are in `SKILL.md`, **Comments**, including the ban on decision citations
(`NAR012`).

Exception: a program may name a rule it **implements**. `checks.py` has the comment
`names bound in the function are locals, covered by NAR006`, where `NAR006` is its own identifier.
Naming your own code is not a citation.

## Not architecture, learned alongside

**The last return names its value.** (`R7-return-naming`) At the end of a long function the name says
what comes out, and the reader does not scroll to the signature. Early returns and guard exits are
exempt, because a name on those produces near-identical pairs and manufactures the rote diffing
`R2b-P0` forbids. `RET504` stays disabled, so this form is legal. *No size threshold is set: apply
it where the signature is off the screen.*

**Order module constants by who changes the value.** (`R7-A05-ordering`) Operator-tunable first,
developer-only bindings last. Where execution order forces a constant later in the block, it joins
the block rather than leading it. Do not contort around it (`R4-03`).

**Take `ruff format`'s signature indentation.** (`R7-indent`, `R7-indent-resolved`) A hanging double
indent reads better and PEP 8 allows it, but the formatter rewrites it and has no setting for it.
Accept the constraint rather than work around it.

## What no tool can check

Stated plainly, as `SKILL.md` does for constant placement.

- **Dependency direction.** No layer table, no directory rule. (`R7-A05-levels`)
- **Where a fact belongs.** Ownership is a judgement about meaning. (`R7-A05-property`)
- **The split axis, and whether a concern is coherent.** (`R7-B02`, `R7-B01-B03-criterion`)
- **Whether a bundle names a real thing.** (`R7-C05-naming`)

Four more are checkable in principle and **no checker for them exists**, so they are review
judgement too: import cycles, a cross-module import of an underscore-prefixed name, an `__all__`
that names something undefined, and a handle type in a signature outside its owning module.
