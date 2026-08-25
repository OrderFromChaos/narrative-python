# The measurement harness

Three of the four goals for this style can be measured without a human. This directory holds the
instruments.

| goal | instrument | metric |
|---|---|---|
| 1. shorter than unguided | `score_arms.py` | code lines, split from docstring and comment |
| 2. more readable than unguided | **none — human only** | the `RATING.md` forms |
| 3. a future change touches few files and few lines | `changes/` | files touched, lines changed, per change |
| 4. no worse against the spec | `conformance/` | tests passed, of a suite written from the spec alone |

## Goal 4: the conformance suite

The suite is written by an agent that reads **`TASK.md` and nothing else.** It never sees any
implementation. This is the control that makes the number mean anything: a suite written after
reading one arm tests that arm's decisions, and every disagreement then scores as the other arm's
bug.

The suite drives each package as a subprocess through its documented entry point, so it makes no
assumption about module names, function names or internal structure. An arm that reorganises
entirely still passes.

Where `TASK.md` is silent the suite must not assert. Those cases are recorded in
`conformance/UNDERSPECIFIED.md` instead, because a disagreement there is a defect in the spec.

## Goal 3: the change requests

Each file in `changes/` states one change a maintainer might ask for next. They are written from
`TASK.md`'s own vocabulary, and each one names a different seam:

| change | seam it probes |
|---|---|
| `C1_third_format` | format detection and reader dispatch |
| `C2_fourth_finding` | the finding pipeline: enum, join, table, JSON, SQLite |
| `C3_rules_field` | the config boundary |
| `C4_thread_field` | a new field from one reader, through the join, to three outputs |
| `C5_fourth_format` | a **second** format addition, run on top of C1's output |

`C2` and `C4` are the ones that matter most among the first four, because they are the changes that
cross every layer. A design that localises them is the design the style claims to produce.

`C5` is different in kind. It starts from each arm's **own C1 output** rather than from the pristine
arm, so it measures the *second* change in a sequence — whether a design that paid to generalise at
C1 is cheaper at C5 than one that duplicated. It exists because C1 showed the style paying a cost
whose benefit this harness could not otherwise see.

**`C5` was written after `C1` was measured**, by someone who knew which arm the extraction favours.
The first four requests were written before any of them ran. That difference is stated wherever the
C5 numbers appear.

Each arm receives each change **applied to its own codebase**, in an isolated copy, by an agent that
sees only that arm and the change request. The agent does not know another arm exists.

After each change the conformance suite runs again. **A small diff that breaks the suite is not a
good result**, so files-touched is reported beside conformance-after.

## A known gap in the conformance suite

**The suite builds every malformed fixture as valid UTF-8**, so it never exercises a file that is
not decodable text. That misses a real violation of requirement 7: `base` reads with
`encoding='utf-8'` and catches only `OSError`, and `UnicodeDecodeError` is a `ValueError`, so a
non-UTF-8 input file aborts the whole run instead of failing that one file. `full` catches it and
carries on.

It was found by a maintenance agent working on `C1`, in passing, not by the twenty tests.

**The gap is recorded rather than closed.** Adding the test now, knowing which arm fails it, would
make the suite no longer blind and would make its score unusable as evidence. Closing it properly
means a fresh agent extending the suite from `TASK.md` alone, and until that happens the 20-of-20
result should be read as *"no difference on twenty spec-derived tests"* rather than as
*"no difference."*

## What this cannot measure

**Readability.** Goal 2 has no instrument here and is not inferred from the other three.

**Whether the change requests are fair.** They were written by someone who has read both
implementations. They are derived from `TASK.md` rather than from either codebase, and none of them
names a module, a function or a data structure — but the risk of unconscious tilt is real and is not
controlled for.

**One run per cell.** No repeats, no variance. Read a large difference; ignore a small one.
