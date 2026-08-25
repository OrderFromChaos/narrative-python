# Narrative Python

A Python house style, and a Claude Code skill that writes and reviews against it.

A module reads as a document: `main()` is the thesis, the workflow functions are the argument in
call order, and the types are a glossary at the back under a `### vocabulary` divider.

The module leaves nothing for the reader to infer. Side effects carry a `global` marker, dispatch
over a closed set is exhaustive, `__init__` declares every attribute, and one boundary gate parses
untrusted input into a frozen dataclass.

Every rule cites the decision that produced it. The decisions came from 276 forced choices between
real working programs, not from preference stated in the abstract.

## Install

The skill is seven files in one directory. Clone the repository first, and run every command below
from its root.

```bash
git clone git@github.com:OrderFromChaos/narrative-python.git
cd narrative-python

mkdir -p ~/.claude/skills/narrative
cp skill/SKILL.md skill/architecture.md skill/tooling.md \
   skill/checks.py skill/verify.py \
   skill/requirements-lock.txt \
   skill/pyproject-snippet.toml \
   ~/.claude/skills/narrative/
```

Invoke it as `/narrative`, or let Claude load it when a task involves Python in this style.

**To update, run the same `cp` again.** Nothing detects a stale install, and a skill installed at an
earlier version keeps its old rules with no warning. `git pull && cp ...` is the whole procedure.

## Dependencies

### The custom checker needs nothing

`checks.py` imports only `argparse`, `ast`, `dataclasses`, `pathlib`, `re` and `sys`. Run it with any
`python3` at 3.11 or later. No virtual environment, no install.

```bash
python3 ~/.claude/skills/narrative/checks.py src/
python3 ~/.claude/skills/narrative/checks.py src/ --select NAR001 --select NAR009
```

### The external toolchain needs `uv`

Four tools do the work `checks.py` does not, plus one library they need. Install them into a
project-local environment:

```bash
uv venv .lintenv --python 3.11
uv pip install --python .lintenv/bin/python -r ~/.claude/skills/narrative/requirements-lock.txt
echo '.lintenv/' >> .gitignore
```

**Pin the interpreter.** Without `--python`, `uv` picks whatever it finds, and `mypy` then types
your code against a different standard library than the floor this style targets.

| tool | pinned version | what it owns |
|---|---|---|
| `ruff` | 0.16.3 | formatting, imports, annotations, bugbear, quotes, banned APIs |
| `pylint` | 4.0.7 | `mixedCase` function names — **no other linter can require this** |
| `mypy` | 2.3.1 | type correctness under `--strict` |
| `vermin` | 1.8.0 | the Python 3.11 floor |
| `hypothesis` | 6.165.10 | not a linter. The style mandates property tests, and `mypy --strict` needs its stubs |

The versions are pinned in `requirements-lock.txt`. An unpinned install can change what the config
means, because ruff moved `[tool.ruff.lint]` in 0.2.

**Merge** `pyproject-snippet.toml` into your project's `pyproject.toml`. If the project has none,
copy the file and rename it:

```bash
cp ~/.claude/skills/narrative/pyproject-snippet.toml pyproject.toml   # new project
```

The settings are not defaults and several are load-bearing. `tooling.md` records why each one is
there and what breaks without it.

### Docstring prose

Docstrings are written for a professional developer who has the file open, so trade vocabulary is
correct and a plain-English circumlocution around it is not. `SKILL.md` carries the rules: what a
docstring body may say, what it may not, and the tests that cut a sentence.

**No tool checks prose, and none is coming.** Docstring quality is review judgement; `verify.py`
reads Python files only. `NAR011` catches the one mechanical trap — a docstring body indented past
its own column, which `ruff format` flattens and which silently destroys a pasted sample. (`R9-09`)

### Python version

Write for **3.11**. `ruff` targets `py311` and `vermin` checks it. The floor moved from 3.10 because
`asyncio.TaskGroup` is the right tool for supervising several long-lived tasks, and because 3.10
reaches end of life in October 2026. `datetime.UTC`, `typing.assert_never`, `enum.StrEnum`,
`asyncio.TaskGroup`, `asyncio.timeout()`, `typing.Self` and `tomllib` are all available. (`R7-E07-floor`)

## Verify

Run `verify.py`. Do not call the tools by hand.

```bash
cd your-project                                          # both defaults are relative
python3 ~/.claude/skills/narrative/verify.py .           # rewrites files: runs --fix and format
python3 ~/.claude/skills/narrative/verify.py . --no-fix  # reports only, changes nothing
```

One command covers the project. Give it any path and it finds every Python file below it, so
nothing has to choose a workflow.

**Run it from your project root.** `--venv .lintenv` and `--config pyproject.toml` are relative to
the working directory, not to the script. Invoking it by absolute path from elsewhere exits 2.

**The plain form rewrites your files.** It runs `ruff check --fix` and `ruff format` before
reporting, which is what makes the run converge. Use `--no-fix` when you want a report only.

When a tool fails, `verify.py` prints that tool's own output, so you never need to re-run it by
hand.

It resolves every tool to an absolute path, and exits 2 if a tool is missing or if
`pyproject.toml` is absent. Both of those states otherwise produce empty tool output, which a
hand-rolled loop reads as a pass. That mistake happened twice while building this.

It runs the tools in the order that converges: `ruff check --fix`, `ruff format`, `pylint`,
`mypy --strict`, `checks.py`, `vermin`.

| exit | meaning |
|---|---|
| 0 | every tool passed |
| 1 | at least one tool reported a finding |
| 2 | the toolchain or the config is missing, so nothing was checked |

The `vermin` call uses `-t=3.11-` with a trailing hyphen. Without it `vermin` asserts an exact
match and fails any file that uses no 3.11-only feature.

## The ten custom rules

`checks.py` implements what no off-the-shelf tool does.

| rule | catches |
|---|---|
| `NAR001` | module state mutated with no `global` — **ruff and pylint report nothing on this at any setting** |
| `NAR002` | `hasattr(self, ...)`, meaning an attribute is conditionally defined |
| `NAR003` | more than three *positional* arguments on one `def` line |
| `NAR004` | no docstring where the contract is complex: >3 parameters or long; and a missing `Raises:` on one that raises |
| `NAR005` | an annotation naming more than four things below the outermost: a callable needs a `Protocol`, anything else a dataclass |
| `NAR006` | an assignment that shadows a module name, so the module value silently never changes |
| `NAR007` | `and` inside `or` without parentheses |
| `NAR009` | a missing module docstring, or a runnable module with no usage example. An empty `__init__.py` and a single-def module are exempt |
| `NAR010` | a `FIXME` in code that runs, which is a merge blocker rather than a danger sign |
| `NAR011` | a docstring body indented past the docstring's own column, which `ruff format` flattens, destroying a pasted sample |

`NAR000` is not a style rule. It reports a file that could not be read or parsed.

**Blank lines inside a function are review judgement, and no check enforces them.** `NAR008` is
withdrawn and its code stays in a `RETIRED` registry, so a document naming it still resolves while
`--select` never offers it. (`R8-NAR008`)

## What is in this repository

| path | contents |
|---|---|
| `skill/` | the deliverable: `SKILL.md`, `architecture.md`, `tooling.md`, `checks.py`, `verify.py`, `pyproject-snippet.toml`, `requirements-lock.txt` |
| `skill/architecture.md` | the multi-module rules: 70 decisions from round 7, loaded only when a program spans files |
| `benchmark/decisions.jsonl` | all 276 decisions, each with its reasoning and evidence |
| `benchmark/GAPS.md` | gaps found by writing real programs against the skill, and what each rule became |
| `benchmark/round1/` | 24 forced-choice snippet questions |
| `benchmark/round2b/` | side-by-side comparisons that settled specific rules |
| `benchmark/round3/` | two problems in three architectures each, style held constant |
| `benchmark/round4/` | five comparisons that settled the reported gaps |
| `benchmark/round5/` | two measured rule revisions: NAR005 depth, NAR008 data literals |
| `benchmark/round7/` | 41 forced choices on architecture, plus two measured programs; all six blocks answered |
| `benchmark/round8/` | red team: 35 defects from four fresh-context agents, and the NAR008 whitespace measurement |
| `benchmark/round9/` | the skill read as an artifact: four defects in its own text, and V4 as the held-out test |
| `validation/` | held-out tasks, three arms each: no guidance, prior style doc, skill |
| `experiment/length/` | does the style make code longer — four tasks, two arms |

## Status

Ready for real work. Two things are worth knowing before you rely on it.

### The result

The style is trying to do four things. Three can be measured by an agent harness; the fourth cannot.

| goal | verdict |
|---|---|
| 1. shorter than unguided | **yes** — a third less executable code |
| 2. more readable than unguided | **not measured** — human judgement, and the rating forms are empty |
| 3. a future change touches few files and lines | **no on one change** — unguided wins 18/390 against 22/491. **Narrowly yes over two** |
| 4. no worse against the spec | **yes, on twenty blind tests** — 20 of 20 both |

The current comparison is **V5**, a held-out billing reconciler: read two inventory formats, join
them, report what fails to match on either side. Both arms got the same spec, at the same time, and
neither was asked for tests. `base` got the task and nothing else; `full` got the whole skill.
`validation/harness/` holds the instruments for goals 3 and 4.

| | modules | lines | ruff | format | pylint | mypy | checks |
|---|---|---|---|---|---|---|---|
| `base` | 12 | 1317 | 321 | FAIL | 36 | 0 | 14 |
| **`full`** | 12 | **963** | **0** | **ok** | **0** | **0** | **0** |

Split by line kind, the same two programs:

| | `base` | **`full`** |
|---|---|---|
| **code** | 879 | **590** |
| docstring | 232 | 184 |
| comment | 0 | 11 |
| blank | 206 | 178 |

The guided arm is 354 lines shorter, and **289 of those are code**. It gives up a third of the
executable lines and keeps the documentation.

### What the 289 lines would have bought

The two programs were compared module by module and probed on twenty-two edge cases. They agree on
every finding their own fixtures produce, on both exit codes, and on the malformed-file path. They
diverge on four things, and only the last is a gap:

| | `base` | `full` |
|---|---|---|
| region name `ZONE1` vs `zone1` | same region | **different** |
| alias chain `a→b`, `b→c` | follows it, `a` = `c` | **one hop, `a` ≠ `c`** |
| stderr on a clean run | silent | one `INFO` line |
| SQLite columns | 11 | **7** |

The first two are where the spec is silent, and `full` is the more literal reading of it — an alias
is defined as a pair of names, so transitive closure is a rule nobody asked for. Neither is a defect.

The fourth is real. `base` stores `above_grace`, `sources`, `first_seen_at` and `last_seen_at`;
`full` stores none of them, so a query against `full`'s table cannot say which findings set the exit
code, or when a mismatch first appeared, or whether it is still present. That is the one place the
extra code buys something.

Going the other way, `base` ships one dead function — `read_findings`, 14 lines, defined and
exported and never called — and `full` ships none.

**Neither can tell a consumer that a run was degraded.** When an inventory file fails to parse, both
emit `billed_not_found` for every resource that file would have matched, write them to SQLite
indistinguishable from real findings, and exit 1. That defect is shared, unrelated to style, and the
first thing worth fixing in either program.

Two earlier rounds, `v3_manifest_audit` and `v4_quota_reconcile`, ran against older versions of the
skill and are kept as history. Both reproduce the same mechanical shape: `base` at 324 and 367 ruff
findings, the guided arms at zero.

### Does it cost real bugs?

A conformance suite written by an agent that read the spec and **was forbidden to see any
implementation** scores both arms **20 of 20**. That blindness is the control: a suite written after
reading one arm tests that arm's decisions, and every disagreement then scores as the other arm's
bug. It drives each package as a subprocess through its documented entry point, so an arm that
reorganises entirely still passes. It also produced a list of 50 questions the spec does not settle,
at `validation/harness/conformance/UNDERSPECIFIED.md`.

Read the score as *"no difference across twenty spec-derived tests"* rather than *"no difference"*,
for a reason the harness found the hard way. **A maintenance agent found a spec violation the suite
cannot see**: `base` reads input with `encoding='utf-8'` and catches only `OSError`, and
`UnicodeDecodeError` is a `ValueError` — so one non-UTF-8 file aborts the whole run, against
requirement 7, that one malformed file must not stop the others. `full` catches it and carries on.
The suite misses it because every malformed fixture it builds is valid UTF-8.

That test has **not** been added. Writing it now, knowing which arm fails, would end the suite's
blindness and make its score unusable as evidence. `validation/harness/README.md` records the gap.

### Does a future change stay small?

This is the style's own central claim — *"name the change, and the name must give you one file to
open"* — so it is worth measuring rather than asserting. `validation/harness/` holds the instrument.

Four change requests were written from the spec's vocabulary, each naming a different seam. Each arm
received each change **applied to its own codebase**, in an isolated copy, by an agent that saw only
that arm, that change, and — for `full` — the skill. Cost is files touched and lines moved.

| change | what it asks for | `base` files / churn | `full` files / churn |
|---|---|---|---|
| C1 | a third input format | **5 / 137** | 7 / 234 |
| C2 | a fourth finding kind, crossing every layer | 6 / 115 | **5 / 106** |
| C3 | a new rules field | **2 / 48** | 4 / 59 |
| C4 | a new column threaded to three outputs | **5 / 90** | 6 / 92 |
| | **total** | **18 / 390** | 22 / 491 |

**The unguided arm wins, and the result is the opposite of what the style predicts.** `full` absorbs
a cross-layer change better — C2 is the one change designed to touch everything, and it is the one
`full` wins — but pays for it everywhere else.

C1 is most of the gap, and the cause is a rule doing exactly what it says. Asked for a third format
whose parser would be near-identical to an existing one, the guided agent refused to copy it:

> Extracted `cost_line.py` instead of copying the billing parser. A standalone ledger parser would
> have been token-identical to `_parseBillingLine` bar the origin — the rote diffing `R2b-P0` /
> `R2b-E4` forbid. Cost: `billing_csv.py` changed.

That is a refactor of working code that `base` never had to do: 72 new lines, and `billing_csv.py`
cut from 94 lines to 57. **The style trades cost now for cost later** — so the obvious question is
whether "later" ever arrives.

### Does the deferred cost pay off?

A fifth change, `C5`, adds a *fourth* cost format on top of what C1 produced, so each arm starts from
its own C1 output. `base` begins with the four-field validation in two places; `full` begins with it
in one.

| | `base` files / churn | `full` files / churn |
|---|---|---|
| C1 — add a 3rd cost format | **5 / 137** | 7 / 234 |
| C5 — add a 4th cost format | 7 / 228 | **7 / 95** |
| **two-change total** | **12** / 365 | 14 / **329** |

**The crossover is real and it is narrow.** `full` wins the sequence on churn by 36 lines out of 365,
just under 10%, and still loses on files. The two metrics disagree; both are reported.

`base` was not able to duplicate a third time, because the change required identical rejection
messages across the formats. Its agent extracted the validator itself:

> A third copy would satisfy that only by inspection and would drift on the next edit; one function
> satisfies it by construction.

That is `R2b-P0`'s argument, reached from the requirement text rather than from a style rule. So
`base` arrived at the same design one change later, and paid **137 + 228 = 365** to get where `full`
got for **234 + 95 = 329**.

The shape of `full`'s second change is the point. Seven files touched, but only one of substance:

    charges_psv.py   +75  -0     the whole change
    vocabulary.py     +2  -1     one enum member
    inventory.py      +5  -3     one match arm
    join.py           +1  -1     one enum name
    __main__.py       +2  -1     module map line
    cost_line.py      +1  -1     one word in a docstring
    report.py         +1  -1     a re-pasted sample

`base`'s second change had three files of substance: the new reader, the extraction, and the gutting
of the two readers it had duplicated.

**This is not "the style wins in the long run."** A fifth format now costs both arms about 95, since
`base` has the shared validator too. It is narrower than that: the style pays the extraction at the
first change, unguided pays it at the second, and the 36-line difference is the interest. On any
single change measured cold, unguided wins.

**Caveat, and it matters:** `C5` was designed after `C1`, by someone who knew which arm the
extraction favours. It is a fair test of that specific claim and it returned a smaller margin than
expected — but a run designed to check a hypothesis already held is weaker evidence than one designed
before it. The four-change table above was written blind to its own outcome; this one was not.

A second, smaller cost is `R9-08`, the rule that says paste a real sample of a module's output. Two
of `full`'s C1 files and one of its C3 files were touched **only** to re-paste samples that had gone
stale. No behaviour changed in them.

Every non-breaking change left the conformance suite at 20 of 20 for both arms, so none of this was
bought by breaking something. C4 takes both arms to 5 of 20 by design — it makes the old four-column
CSV malformed, which is the point of the change.

### How far this evidence goes

One task, one agent per arm, no repeats. Agent variance is visibly larger than arm variance, and
**no arm wrote tests** — real use would ask for tests and iterate, which plausibly closes most of
what remains. `benchmark/round9/README.md` holds the verdict and the rest of its limits.

### What is still open

**The comparison is not blind.** The directory names identify the arms, and normalising the layout
would destroy what the round measures.

**The subjective rating forms are empty.** Each `RATING.md` holds the analysis and the measurements;
the human judgement rows at the bottom — "is this how I would want it written", "lines I would change
in review" — are unfilled. The project still has no answer to its own stated bar.

**Nothing mechanical justifies `architecture.md`.** A third arm gets `SKILL.md` without it, and ties
`full` at zero on every tool in every round. The case for it rests on the ratings, on the count of
inter-module questions the reduced arm had to invent answers to (17 on V5), and on one functional
result: on V5 that arm was the sole outlier of three on input hardening, with **zero `.strip()` calls
in the package** against 9 in `base` and 6 in `full`, which cost it a join split in two by a padded
identifier and a table that clobbers its own alias mapping.

An older four-task experiment in `experiment/length/` reached the same code-versus-prose conclusion
from a different direction, with weaker evidence — one run per cell, and the arm was edited after the
run. V5 supersedes it.
