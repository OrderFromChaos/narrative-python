# Narrative Python

A Python house style, and a Claude Code skill that writes and reviews against it.

A module reads as a document: `main()` is the thesis, the workflow functions are the argument in
call order, and the types are a glossary at the back under a `### vocabulary` divider.

The module leaves nothing for the reader to infer. Side effects carry a `global` marker, dispatch
over a closed set is exhaustive, `__init__` declares every attribute, and one boundary gate parses
untrusted input into a frozen dataclass.

Every rule cites the decision that produced it. The decisions came from 254 forced choices between
real working programs, not from preference stated in the abstract.

## Install

The skill is eight files in one directory. Clone the repository first, and run every command below
from its root.

```bash
git clone git@github.com:OrderFromChaos/narrative-python.git
cd narrative-python

mkdir -p ~/.claude/skills/narrative
cp skill/SKILL.md skill/architecture.md skill/tooling.md skill/GAPS.md \
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

### Simplified Technical English, for prose only

Write module docstrings in STE: one idea per sentence, active voice, one word for one thing.
Narrative defers to the `ste-writing` skill for that prose, which implements ASD-STE100 Issue 9
(January 2025).

Source: [ste-writing-skill.md](https://github.com/woosal1337/blog/blob/main/videos/ep01-the-cure-for-ai-slop/ste-writing-skill.md).
Install it alongside its two companion files, `ste-lint.py` and `ste-recurring-errors.md`:

```bash
mkdir -p ~/.claude/skills/ste-writing   # then add SKILL.md, ste-lint.py, ste-recurring-errors.md
```

It has two modes. **STE-flavored** covers docstrings, comments and READMEs. **Strict** covers
runbooks and safety text. The linter takes a file argument, not `--help`, which tracebacks:

```bash
python3 ~/.claude/skills/ste-writing/ste-lint.py src/loader.py
python3 ~/.claude/skills/ste-writing/ste-lint.py --strict RUNBOOK.md
```

This is a **soft dependency**. Without it the rule still stands and `NAR009` still enforces that the
docstring exists. Only the wording guidance is absent.

`verify.py` looks for it at that path and takes `--ste-lint <path>` if you keep it elsewhere. When it
is missing, the run reports `SKIPPED, prose was not checked` and still exits 0. Read that row: a
skipped check is not a clean one.

STE governs docstrings, comments and READMEs. It never governs code, and it never governs
identifiers.

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
python3 ~/.claude/skills/narrative/verify.py . --ste-lint path/to/ste-lint.py
```

One command covers the project. It sorts Python files from prose, runs the six code checks on the
first and the STE linter on the second, so nothing has to choose a workflow.

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

## The nine custom rules

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

`NAR000` is not a style rule. It reports a file that could not be read or parsed.

`NAR008` was withdrawn. It asked for a blank line after any statement of three or more lines, and
measured at 42% precision and 22% recall against hand-marked whitespace, so the rule it stood for is
now review judgement. `checks.py` keeps the code in a `RETIRED` registry so the writeups that
measured it still resolve. (`R8-NAR008`)

## What is in this repository

| path | contents |
|---|---|
| `skill/` | the deliverable: `SKILL.md`, `architecture.md`, `tooling.md`, `GAPS.md`, `checks.py`, `verify.py`, `pyproject-snippet.toml`, `requirements-lock.txt` |
| `skill/architecture.md` | the multi-module rules: 70 decisions from round 7, loaded only when a program spans files |
| `skill/GAPS.md` | gaps found by writing real programs against the skill, and what each rule became |
| `benchmark/decisions.jsonl` | all 254 decisions, each with its reasoning and evidence |
| `benchmark/round1/` | 24 forced-choice snippet questions |
| `benchmark/round2b/` | side-by-side comparisons that settled specific rules |
| `benchmark/round3/` | two problems in three architectures each, style held constant |
| `benchmark/round4/` | five comparisons that settled the reported gaps |
| `benchmark/round5/` | two measured rule revisions: NAR005 depth, NAR008 data literals |
| `benchmark/round7/` | 41 forced choices on architecture, plus two measured programs; all six blocks answered |
| `benchmark/round8/` | red team: 35 defects from four fresh-context agents, and the NAR008 whitespace measurement |
| `validation/` | held-out tasks, three arms each: no guidance, prior style doc, skill |
| `experiment/length/` | does the style make code longer — four tasks, two arms |

## Status

Ready for real work. Two things are worth knowing before you rely on it.

**The blind validation was never done.** Six implementations exist across two held-out tasks and
`RATING.md` is still an empty form. Nobody judged the comparison that matters, skill against the
prior style doc, so the project has no answer to its own stated bar. The reported line counts had
already compromised the blinding by going out before any rating.

**The mechanical scores were wrong, and are now regenerated.** `SCORES.json` recorded `checks: 0`
for an arm that has a finding, and a line count that was off by one — both wrong when written,
confirmed against the checker as shipped at the time (`R8-D36`). It also recorded `mypy: 0` for an
arm that needs `hypothesis`, which was not in `requirements-lock.txt`, so the toolchain could not
check code the style mandates (`R8-F05`). Current numbers, all six arms, one checker:

| | lines | ruff | pylint | mypy | checks |
|---|---|---|---|---|---|
| v1 skill | 497 | **0** | 0 | 0 | **1** |
| v1 doc | 534 | 4 | 0 | 0 | 8 |
| v1 base | 656 | 185 | 12 | 23 | 2 |
| v2 skill | 513 | 2 | 0 | 0 | **1** |
| v2 doc | 336 | 10 | 0 | 0 | 5 |
| v2 base | 758 | 230 | 39 | 0 | 7 |

The skill arm wins on `checks` and on `ruff` in both tasks. **One ordering inverted**: on `v1`
`checks`, base now scores better than doc, because most of what the doc arm was penalised for was
`NAR008`, which has since been withdrawn. Read the whole table as measuring today's checker, not the
one that produced the original numbers.

**Does the style make code longer?** Measured over four tasks against unguided Claude. Both arms
got identical instructions and neither was asked for tests.

| | unguided | Narrative |
|---|---|---|
| total | 899 | 1144 |
| **code** | **612** | **572** |
| docstring | 140 | 274 |
| comment | 5 | 66 |
| blank | 142 | 232 |

Read that aggregate with three caveats, because it is weaker than it looks.

**The sign flips per task.** Narrative wrote *more* logic on two of the four:

| | t1 | t2 | t3 | t4 |
|---|---|---|---|---|
| code, unguided → Narrative | 204 → 210 | 101 → 107 | 166 → **129** | 141 → **126** |

The 6.5% aggregate rests entirely on t3 and t4.

**The sample is four, one run per cell, no repeats and no variance measured.** It is a direction,
not a number.

**The Narrative arm was edited after the run.** The module-docstring rule landed later, and
retrofitting it added 117 lines to these four files. So 1144 is a post-hoc artefact rather than a
one-pass result. The `code` count did not move, which is the reason to trust that figure and not
the total.

What survives all three caveats: **the style adds documentation and whitespace, not logic.**
