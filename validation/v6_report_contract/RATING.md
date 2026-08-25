# V6 — the outputs pinned, and the two report modules finally comparable

V5 asked "write a JSON report" and fixed nothing about it. `base` emitted eight top-level keys and
`full` emitted three, so `full`'s `report.py` came in 53 lines shorter while doing materially less
work. **The two modules could not be compared, because they were not doing the same job.**

V6 pins the outputs and re-runs the round. Both arms were written fresh against
[`TASK.md`](TASK.md); neither is V5 code.

**V5 is untouched.** Every number in `v5_billing_reconcile/RATING.md` stands.

## Method

| | |
|---|---|
| task | [`TASK.md`](TASK.md) — V5's task with the outputs specified |
| fixture | `fixture/`, shipped **with** the task, not written by the arms |
| `base` | TASK.md + fixture. No style guidance |
| `full` | TASK.md + fixture + `SKILL.md`, `architecture.md`, `tooling.md`, `pyproject-snippet.toml` |
| `skill` | excluded — an older configuration that does not reflect a real install |
| oracle | `EXPECTED.md`, derived from `TASK.md` alone by an agent that never saw an implementation |

Each arm was blind to the other, to `EXPECTED.md`, to every V5 arm, and — for `base` — to `skill/`.

## The acceptance test

`TASK.md` states its own: *two correct implementations must produce byte-identical report JSON for
the same input*, excepting `generated_at`, `input_dir`, and the prose inside `problems`.

| comparison | result |
|---|---|
| `base` against the oracle | identical |
| `full` against the oracle | identical |
| `base` against `full` | **byte-identical, 5569 bytes each** |

All 13 findings, all 4 file outcomes, all 8 totals, key order at every level, the value sorts, the
indentation, the empty-array rendering and the trailing newline. Both exit 1. Both hold 13 SQLite
rows after a second run.

Three parties derived the same document independently — the oracle from the spec, and two
implementations from the spec — which is the strongest evidence available here that the contract
says what it means to say.

## What the contract cost to write

Five adversarial passes, each one re-deriving the oracle and hunting for ambiguity.

| pass | found |
|---|---|
| 1 | 7 gaps, two of them contradictions in the first draft |
| 2 | 4 blockers, including `accepted`/`rejected` defined as "parsed" — which no rejection in the fixture actually is |
| 3 | 3, including a hole in the list that declared itself closed |
| 4 | 3, including a blank trailing CSV line and output files landing inside the input directory |
| 5 | ship it |

**Two of those were introduced while closing the previous pass's finding.** The pattern is the
result: an output contract does not survive first drafting, and nothing in the V1–V5 protocol ever
forced one to be read adversarially.

Pass 5 caught the sharpest one. The header row `resource_id,sku,monthly_cents,region` holds four
non-empty fields, so it fails no clause of the closed rejection list *except* the digits rule — its
third field is the literal string `monthly_cents`. Without "the header is not a record", a
conforming implementation rejects it and reports `core.billing.csv` as `partial`.

## The result V6 exists to produce

| | V5 | V6 |
|---|---|---|
| `base` report module | 170 lines | 99 |
| `full` report module | 117 lines | 115 |
| `full` shorter by | 31% | **it is now longer** |

V5's headline was that `full` wrote a much shorter report module. **That gap was scope, not style.**
At equal scope the two land within 16 lines, and the sign flips.

Both arms also split the JSON report from the terminal table — `report.py` + `summary.py` in `base`,
`report.py` + `table.py` in `full`. **Neither V5 arm did this.** Two independent agents reaching the
same split, when V5's two both fused the concerns differently, is the strongest architectural signal
in the round, and no rule in `SKILL.md` prescribes it. Pinning the JSON as a contract appears to
have made it legible as a separate concern.

## What actually differs, now that scope does not

Both modules build the same seven-key document and pin the same serialisation. What is left is
style, which is what the round set out to isolate.

- **Decomposition.** `base` extracts `_rules_block` and `_totals_block`, so `build_report` is 10
  lines. `full` inlines both, so `buildReport` is 36. `full`'s choice is consistent with `R2b-E2`
  and `R9-12`, which resist helpers called once.
- **Signature.** `base` takes one `ReconcileResult`. `full` takes four parameters, because its
  `Reconciliation` does not carry `generated_at` or `exit_code` and they must be threaded in.
- **Docstring.** `full` pastes real rendered output — `R9-08`, show rather than describe. `base`
  writes prose, but the prose says *why*: the contract, no `sort_keys`, the pinned serialisation.
  On this module `base`'s content is the more useful of the two, and `full`'s form is the better.
- **Robustness.** `full`'s `writeReport` calls `mkdir(parents=True, exist_ok=True)`; `base`'s does
  not, and fails on a missing parent directory.
- **Naming.** snake_case against mixedCase, per the style. Not a maintainability property.
- `full`'s lines 67 and 115 run past 110 characters; `base` wraps.

One suspected defect did not survive checking. `base` renders `by_kind` from `totals.by_kind.items()`
while `full` re-iterates `FindingKind`, which looked as though a zero-count kind could vanish from
`base`'s report. Both build the mapping with `for kind in FindingKind`, so both always carry three
keys.

## Where the spec is still open

Both arms reported the same live hazard, and it is the one to fix next.

**`sources` on a finding whose other side was ignored.** `min-chert-8830` has an accepted-then-
ignored billing record and a surviving scanned record. The spec excludes only *rejected* records
from `sources` by name, so "accepted" read literally lists both files. Both arms, and the oracle,
independently listed only `estate.scan.json` — reasoning that a record dropped before the join
supplied nothing *to the finding*. Three parties agreeing does not mean the text compelled it. **One
sentence closes it.**

Five passes missed this because each asked whether the *fixture* could distinguish two readings.
None noticed that `sources` turns on an ignore-versus-reject distinction the closed list never
draws.

Also reported, none of which fires on this fixture: which `reconcile.json` is "the rules file" when
`--rules` points elsewhere; a directory entry named `*.scan.json`; permission errors and invalid
UTF-8, absent from the closed failure list; a whitespace-only CSV row; `grace_cents: true`, since
`bool` subclasses `int`; and a first CSV row that is neither the exact header nor absent.

## Where the style and the spec pulled against each other

`full` reported one. `architecture.md` (`R7-A06`) wants a closed set dispatched in an exhaustive
`match`, but the natural shape for `InventoryFormat` is a side-effecting loop body, and `SKILL.md`
says a `-> None` dispatch gets no protection and must be restructured to return. It split out
`_readInventoryFile(...) -> FileOutcome`, at the cost of a four-parameter signature carrying two
accumulators mutated in place. That is the one place a reviewer may prefer a plain `if/elif/else`.

## Toolchain

`full` passes all six gate checks — `ruff check`, `ruff format`, `pylint`, `mypy --strict`,
`checks.py`, `vermin` at 3.11 — using the repository's `.lintenv`. `checks.py` initially reported one
`NAR004` finding, a four-parameter function with no docstring, which was fixed. `base` was not
linted; it is the control.

## Limitations

**One run per arm, no repeats.** Read a large difference, ignore a small one. The 99-against-115
line counts are a small difference.

**The contract is tilted toward completeness.** V5's `base` already emitted a near-complete report,
so a contract demanding completeness resembles it. That mattered when the plan was to retrofit V5's
arms; it does not matter here, because both V6 arms were written from scratch and neither had a
head start.

**Readability still has no instrument.** Goal 2 is human-only, as in every round.

**The fixture is blind to the arms but not to the spec.** It was extended, twice, specifically to
exercise clauses the spec had just gained.

## What to record

| | base | full |
|---|---|---|
| 1–5: is this how I would want it written | | |
| which `report.py` would you rather maintain | | |
| was splitting the table out the right call | | |
| does `full`'s pasted sample earn its 26 lines | | |
| lines you would change in review | | |
