# Narrative Python

A Python house style, and a Claude Code skill that writes and reviews against it.

A module reads as a document: `main()` is the thesis, the workflow functions are the argument in
call order, and the types are a glossary at the back under a `### vocabulary` divider.

The module leaves nothing for the reader to infer. Side effects carry a `global` marker, dispatch
over a closed set is exhaustive, `__init__` declares every attribute, and one boundary gate parses
untrusted input into a frozen dataclass.

Every rule cites the decision that produced it. The decisions came from 423 forced choices between
real working programs, not from preference stated in the abstract.

## Install

The skill is nine files in one directory. Clone the repository first, and run every command below
from its root.

```bash
git clone git@github.com:OrderFromChaos/narrative-python.git
cd narrative-python

./install.sh
```

`install.sh` copies the nine files to `~/.claude/skills/narrative`. Give it a path to install
somewhere else. It removes a file the skill no longer ships, and names each one it removes.

Invoke it as `/narrative`, or let Claude load it when a task involves Python in this style.

**To update, run `git pull && ./install.sh`.** Nothing detects a stale install, and a skill installed
at an earlier version keeps its old rules with no warning.

## Dependencies

### The custom checker needs nothing

`checks.py` imports only `argparse`, `ast`, `dataclasses`, `pathlib`, `re` and `sys`. Run it with any
`python3` at 3.11 or later. No virtual environment, no install.

```bash
python3 ~/.claude/skills/narrative/checks.py src/
python3 ~/.claude/skills/narrative/checks.py src/ --select NAR001 --select NAR009
```

### The external toolchain needs `uv`

Four tools and `agentverbs.py` do the work `checks.py` does not, plus the libraries they need.
Install them into a project-local environment:

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
| `pendulum` | 3.2.0 | not a linter. Dates and times use it, and `mypy --strict` needs it importable |
| `spacy`, `en_core_web_md` | 3.8.16, 3.8.0 | the sentence parse behind `agentverbs.py` (`NAR017`) |

The versions are pinned in `requirements-lock.txt`. An unpinned install can change what the config
means, because ruff moved `[tool.ruff.lint]` in 0.2.

**Merge** `pyproject-snippet.toml` into your project's `pyproject.toml`. If the project has none,
copy the file and rename it:

```bash
cp ~/.claude/skills/narrative/pyproject-snippet.toml pyproject.toml   # new project
```

The settings are not defaults and several are load-bearing. `tooling.md` records why each one is
there and what breaks without it.

### Comments and docstring prose

Comments and docstrings are written for a smart, experienced developer who has the file open, so
trade vocabulary is correct and a plain-English circumlocution around it is not.

Claude's comments tend to record the reasoning it did while writing: edge cases, alternatives and
spec gaps. The rules in `SKILL.md`, **Comments**, open with a test (what information does this
comment provide over the code itself?) and two paragraphs against this: that reasoning is a
thinking trace for the report to the user, and a comment a smart reader would get from the code
below it is cut. In blind ratings over four runs per variant, the author cut 0 of 18 comments
written with both paragraphs, against 11 of 28 with the cut rule alone. Four comment kinds with a
test for each, a list of what is never a comment, and the sentence form follow. They come from
round 10 (`benchmark/round10/`), which measured Claude's comments against human-written ones and
put 53 forced choices to the author.

**Six wording faults in comments and docstrings are checked**: decision ids (`NAR012`), a dash
or semicolon joining clauses (`NAR013`), `deliberately` and its synonyms (`NAR014`), changelog wording
(`NAR015`), the container verbs `holds` and `carries` (`NAR016`), and a possessive `own`
(`NAR018`). Everything else is review judgement. `NAR011` catches the one mechanical
docstring trap: a body indented past the docstring's column, which `ruff format` flattens, destroying a
pasted sample. (`R9-09`, `R10-lint`)

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
`mypy --strict`, `checks.py`, `vermin`, `agentverbs.py`. After a passing run it lists every comment
and docstring summary, for the agent to read against the comment rules.

| exit | meaning |
|---|---|
| 0 | every tool passed |
| 1 | at least one tool reported a finding |
| 2 | the toolchain or the config is missing, so nothing was checked |

The `vermin` call uses `-t=3.11-` with a trailing hyphen. Without it `vermin` asserts an exact
match and fails any file that uses no 3.11-only feature.

## The eighteen custom rules

`checks.py` implements what no off-the-shelf tool does. `agentverbs.py` implements `NAR017`.

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
| `NAR011` | a docstring body indented past the docstring's column, which `ruff format` flattens, destroying a pasted sample |
| `NAR012` | a decision id in a comment or docstring, unresolvable outside the repository that recorded it |
| `NAR013` | a dash or a semicolon joining clauses in a comment or docstring |
| `NAR014` | `deliberately`, `on purpose`, `by design` or `intentionally` in a comment or docstring |
| `NAR015` | changelog wording in a comment or docstring: `no longer`, `previously`, `it used to` |
| `NAR016` | a container verb in a comment or docstring: `holds`, `carries` and their forms |
| `NAR017` | an agent verb on a subject that cannot act, in a comment or docstring: `a period ranks`, `the report names it`. From a spaCy parse and WordNet word classes |
| `NAR018` | a possessive `own` in a comment or docstring: `its own`, `the layer's own` |
| `NAR019` | a return contract written as a comment at the top of a function body, where the docstring belongs |

`NAR000` is not a style rule. It reports a file that could not be read or parsed.

**Blank lines inside a function are review judgement, and no check enforces them.** `NAR008` is
withdrawn and its code stays in a `RETIRED` registry, so a document naming it still resolves while
`--select` never offers it. (`R8-NAR008`)

## What is in this repository

| path | contents |
|---|---|
| `skill/` | the deliverable: `SKILL.md`, `architecture.md`, `tooling.md`, `checks.py`, `verify.py`, `agentverbs.py`, `words.json`, `pyproject-snippet.toml`, `requirements-lock.txt` |
| `skill/architecture.md` | the multi-module rules: 70 decisions from round 7, loaded only when a program spans files |
| `install.sh` | the list of files the skill contains, and the command that installs them |
| `benchmark/decisions.jsonl` | all 338 decisions, each with its reasoning and evidence |
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
| `validation/v5_billing_reconcile/` | the billing reconciler against an **imprecise** spec — the outputs are named, not specified |
| `validation/v6_report_contract/` | the same task against a **precise** spec, with the report pinned to the byte; both arms rewritten against it |
| `validation/harness/` | the instruments: the blind conformance suite, the change requests, `UNDERSPECIFIED.md` |
| `experiment/length/` | does the style make code longer — four tasks, two arms |

## Status

Ready for real work. Two things are worth knowing before you rely on it.

### The result

The style is trying to do four things. Three can be measured by an agent harness; the fourth cannot.

| goal | verdict |
|---|---|
| 1. shorter than unguided | **yes** — executable lines run **33% below the unguided arm** against an ordinary spec, and **9% below it** against one that pins its outputs |
| 2. more readable than unguided | **not measured** — human judgement, and the rating forms are empty |
| 3. a future change touches few files and lines | **lines yes, files no** — a two-step cycle costs 329 lines against 365, over 14 files against 12 |
| 4. no worse against the spec | **yes, on twenty blind tests** — 20 of 20 both |

The comparison is a held-out billing reconciler: read two inventory formats, join them, report what
fails to match on either side. Two rounds run it against two versions of its own specification.

| round | spec | holds constant |
|---|---|---|
| **V5** | the outputs are named, not specified — *"write a JSON report"* | nothing; each arm chooses its own report scope |
| **V6** | the report schema, the ordering, the exit codes and the join semantics are pinned to the byte | output scope, so the remaining difference is style |

In both, `base` gets the task and nothing else, `full` gets the whole skill, both get the same spec
at the same time, and neither is asked for tests. `validation/harness/` holds the instruments for
goals 3 and 4.

**V6, the precise spec** — `validation/v6_report_contract/`:

| | modules | lines | ruff | format | pylint | mypy | checks |
|---|---|---|---|---|---|---|---|
| `base` | 14 | 1380 | 93 | FAIL | 32 | 2 | 2 |
| **`full`** | 14 | **1316** | **0** | **ok** | **0** | **0** | **0** |

**V5, the imprecise spec** — `validation/v5_billing_reconcile/`:

| | modules | lines | ruff | format | pylint | mypy | checks |
|---|---|---|---|---|---|---|---|
| `base` | 12 | 1317 | 321 | FAIL | 36 | 0 | 14 |
| **`full`** | 12 | **963** | **0** | **ok** | **0** | **0** | **0** |

The guided arm is clean on every tool in both rounds and the unguided arm is not, by a margin larger
than agent variance.

Split by line kind, one counter across all four programs:

| | V5 `base` | V5 **`full`** | V6 `base` | V6 **`full`** |
|---|---|---|---|---|
| **code** | 879 | **590** | 831 | **752** |
| docstring | 182 | 146 | 271 | 282 |
| comment | 0 | 11 | 5 | 12 |
| blank | 256 | 216 | 273 | 270 |
| **total** | 1317 | **963** | 1380 | **1316** |

**Against an ordinary spec the guided arm gives up 289 code lines, a third.** That is the figure to
expect in real use, because an ordinary spec is what a person writes: V5 names its outputs and does
not specify them, and so do V1 to V4.

**Pinning the outputs narrows the gap to 79 lines, 9% of `base`'s 831.** `full` gains 162 code lines between
the rounds and `base` loses 48, because `full`'s V5 report emitted three top-level keys where
`base`'s emitted eight, and both are correct answers to V5's text. The 210-line narrowing is not
purely scope — each round is a fresh agent draw on both arms, and nothing here separates the two
effects.

Both percentages measure the guided arm against the unguided arm of the same round: 289 of `base`'s
879 code lines in V5, 79 of its 831 in V6. They answer two questions. **33% below unguided** is what
the skill delivers on the specs people write. **9% below unguided** is what it delivers when both
arms are made to emit the same bytes, and that is the part attributable to how the code is written
rather than to how much the program was asked to do. The remainder is bought by the guided arm
choosing a narrower report — mostly harmless, and documented below as a real loss in one place.

The docstring row runs the other way: against the precise spec the guided arm carries more prose
than the unguided one.

### V5: what the 289 lines would have bought

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

### What does a future change cost?

This is the style's own central claim — *"name the change, and the name must give you one file to
open"* — so it is measured rather than asserted. `validation/harness/` holds the instrument.

Five change requests were written from the spec's vocabulary, each naming a different seam. Each arm
received each change **applied to its own codebase**, in an isolated copy, by an agent that saw only
that arm, that change, and — for `full` — the skill. Cost is files touched and lines moved.

**A maintained program pays for a change over the whole cycle it starts, so the cycle is the unit.**
`C1` adds a third cost format and `C5` adds a fourth on top of it, which is one cycle in two steps:

| | `base` files / churn | `full` files / churn |
|---|---|---|
| C1 — add a 3rd cost format | **5 / 137** | 7 / 234 |
| C5 — add a 4th cost format | 7 / 228 | **7 / 95** |
| **the cycle** | **12** / 365 | 14 / **329** |

`full` completes the cycle for 36 fewer lines out of 365, just under 10%, while touching two more
files. The two metrics disagree and both are reported.

The step costs differ because the arms buy the shared parser at different points. Asked at `C1` for
a third format whose parser would be near-identical to an existing one, the guided agent refused to
copy it:

> Extracted `cost_line.py` instead of copying the billing parser. A standalone ledger parser would
> have been token-identical to `_parseBillingLine` bar the origin — the rote diffing `R2b-P0` /
> `R2b-E4` forbid. Cost: `billing_csv.py` changed.

At `C5` the unguided arm reaches the same design, because the spec demands identical rejection
messages across formats and a third copy cannot guarantee that:

> A third copy would satisfy that only by inspection and would drift on the next edit; one function
> satisfies it by construction.

Both arms therefore end the cycle with one shared validator and four readers. `full` paid 234 then
95; `base` paid 137 then 228. **A fifth format costs either arm about 95 from here.**

The shape of the second step is where the difference sits. `full` touched seven files and one of
substance:

    charges_psv.py   +75  -0     the whole change
    vocabulary.py     +2  -1     one enum member
    inventory.py      +5  -3     one match arm
    join.py           +1  -1     one enum name
    __main__.py       +2  -1     module map line
    cost_line.py      +1  -1     one word in a docstring
    report.py         +1  -1     a re-pasted sample

`base` touched seven with three of substance: the new reader, the extraction, and the gutting of the
two readers it had duplicated.

**Three changes that open no cycle**, each measured cold against the pristine arm:

| change | what it asks for | `base` files / churn | `full` files / churn |
|---|---|---|---|
| C2 | a fourth finding kind, crossing every layer | 6 / 115 | **5 / 106** |
| C3 | a new rules field | **2 / 48** | 4 / 59 |
| C4 | a new column threaded to three outputs | **5 / 90** | 6 / 92 |

`full` wins the change designed to touch every layer and loses the two narrower ones, by 11 lines
and 2 lines. Across all five changes the guided arm touches more files in every case but one.

A cost that shows up in three of the five is `R9-08`, the rule that says paste a real sample of a
module's output. Two of `full`'s C1 files, one of its C3 files and one of its C5 files were touched
**only** to re-paste samples that had gone stale. No behaviour changed in them.

Every non-breaking change left the conformance suite at 20 of 20 for both arms, so none of this was
bought by breaking something. C4 takes both arms to 5 of 20 by design — it makes the old four-column
CSV malformed, which is the point of the change.

**On evidence strength:** `C1` through `C4` were written before any of them ran. `C5` was written
after `C1` was measured, by someone who knew which arm the extraction favours. A run designed to test
a held hypothesis is weaker evidence than one designed before the hypothesis exists, and the cycle
result rests on `C5`.

### V6: the report pinned to the byte

A later round adds an acceptance test the spec states itself: two correct implementations must
produce byte-identical report JSON for the same input, excepting the run time, the input path and
the wording inside `problems`. Both arms were written fresh against it, blind to each other and blind
to an oracle derived from the spec alone by a third agent. All three agree — `base` against the
oracle identical, `full` against the oracle identical, `base` against `full` **byte-identical at 5569
bytes**. One ambiguity survives, found independently by both arms: `sources` on a finding whose other
side is *ignored* rather than *rejected*, which the spec excludes only for rejected records. Both
arms and the oracle pick the same reading by reasoning rather than because the text compels it.
`validation/v6_report_contract/RATING.md` holds the round, including the five adversarial passes the
contract took to write and the two gaps introduced while closing earlier ones.

### How far this evidence goes

One task, one agent per arm per round, no repeats. Agent variance is visibly larger than arm
variance, and **no arm wrote tests** — real use would ask for tests and iterate, which plausibly
closes most of what remains. `benchmark/round9/README.md` holds the verdict and the rest of its
limits.

V5 and V6 are two runs of one task, not two tasks. They share a domain, a fixture design and an
author, which makes them a controlled pair on one variable rather than two independent samples of
the style. The code-line difference between the rounds also carries a fresh agent draw on both arms,
and nothing here separates that from the effect of the pinned contract.

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

**Every length number here except V6's carries output scope as well as style.** V1 to V5 all name
their outputs without specifying them, so each arm sets its own report scope, and the guided arm
sets a narrower one. V6 is the only round that holds scope constant. It puts the guided arm 9% below
the unguided one on executable lines, where the open-spec rounds put it 33% below.

Which figure is the honest one depends on the question. A reader choosing whether to adopt the skill
should use 33%, since an ordinary spec is what they will write against. A reader asking what the
*style rules* do, as opposed to what the guided arm chooses to build, should use 9%.

An older four-task experiment in `experiment/length/` reaches the same code-versus-prose conclusion
from a different direction, with weaker evidence — one run per cell, and the arm was edited after the
run. V5 supersedes it, and the scope caveat above applies to both.
