# V3 rating — open, not blind

Three implementations of `TASK.md` sit in `base/`, `skill/` and `full/`.

## Why this one is not blind

A script shuffled and redacted `v1` and `v2`. That cannot work here, and pretending otherwise is
worse than admitting it: **the directory tree identifies the arm before anyone reads a line.** An
unguided program is a flat handful of files. A styled one is a package with `__main__.py`, a
`vocabulary` module and a `### vocabulary` divider. Normalising the layout would destroy what this
measures, because layout is exactly what `architecture.md` governs.

So this is an open comparison. Treat that as a real limitation, not a footnote. If you know which
arm you read, that knowledge can move your judgement, and nothing here prevents it.

## What the arms are, and why they differ from v1

| arm | context given |
|---|---|
| `base` | the task, no style guidance |
| `skill` | the task, `SKILL.md`, `tooling.md`, the config — **`architecture.md` withheld** |
| `full` | the task, all of the above **plus `architecture.md`** |

`v1` and `v2` compared no guidance against the prior style doc against the skill. That prior doc is
not in this repository, and the question it answered is stale. The open question now is whether
**`architecture.md` earns its context budget** on a program that spans several modules. It holds 70
rules that no held-out task has exercised.

`skill` against `full` is the comparison that matters. `base` is the floor.

## What to record

Per arm:

| | base | skill | full |
|---|---|---|---|
| 1–5: is this how I would want it written | | | |
| lines I would change in review | | | |
| where would I look to add a third manifest format | | | |

The third row is the point. `R7-M01` says a change of a given kind lands at exactly one
abstraction level, and the kind names the level. A new lockfile format is that change. If `full`
does not make that easier to answer than `skill`, `architecture.md` did not pay for itself.

**The marked lines matter more than the number.** A rating says which arm won. The marks say which
rule did the work.

## Mechanical scores

`SCORES.json` in the parent directory covers `v1` and `v2` only. Run `validation/score_v3.py` for
these three, which walks a directory where `prepare_blind.py` copies one file.

| arm | modules | lines | ruff | pylint | mypy | checks |
|---|---|---|---|---|---|---|
| `base` | 12 | 1433 | 367 | 33 | 0 | 3 |
| `skill` | 9 | 811 | 0 | 0 | 0 | 0 |
| `full` | 13 | 1012 | 0 | 0 | 0 | 0 |

**The tie was predicted before the numbers existed, and it held.** `skill` and `full` score zero on
every tool. Every rule `architecture.md` adds is one no tool checks, so the mechanical half cannot
separate them and the whole case rests on the rating below.

What the numbers do settle is the floor: unguided work is 367 `ruff` findings and 33 `pylint`, and
both guided arms are clean.

## What the arms did differently

`base` split into 12 modules with no prompting, so **the guidance is not what produces a split**. The
question is whether the split is better.

`full` carries three modules `skill` does not: `vocabulary.py` for types that cross (`R7-B07`),
`errors.py` for the exception hierarchy (`R7-A04-revised`), and `logs.py` with one shared
`getLogger('manifest_audit')` (`R7-E02`). The `skill` arm mixed `getLogger(__name__)` with a literal
and reported that as a guess.

`full` deviated once: `architecture.md` says an application package's `__init__.py` is empty, and
`full` wrote a re-export façade. The task required the tool to be importable, which makes it a
library, so the **application-versus-library split in `R7-B05` is what is under-specified**.

The `skill` arm listed nine inter-module questions it had to invent answers to. `architecture.md`
answers five. The four it misses are new: which module configures logging and how far `global`
reaches, `Q11` against builtin shadowing, where a string becomes an `Enum`, and what happens when a
task spec and `Q24` disagree about an exit code.
