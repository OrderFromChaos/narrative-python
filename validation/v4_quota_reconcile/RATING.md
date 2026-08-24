# V4 rating — open, not blind

Three implementations of `TASK.md` sit in `base/`, `skill/` and `full/`.

## What this round is for

V4 exists to test five rules that round 9 wrote **after reading the V3 output**. A rule written to
fix what one program did will fix that program. The only question worth asking is whether it fixes
the next one, so this task is new and no arm saw V3.

| arm | context given |
|---|---|
| `base` | the task, no style guidance |
| `skill` | the task, `SKILL.md`, `tooling.md`, the config — **`architecture.md` withheld** |
| `full` | the task, all of the above **plus `architecture.md`** |

## Why this one is not blind either

The same limitation as V3 holds and for the same reason: **the directory tree identifies the arm
before anyone reads a line.** `full/` has `vocabulary.py` and `logs.py`; `base/` does not. Normalising
the layout would destroy what the round measures. Treat the open comparison as a real limitation.

## Mechanical scores

`validation/score_arms.py validation/v4_quota_reconcile` writes `scores.json`.

| arm | modules | lines | ruff | pylint | mypy | checks |
|---|---|---|---|---|---|---|
| `base` | 13 | 1347 | 324 | 41 | 0 | 5 |
| `skill` | 11 | 1117 | 0 | 0 | 0 | 0 |
| `full` | 14 | 1112 | 0 | 0 | 0 | 0 |

V3 gave 367/33/0/3 for `base` and zeros for both guided arms. **The pattern reproduces**, including
the part that matters: `skill` and `full` tie at zero, so the mechanical half cannot separate them
here either. Every rule round 9 changed is one no tool checks.

## Did the five rules transfer?

Counted over the `full` arm of V3 against both guided arms of V4.

| defect the rule targets | V3 `full` | V4 `skill` | V4 `full` |
|---|---|---|---|
| `<noun>In` / `<noun>Of` function names (`R9-03`) | 6 | **0** | **0** |
| cross-module and only-place claims (`R9-02`) | 3 | 1 | **0** |
| style-guide justification in prose (`R9-02`) | 4 | **0** | **0** |
| bare `path:`/`text:` parameters (`R9-04`) | 7 | **0** | 1 |
| invented parse default (`R9-01`) | 1 | **0** | **0** |
| `Args:` sections | 5 | 2 | 1 |

### The clearest single result

`R9-01` says a parsed record states only what its input carried. The task gives one format that
names the owning team and one that does not, so every arm had to decide what team-less bytes belong
to. They split three ways:

- `base` invented `UNATTRIBUTED_TEAM`, gave it `default_quota`, and **reported it as a team over
  quota**. It also grew a `--unattributed-team` flag to rename the invention.
- `skill` totals them into `Reconciliation.unattributed_bytes` and prints them on their own line.
- `full` gives them their own record, `UnattributedUsage`, and prints
  `UNATTRIBUTED 2.0T in 5 entries that name no team`.

The unguided arm produced the exact failure `R9-01` was written from, independently, on a task that
shares no domain with the one that produced the rule. Both guided arms avoided it.

`skill` then generalised the rule to a case nobody wrote down. Asked what an absent `default_quota`
should do, it made the field required, and gave the reason: it "would force the gate to invent a
number the file never carried."

### The two residuals, stated plainly

**`skill/vocabulary.py:12` — "This module imports no other module of the package."** A claim about
relationships rather than behaviour. It is the mildest form: a reader checks it against the import
block three lines below. It survives because `R9-02` bans claims about *other* modules and this one
is about itself.

**`full/quotas.py:65` — `def exemptFromQuota(path: Path, policy: QuotaPolicy) -> bool`.** `R9-04`
wanted `usage_path`. Note what the same arm did seven lines away: `parseTextReport(report_text: str,
source: Path)` — it named the `str` informatively and left the `Path` beside it as `source`. `source`
is better than V3's bare `path` and it is not the name the rule asked for. **`R9-04` took fully in
`skill` and partially in `full`.**

**A gap the rule does not cover.** It governs parameter names and says nothing about dataclass
fields, so `UsageEntry.path` and `UsageReport.source` are unruled in both arms. Recorded as a
question, not patched to fit this result.

## Where the code went

| arm | modules | code | docstring | comment | blank |
|---|---|---|---|---|---|
| `base` | 13 | 900 | 198 | 0 | 249 |
| `skill` | 11 | 605 | 262 | 12 | 238 |
| `full` | 14 | 665 | 178 | 10 | 230 |

The unguided arm carries about 35% more executable code and writes fewer comments than either
guided arm. This reproduces V3, where `base` held 851 code lines against `full`'s 394 while `full`
carried *more* docstring lines. **A shorter guided arm is not a less documented one**, and the
reading that guidance buys brevity by cutting prose is wrong in both rounds.

## What the arms did differently

`full` carries three modules `skill` does not: `vocabulary.py`, `logs.py` and the `overages.py`
/ `reconcile.py` split. `skill` folded logging configuration and its `FieldFormatter` into
`__main__.py` and reported that as an invented answer.

`skill` listed **18** inter-module questions it had to answer with no rule to consult, against 9 on
V3. `architecture.md` answers 10 of the 18: where a shared type lives, import direction, the format
seam, the divider on a pure-types module, the entry-point map, where exit codes live, the degrade
boundary, who logs the tally, the `__init__.py` façade, and package-wide name collisions — that last
one only because `R9-03` now states it.

The eight it misses are worth listing, because they are the round-10 candidates:

1. Where a type **with behaviour** lives, when the glossary is types-only (`QuotaPolicy`).
2. Whether two sibling readers may share file I/O, or whether the caller reads the bytes.
3. Whether `getLogger(__name__)` or the package name, given `__main__` under `-m`.
4. Which module owns the exit codes.
5. Whether the degrade boundary nests — a bad line inside a bad file.
6. Whether the SQLite key spans runs.
7. Which quota fields are optional.
8. Whether `__init__.py` re-exports for an application package that must also be importable.

Items 1 and 3 are already `R8-D38` and an open `R8-D37`/`R8-D43` pair. Item 5 is `R8-D42`.

`full` reported six places where two rules pulled against each other and it had to choose. Two are
new and neither is recorded: the exhaustive `match` producing near-identical return lines against
`R2b-P0`, and `Q10`'s all-code-in-`main()` against the 20-line docstring trigger.

## Limitations, stated rather than footnoted

**`R9-01` is the weakest test in this round.** Its worked example in `SKILL.md` is drawn from V3's
lockfile-with-no-source case, and V4 has the same shape: two formats, one missing a field. The
guided arms got a near-verbatim hint. The result is still worth something — `base` shows the trap is
real and easy to fall into, and `skill` generalised the rule past the example to `default_quota` —
but a genuinely independent test of `R9-01` needs a task whose asymmetry is not a missing string
field.

**One task, one agent per arm, no repeats.** Nothing here separates a rule that works from an agent
that happened to write well. V3 and V4 agreeing is two points, not a trend.

**`skill` against `full` is still unseparated mechanically.** Both score zero, as predicted before
either was written, so the case for `architecture.md` rests entirely on the rating below and on the
18-questions count.

## What to record

Per arm:

| | base | skill | full |
|---|---|---|---|
| 1–5: is this how I would want it written | | | |
| lines I would change in review | | | |
| where would I look to add a third report format | | | |
| does a docstring here tell me anything I did not want | | | |

The last row is new, and it is the one that tests round 9. `R9-02` claims a docstring should carry
behaviour and nothing else. If the V4 docstrings still read like a rulebook, the rule did not work
and the count above is measuring the wrong thing.
