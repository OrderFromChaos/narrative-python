# V5 rating — held out, open, not blind

Three implementations of `TASK.md` sit in `base/`, `skill/` and `full/`.

## What this round is for

V5 is the held-out test of the round-9 docstring rules — `R9-08`, `R9-09` and `R9-10` — which were
written after reading V4's output. A rule derived from one program will fit that program. The
question is whether it fits the next one.

V5 is also a **different computation shape on purpose**. V3 and V4 both read two formats, aggregate,
and compare against a threshold. V5 is a **join with leftovers on both sides**: two of its three
finding kinds *are* the leftovers. If the rules only work on aggregate-and-threshold programs, this
is where that shows.

| arm | context given |
|---|---|
| `base` | the task, no style guidance |
| `skill` | the task, `SKILL.md`, `tooling.md`, the config — **`architecture.md` withheld** |
| `full` | the task, all of the above **plus `architecture.md`** |

## Mechanical scores

| arm | modules | lines | ruff | pylint | mypy | checks |
|---|---|---|---|---|---|---|
| `base` | 12 | 1317 | 321 | 36 | 0 | 14 |
| `skill` | 10 | 1039 | 0 | 0 | 0 | 0 |
| `full` | 12 | 968 | 0 | 0 | 0 | 0 |

All three run, all three exit 1 on their fixture, all three are idempotent on a second run. Both
guided arms pass all six gate checks.

## Did the round-9 rules transfer?

**The naming and data rules did, cleanly.**

| defect | `base` | `skill` | `full` |
|---|---|---|---|
| `<noun>In` / `<noun>Of` names (`R9-03`) | 0 | 0 | 0 |
| cross-module claims (`R9-02`) | 0 | 0 | 0 |
| style-guide justification (`R9-02`) | 0 | 0 | 0 |
| bare `path:` / `text:` parameters (`R9-04`) | **9** | **0** | **0** |
| invented parse defaults (`R9-01`) | 0 | 0 | 0 |

One grep hit on `skill` was a false positive of the pattern, not a defect:
`# The program cannot know what it was asked to reconcile, so this is an error and not a tally.` is
a `#` comment carrying a reason at the line that needs it, which is what `R9-10` prescribes.

`R9-01` transferred to a shape it was never derived on. `full` kept one `InventoryRecord` with
`monthly_cents: Cents | None` and `team: TeamName | None` and added `origin: InventoryFormat`,
reasoning that `origin` "is provenance the file actually carries, not an invented default". Nothing
in the rule mentions joins or provenance.

## The claim that did not reproduce

**Prose concision.**

| | `base` | `skill` | `full` |
|---|---|---|---|
| V4 re-run, module-docstring prose words | 594 | 395 | 345 |
| **V5, module-docstring prose words** | **483** | **536** | **518** |

On V4 the guided arms sat 35–42% below `base`. On V5 they sit **7–11% above** it. The effect
inverted.

The reason is in the code: **V5's `base` arm writes well.** With no guidance it produced this in
`rules.py` —

```
    ignored_skus    a resource with one of these skus takes part in no join
    region_aliases  a long region name mapped to its short name
    grace_cents     a billed_not_found finding at or below this cost is
                    recorded but does not set the exit code
```

— which is `R9-08`'s show-rather-than-describe rule, arrived at unprompted. Its `store.py` also
carries "A row whose `last_seen_at` is older than the latest run is a mismatch that the inputs no
longer show", which is real information neither guided arm thought to state.

The guided arms still do the right things — `full/store.py` pastes real row tuples, `full/rules.py`
pastes the JSON, `full/join.py` states the field asymmetry exactly — but **on this task the rules
bought correctness, not brevity.** Any claim that they produce shorter prose rests on V4 alone,
which is the task they were derived from. Two data points, one positive and one neutral.

## A trap that `R9-01` creates

`R9-01` says a parsed record states only what its input carried, so `team` and `monthly_cents` are
`None` on the side that does not carry them. Those records are then the dedup key for requirement 5.

**A SQLite `UNIQUE` index spanning a nullable column does not deduplicate.** Verified: three
identical `INSERT OR IGNORE` of a row whose `team` is `NULL`, under `UNIQUE(kind, rid, cents, team)`,
produce **three rows**. The same insert under `UNIQUE(kind, rid)` produces one.

All three arms avoided it, by three different routes — `base` with a `(kind, resource_id)` primary
key and `ON CONFLICT DO UPDATE`, `full` with `UNIQUE (kind, resource_id)` and `INSERT OR IGNORE`,
`skill` with a sha256 digest of every field as the key. Only `skill` named the trap, calling it "the
one non-obvious correctness trap in the task".

This is a second-order consequence of a rule, not a defect in it, and it belongs in the record
because the next program that keys a store on a record with optional fields will meet it.

## A defect in the spec, not in the arms

`base` found it: requirement 8 ties the exit code only to a `billed_not_found` finding above grace,
so **an input file that fails to parse leaves the exit code at 0 while silently manufacturing
`billed_not_found` findings.** A scan file that will not parse means every resource it would have
matched now reads as "billed but not found".

A join has this failure mode in a way V3's and V4's aggregations do not, which is a direct
consequence of choosing a different computation shape. All three arms inherit it. `base` and `skill`
both flagged it and chose differently — `base` stayed spec-literal with a stderr warning, `skill`
exits 1 on a rejected file, citing `Q24`. The spec should have said.

## Where the guided arms differ

`skill` listed **17** inter-module questions it had to answer with no rule to consult, against 18 on
V4 and 9 on V3. `architecture.md` answers most of them. Three are new and worth carrying:

1. **The module map has no defined format.** `R9-02` names "the `__main__.py` module map" and never
   says what one looks like. `skill` invented a `Modules:` block in dependency order.
2. **When a docstring may name another module.** `skill` read `R9-02` as forbidding claims *about*
   another module while permitting pointers to one, and used pointers. That reading is right and the
   rule does not say it.
3. **One sample per producing module, never re-pasted.** `skill` arrived at this to stop two copies
   of one table going stale independently. It is the answer to a collision `full` hit on V4 and had
   no rule for.

## A collision that has now recurred twice

`full` hit the same fork the V3 full arm hit: **"an application package's `__init__.py` is empty"
against the requirement that the package be importable.** Both arms resolved it the same way, with a
re-export façade and `__all__`, and both reported having to invent that.

`R8-D37` recorded this as open, noting that `R7-B05` gives no test for whether a program is an
application or a library. Two independent arms on two unrelated tasks have now paid for it. It is
ready to settle.

## Limitations

**One task, one agent per arm, no repeats.** `base` writing well on V5 and poorly on V3 is agent
variance, and it is exactly why the prose-concision result should not be read as a refutation any
more than V4's should have been read as a proof.

**Open, not blind.** The directory names identify the arms. Normalising the layout would destroy
what the round measures.

**`skill` and `full` still tie at zero.** As in V3 and V4, nothing mechanical separates them.

## What to record

| | base | skill | full |
|---|---|---|---|
| 1–5: is this how I would want it written | | | |
| lines I would change in review | | | |
| where would I look to add a fourth finding kind | | | |
| does a docstring here tell me anything I did not want | | | |
