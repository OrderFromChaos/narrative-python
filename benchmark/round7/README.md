# Round 7 — architecture

The first five rounds measured what one file looks like. This round measures what several files look
like together.

## Why the round exists

`skill/SKILL.md` rests on 105 decisions taken before this round, and almost none of them reach above
one file. `architecture.*` held 3 of the 105. Nothing in the style says which module may import
which, when one file becomes two, what `__init__.py` holds, or where a shared type lives.

The repository shows the same hole. It contains 35 Python files, no `__init__.py`, and **no internal
import edges**. No file in this repository imports another file in this repository.

Round 3 did rank three architectures. The recorded reason for the P1 ranking — "passing state
through global variables seems weird" — argues against variant `a`, not against the layered variant
`c` that placed third. A three-way ranking let the wrong comparison decide, and no rule came out of
it. Round 7 asks the comparison round 3 missed.

## Scope

**In:** multi-file and package structure; dependency and third-party policy.

**Out:** rules that live inside one function or one file. Rounds 1 to 6 own those.

**The program kinds are a long-running service, an importable library, and a monorepo.** The
one-shot CLI is deliberately absent. It is the shape the corpus already covers, and it is the shape
that hides every question this round asks: a program that runs once and exits has no state that
outlives a request, no consumer that imports it, and no second entry point to share code with.

## The repository the questions assume

```
scanlib/       importable library: the scan wire format, its types, its errors
collector/     long-running service: polls instruments over TCP, writes readings to SQLite
drift_check/   batch program: reads the database, reports calibration drift
tools/         fixture generators
```

Three programs, one shared library, one repository.

## Protocol

**Stage 1 — `questions.md`.** Six blocks of forced choices. Answer as if you had infinite time and
effort. Every pair is behaviourally identical and one dimension varies. "Depends" is a real answer
when it comes with a condition.

Answer **block M first**. Its two questions set the exchange rate — what a reader's attention costs,
and which of two conflicting measures wins — and every later block trades in that rate.

## The measure, settled

Block M is answered. Every later block and every stage-2 change request scores against this.

**A change of a given kind lands at exactly one abstraction level, and the kind of the change names
which level.** (`R7-M01`)

Files touched is not the measure, in either direction. M01 offered both file-count metrics and both
were rejected. The design that answered it separates a general probing policy, a vendor byte format,
and one device's quirks, so that "the vendor released a new format" has exactly one destination and
the person making the change knows which one without reading the program first.

**The exchange rate** between three ways of paying for clarity (`R7-M02`), dearest first:

1. a parameter threaded through functions that do not use it — it takes reader attention and returns
   nothing
2. one more file
3. one more named type — free when the field belongs to the thing it describes

A design that spends a named type to remove a threaded parameter is therefore strictly better, and so
is one that spends a file to remove a threaded parameter. That is the architectural reading of
`NAR005`, and it reinforces `R2b-E3` from a second direction.

Three size thresholds were named in passing and recorded **weak** (`R7-M01-sizes`): several devices
may share a file when each is about 10 lines; one device earns its own file when it builds a full
parsed dataclass; past roughly 800 lines a device becomes a directory.

**Block B superseded all three.** `R7-B01-B03-criterion`: a coherent concern earns a module and line
count is not the criterion. Twenty-eight lines earned a file; three hundred and forty became six. The
numbers above describe how big a concern usually is in that domain. They are not the test.

## Block A, settled

Eight questions on which module imports which. The control passed and the block stands.

**There is no layer table and no directory rule.** `R7-A05-levels` closed this hard. `io/reader.py`
importing `io/checksum.py` is correct, because a checksum is below a reader whatever the directory
says. Directory depth is not the level, a declared layer order was offered and rejected, and no
`NAR1xx` check can enforce dependency direction. It is a review rule and it must carry the admission
that `SKILL.md:167` already uses for constant placement.

What the block did settle:

- **A type that can cross a module boundary lives in a shared module, above the modules that use
  it.** (`R7-A02`, `R7-A04-revised`) Exception types always qualify, because a handler can be
  anywhere; the module that raises does not own the type. The reason in both cases is the same, and
  it is not aesthetics — it is that the alternative pays for a circular import.
- **Two participants that must agree on a byte layout share one module, beside them.** (`R7-A05`) A
  copy on each side is the worst option, because drift between the copies is a bug no type checker
  and no linter reports.
- **Do not make a caller pass what the callee can derive from what it already has.**
  (`R7-A01-revised`) This **outranks** dependency direction: a store module importing a config module
  is accepted rather than push a lookup onto every caller. Record the ordering, because the two
  collide often.
- **A resource is opened at the scope whose lifetime it matches**, and the reader finds the open at
  the top of that scope. (`R7-A03`) Idle time is not the variable; what the handle costs on the far
  side is. A local file handle is free to hold. A network connection, a device socket or a licensed
  SDK seat is not, and an idle hold there can fail silently where the program cannot see it.
  (`R7-A03-idle`)
- **A callee that takes primitives has pushed its own destructuring decision onto every caller.**
  (`R7-A02`) That, not type loss, is why dissolving a shared type to break a cycle is the worst of
  the three fixes.
- **A registering decorator loses to an exhaustive `match`** on readability alone, independently of
  `R4-03`'s type-safety argument. (`R7-A06`)
- **`Q24` survives the move from a batch CLI to a long-running service.** (`R7-A08`) It took a
  re-ask; see the note on that record, and the instrument lesson below.

Two answers are conditional and neither should be pushed hard: the direction of a config lookup
depends on whether the callee already owns the thing (`R7-A01`), and leaf modules importing their own
constants beats threading a config object only when the constants are known at import (`R7-A07`).

**Two instrument lessons, both paid for.**

`R7-A08` was answered wrongly first time because the two options differed in behaviour while the
preamble promised they did not, so the answer came on readability. Any option that changes what the
program does must say so in the question.

`R7-A04` **reversed** on the follow-on. A question about where a type *lives* gives the wrong answer
if it does not also show the type *crossing*. Placement reads as a locality problem until you watch a
handler two modules up try to name the type, and then it is an import-cycle problem. Every remaining
placement question in this round must show the crossing.

### The rule block A was actually looking for

`R7-A05` stalled on which test decides a module's level, so `programs/level_test/` was built to
settle it — three variants, fifteen files, one behaviour, the whole toolchain clean on all of them.
The code dissolved the question instead of answering it.

**A fact lives in the module that is about the thing the fact is a property of.** (`R7-A05-property`)

A per-vendor retry cap does not belong in a generic backoff module, and the reason is not that an
arrow points the wrong way — it is that the recovery time is a property of the manufacturer's
networking stack, and the backoff module is not about the manufacturer. Four round-7 answers that
looked unrelated are the same rule: the `site_code` lookup (`R7-A01-revised`), the exception
hierarchy (`R7-A04-revised`), the log field set, and this. Both candidate level tests turn out to be
indirect ways of asking the ownership question, which is why they agree exactly when the fact is
already in the right place.

**The entry point knows which modules exist and nothing about any of them.** (`R7-A05-entry`) Two
files is the floor for adding a vendor; one is unreachable without an import-time registry, which
`R7-A06` rejected.

**Measure what an edit must know, not how many files it touches.** (`R7-A05-measure`) Two of the
three variants touch the same number of files and are not the same design: one writes the wire format
and the magic bytes into the entry point, the other writes the vendor's name twice. This is
independent code support for `R7-M01`, which rejected both file-count metrics when they were put
abstractly, and it is the scoring rule for every remaining stage-2 cluster.

Still open: a fact that is genuinely a property of two things. `R7-A05` sent a shared wire format to a
module beside both readers; whether that is a third case or the same rule with "the pair" as owner is
unsettled.

## Block B, settled

Ten questions on where the cuts go. **The control failed and the failure is real.**

`R7-B10` asked whether an internal module keeps its docstring. It was defective on the first pass —
one option carried both the module docstring and a mechanical detail, so the answer was about the
detail. Re-asked with the detail held constant, the departure was **confirmed**: no module docstring
while a module has exactly one public function, mandatory at the second. That is a **change request
against `NAR009`**, which fires on any docstring-less module today. Unlike `R7-A08`, the re-ask did
not return to the doc.

No checker change is made here. The acceptance gate requires a cost measurement first, and the
exemption's scope is unsettled — a runnable module must presumably still carry its usage example.

What the block settled:

- **A coherent concern earns a module. Line count is not the criterion.** (`R7-B01-B03-criterion`)
  Twenty-eight lines earns a file when it is one concern; three hundred and forty lines is six files
  because it is six concerns. Neither answer mentioned a number. This supersedes the size thresholds
  recorded weak in `R7-M01-sizes`.
- **The never-split provocation is refuted.** (`R7-B01`) Six modules of 40–90 lines beat one file of
  340, for "mental buckets you can slot groups of functions into". The single-file affordance the
  style is built around does not survive past one file's worth of program. The split-on-a-second-
  consumer option was named as real practice and rejected as triage rather than as the best version,
  which is the round's own framing applied unprompted.
- **There is no fixed split axis.** (`R7-B02`) Technical layer won for a program with one wire format
  and one database; subject won in `programs/level_test/owned/`, which has three vendors. The rule is
  `R7-M01` applied directly — cut on the axis the expected changes land in more cleanly.
- **Naming a concept and crossing a boundary are one test.** (`R7-B04`) A helper that leaves the
  package must be findable by a stranger, which forces it to name a concept. Carries an untested
  prediction: no case where the two tests disagree has been built.
- **A type may be centralised before it is shared; behaviour may not be generalised before it is
  needed.** (`R7-B07-preemption`) Exception types and a frame header both went central pre-emptively;
  the registering decorator was refused. The asymmetry is defensible on cost — moving a type later is
  a mechanical edit a type checker verifies, and removing a wrongly-general dispatch is not. **This
  departs from the round's grug calibration and is written as such.**
- **A leading underscore marks a module's internals; `__all__` declares a package's exports.**
  (`R7-B08`, `R7-B05`) The style had no privacy convention at all before this. The pair is lintable
  with no judgement in it: a cross-module import of an underscore-prefixed name is a mechanical
  finding.
- **`__main__.py` holds `main`**, and splits the workflow out only when it grows long. (`R7-B09`)
- **`from collector import store`, then `store.insertReading`.** (`R7-B06`) Extends `R3a-08` from
  third-party modules to first-party ones. Open: the cited precedent aliases (`numpy as np`) and the
  chosen form does not, so aliasing a first-party module is unasked.

## Block C, settled

Eight questions on the abstraction budget. **Both controls passed first time, no re-ask** — the only
block so far where they did.

- **A class is earned by values that could differ between instances.** (`R7-C01-C02-revised`) Two
  connections can coexist, so a store is a class. `FRAME_FORMAT` is the same everywhere, so
  `protocol.py` is a module. Two earlier criteria were offered and rejected: lifetime ownership as
  too narrow, shared state as too loose — *"every file would be a class under this rule"*.
- **A Protocol is earned by a second real implementation**, and a test double is not one.
  (`R7-C01`, `R2-01`, `R2-02`) These are two separate tests that look alike, which is why refusing
  the Protocol and keeping the object is not a contradiction. A single-implementer check would be the
  right rule for Protocols and the wrong one for classes.
- **A long parameter list is a missing owner, not a missing record.** (`R7-C05-resolved`) This
  rewrites `R2b-E3`. Find what owns the values; that owner is a class when the program could hold two
  of it, a module otherwise. The frozen record is the answer only when nothing has behaviour over the
  values. Guard rail from `R7-C05-naming`: if a general name for the group is hard to pick, it is not
  a real grouping.
- **The pure core is earned by the amount of decision in it.** (`R7-C06`, `R7-C07`) Four routing
  rules and three effects: extract the plan. One f-string: do not. Asked at two sizes on purpose and
  the answers split, which is a threshold rather than a flat rule. `R7-C06` also reverses round 3's
  P1 ranking, where the pure-core variant placed third for reasons that were about global state.
- **A flag stops at the level that can act on it.** (`R7-C04`) With the stated escape: a value may
  travel further when bundled into a named config.
- **Chained delegation loses to one coordinator** when the stages are arbitrary cuts. (`R7-C03`)
  Confound recorded — `verifyAndStore` and `storeAndReport` are and-names, so that option was weaker
  than its dimension.

Two rules arrived unprompted while reading the programs, neither of them architectural:

- **Only the last return names its value.** (`R7-return-naming`) `RET504` is already off (`R6-06`) so
  this is implementable, unlike `R7-indent`. Measured before recording: "always" would add a line to
  13 of 14 returns in `six_modules`, including three near-identical `outcome = …` / `return outcome`
  pairs, which manufactures the rote diffing `R2b-P0` exists to prevent. The final-return-only form
  costs none of that. The reason is orientation, not naming — at the end of a long function the name
  says what is coming out without scrolling to the signature. Open: no size threshold was set.
- **Name what a function produces, not what it takes.** (`R7-naming-result`) `cutoffFor` should be
  `deleteBefore`. New: `Q11` covers abbreviations and `Q12` covers predicates, and nothing said a
  name should describe the output.

**Instrument note.** One question was malformed and was called out as such: `R7-C05` offered two
rewrites that applied to different signatures, so they could never compete. `R7-C05` was also
rejected on its own terms first, for using an unnameable bundle — and that rejection produced
`R7-C05-naming`, which is worth more than the question would have been.

## Block D, settled

Six questions on third-party code. No controls — nothing in `SKILL.md` settles dependency policy
beyond the ORM ban, which is what made this block worth asking.

The policy is **two steps that are often mistaken for one**:

- **Take the dependency when it is simpler at the call site.** (`R7-D02`) The style is not
  stdlib-absolutist; `httpx` beat `urllib` behind a thread hop. Extends `R2-06`.
- **Then contain it.** (`R7-D03`, `R7-D01`) One module names the library; everything downstream sees
  a domain type. The provocation that the raw handle should travel freely was refuted strongly —
  `Q17`'s objection is to pervasive runtime validation, not to containment, so the two never
  conflicted.
- **The limit: handles are contained, value types are free.** (`R7-D01-D03-containment`) A
  connection, a client or a socket is wrapped. `datetime`, `Decimal`, a numpy array in a numeric
  program cross freely, because wrapping them buys nothing and costs a conversion at every boundary.
  The criterion is lifetime, not provenance — note that lifetime returns here after being rejected as
  the criterion for whether a class exists (`R7-C01-C02-revised`). Different questions; do not merge
  them later.
- **Depend rather than vendor or reimplement**, weighted by adoption. (`R7-D05`, `R7-D05-trust`)
  Downloads, age and dependents are the proxy, with the blind spot accepted: adoption cannot see a
  package that is popular and bad. Vendoring is the rare middle and needs a frozen fit.
- **A ban exception is a property of the module and is declared there** — as a bare suppression, not
  a written argument. (`R7-D04`) Conformance does not owe an explanation. This is `R7-A05-property`
  applied to configuration.
- **A pin is a property of the deployment, never of the library.** (`R7-D06`) A library states a
  floor; the repository pins the exact set in one lock file. Consistent with what this repo already
  does — `R6-04` pins the toolchain, and the toolchain is a deployment.

### The block found a defect in the skill's own output

`R7-D04-comments`. Raised unprompted: *"comments about the current context window or user discussion
should NOT go into files — the point of comments is to be valuable to future devs who don't have the
context window."*

Measured. Ten citation comments exist in Python source and they split cleanly. Five are
`skill/checks.py` and its `nar003_regimes` copies naming `NAR006`, which is that program's own
identifier and not a leak. **Five are in `validation/v1_log_triage/skill.py` — the arm generated by
the skill** — citing `Q08`, `Q22`, `Q23`, `Q18` and `R2-08` in user code.

`SKILL.md`'s python blocks contain **zero** such citations. The skill never taught this; the agent
mirrored the register of a rule document dense with citations. **Absence of instruction produced the
behaviour, so the prohibition has to be explicit.**

Scope as chosen: a citation is a working cross-reference inside the repository that owns the
benchmark, and forbidden in code written for another project — which is every project the installed
skill runs on. **Tension recorded and not resolved:** the validation arm is code the skill wrote as
if for a user and it sits inside this repository, so it is legal under the rule as stated and is the
exact leak the rule objects to. Settle that before editing `SKILL.md`.

## Block E, settled — and the round is complete

Seven questions on service, library and monorepo shape. No controls; nothing in `SKILL.md` settles
these at multi-module scale.

- **A module-level singleton is fine for anything that never needs closing.** (`R7-E01`) `LOG` is a
  global, a connection is not. That is `R7-D01-D03-handle`'s close() test applied to placement, so
  one idea now serves three rules with `R7-A03`. A module-level *literal default* for an
  operator-tunable path was rejected too — it belongs in the config file, which refines `R7-A07`.
- **One shared logger, from one logs module** (`R7-E02`) — conditional on the record still locating
  itself, which the shipped code does not do. See below.
- **One program-scoped config object reaches every module.** (`R7-E03`) Per-module slices would make
  consumers re-derive a local version, which is new surface. The config object is the one bundle that
  needs no owner with behaviour, because the program owns it.
- **The clock goes inside the parser.** (`R7-E04`) Third application of `R7-A01-revised`. The purity
  cost was put explicitly and accepted rather than waived: test through the real clock and assert on
  ordering and bounds, which is what property-based testing is for.
- **`main()`-first generalises to libraries.** (`R7-E05`) The public entry takes the position `main()`
  holds, callees follow, types last — and it does **not** replace the module docstring.
- **Shared code goes in the shared library.** (`R7-E06`) `R2b-E4` was decided inside one file, where
  collapsing costs no import edge. Across two programs it costs one and the answer is unchanged.
- **The instrument pushes; the service follows** (`R7-E07`), when the device supports it. What
  replaces the round: a **time window**, not an event count. `Q24`'s aggregate survives, defined over
  a window rather than a batch.

### Two change requests, both found by testing rather than reading

**The formatter cannot locate a record.** (`R7-E02-fields`) `SKILL.md`'s `FieldFormatter` excludes
every field a `LogRecord` carries natively, because `_STANDARD` is exactly that set — and `module`,
`filename`, `lineno`, `funcName`, `pathname` and `name` all live there. Verified by running it:
`LOG.debug('frame_parsed', extra={'device_id': 'probe-01'})` prints `DEBUG frame_parsed
device_id=probe-01` and nothing more. **Neither `R7-E02` option would have fixed it** — `getLogger(__name__)`
puts the module in `name`, and `name` is dropped too. Whitelisting `module`, `lineno` and `funcName`
costs 2 lines, 7 → 9. Note this also weakens `R5-09`'s framing: the honest comparison against the
21-line JSONL formatter is 9, not 7.

**The floor moves to 3.11.** (`R7-E07-floor`, superseding `R3a-04`) Two reasons, and the second is
the stronger one. `asyncio.TaskGroup` is 3.11+ and hand-rolling its cancellation over
`asyncio.gather` is exactly what fails silently — and **3.10 reaches end of life in October 2026**,
which is sufficient on its own.

A move to 3.13 was proposed and rejected. Free-threading and the JIT are properties of the **build**,
not of the language level: this machine runs 3.14.4 with `Py_GIL_DISABLED = False`, because the
GIL-free interpreter is a separate binary. A floor makes code legal on such a build; it does not
produce one — `R7-D06` again. Both features are also experimental at 3.13; free-threading is only
supported at 3.14. **One simplification is forgone by stopping at 3.11**, and it is the trigger to
revisit: PEP 649 makes annotations lazy by default at 3.14, so `SKILL.md:31` — *"`from __future__
import annotations`, mandatory: makes types-last legal"* — becomes false, and a line leaves every
file. Demonstrated by running a types-last module with no future import. It does not apply at 3.13. Measured blast radius — **six decisions**
(`R3a-04`, `R3a-05`, `R3a-06`, `R4-03`, `R5-01`) and **four files** (`verify.py`'s `PYTHON_FLOOR` and
vermin call, `pyproject-snippet.toml`'s `target-version`, `README.md`, `SKILL.md`'s floor section and
its exhaustive-match rule, which omits the fallback arm *because* `assert_never` is 3.11+). One whole
workaround dissolves: `verify.py` text-greps `pyproject.toml` rather than parsing it, with the
comment *"`tomllib` is 3.11+, and this style targets 3.10, so the tool that enforces the floor must
not itself break it."* Cost stated: `checks.py` advertises 3.10-or-later, and Ubuntu 22.04 ships 3.10.

**Blocks are separate sittings.** Six blocks at six different altitudes. Answer one, record it, move
on. There is no benefit to answering all of them at once and there is a cost: the later answers drift
toward consistency with the earlier ones rather than toward what is true.

**Stage 2 — `programs/`.** Real multi-module programs, built **only** for a dimension that stage 1
left open: a `depends` with no clean condition, a control that did not reproduce, or a pair of
answers that contradict each other. Round 4 established why. Prose descriptions of a gap produced no
decision. Real code produced one in a single pass every time.

Each stage-2 cluster ends with **one change request applied to every variant**, scored by files
touched and lines moved. A ranking alone produces a preference. The change request produces a rule.

## Controls

Four questions restate something `SKILL.md` already settles. They check that the multi-file format
discriminates at all.

| question | settled by | expected |
|---|---|---|
| `R7-A08` | `Q24` — degrade and report | A |
| `R7-B10` | `R5-02`, `NAR009` — every module opens with a docstring | A — **FAILED**, see block B |
| `R7-C01` | `R2-01` — `Protocol` for a seam with more than one real implementation | B |
| `R7-C08` | `R2-02` — tests use real dependencies | A |

**A control gates its own block, not the run.** Round 1 stopped everything on a control failure
because all 24 questions sat at one altitude. These six do not.

`R7-A08` is the exception worth watching. `Q24` was decided from a snippet rather than from a
program, and its meaning can genuinely change once the failure crosses a module boundary. Treat a
mismatch there as a **finding**, not as a broken instrument, and re-ask it before discarding
anything.

## Provocations

Eight of the forty-one argue a position the doc does not contemplate: `R7-A02`, `R7-A06`, `R7-B01`,
`R7-B05`, `R7-B07`, `R7-C02`, `R7-C06`, `R7-D01`. They are deliberate arguments, not neutral probes,
and they are marked in `key.md`.

The other thirty-three split 29 gaps and 4 controls.

## Recording

One line per answer in `benchmark/decisions.jsonl`, `"round": "7"` as a string. Question ids are the
decision ids: `R7-M01`, `R7-A03`, `R7-D05`.

A rule that reaches `SKILL.md` cites its id. A rule with no id and no linter behind it does not ship.
