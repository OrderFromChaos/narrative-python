# Narrative Python

A Python house style, and a Claude Code skill that writes and reviews against it.

A module reads as a document: `main()` is the thesis, the workflow functions are the argument in
call order, and the types are a glossary at the back under a `### vocabulary` divider.

The module leaves nothing for the reader to infer. Side effects carry a `global` marker, dispatch
over a closed set is exhaustive, `__init__` declares every attribute, and one boundary gate parses
untrusted input into a frozen dataclass.

Every rule cites the decision that produced it. The decisions came from 105 forced choices between
real working programs, not from preference stated in the abstract.

## Install

The skill is seven files in one directory.

```bash
mkdir -p ~/.claude/skills/narrative
cp skill/SKILL.md skill/tooling.md skill/GAPS.md skill/checks.py skill/verify.py \
   skill/requirements-lock.txt \
   skill/pyproject-snippet.toml \
   ~/.claude/skills/narrative/
```

Invoke it as `/narrative`, or let Claude load it when a task involves Python in this style.

## Dependencies

### The custom checker needs nothing

`checks.py` imports only `argparse`, `ast`, `dataclasses`, `pathlib` and `sys`. Run it with any
`python3` at 3.10 or later. No virtual environment, no install.

```bash
python3 ~/.claude/skills/narrative/checks.py src/
python3 ~/.claude/skills/narrative/checks.py src/ --select NAR001 --select NAR009
```

### The external toolchain needs `uv`

Four tools do the work `checks.py` does not. Install them into a project-local environment:

```bash
uv venv .lintenv
uv pip install --python .lintenv/bin/python -r ~/.claude/skills/narrative/requirements-lock.txt
echo '.lintenv/' >> .gitignore
```

| tool | pinned version | what it owns |
|---|---|---|
| `ruff` | 0.16.3 | formatting, imports, annotations, bugbear, quotes, banned APIs |
| `pylint` | 4.0.7 | `mixedCase` function names — **no other linter can require this** |
| `mypy` | 2.3.1 | type correctness under `--strict` |
| `vermin` | 1.8.0 | the Python 3.10 floor |

The versions are pinned in `requirements-lock.txt`. An unpinned install can change what the config
means, because ruff moved `[tool.ruff.lint]` in 0.2.

Copy `pyproject-snippet.toml` into the `pyproject.toml` of your project. The settings are not
defaults and several are load-bearing. `tooling.md` records why each one is there and what breaks
without it.

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

STE governs docstrings, comments and READMEs. It never governs code, and it never governs
identifiers.

### Python version

Write for **3.10**. `ruff` targets `py310` and `vermin` checks it. Two things this rules out, both
cheap to avoid: `datetime.UTC` (use `datetime.timezone.utc`) and `typing.assert_never` (omit the
fallback arm instead, see `SKILL.md`). Also unavailable: `enum.StrEnum`, `asyncio.TaskGroup`,
`asyncio.timeout()`, `typing.Self`, `tomllib`.

## Verify

Run `verify.py`. Do not call the tools by hand.

```bash
cd your-project                                          # both defaults are relative
python3 ~/.claude/skills/narrative/verify.py .           # rewrites files: runs --fix and format
python3 ~/.claude/skills/narrative/verify.py . --no-fix  # reports only, changes nothing
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

The `vermin` call uses `-t=3.10-` with a trailing hyphen. Without it `vermin` asserts an exact
match and fails any file that uses no 3.10-only feature.

## The ten custom rules

`checks.py` implements what no off-the-shelf tool does.

| rule | catches |
|---|---|
| `NAR001` | module state mutated with no `global` — **ruff and pylint report nothing on this at any setting** |
| `NAR002` | `hasattr(self, ...)`, meaning an attribute is conditionally defined |
| `NAR003` | more than three *positional* arguments on one `def` line |
| `NAR004` | no docstring where the contract is complex: raises, >3 parameters, or long |
| `NAR005` | an annotation deeper than 2 or wider than 3: a callable needs a `Protocol`, anything else a dataclass |
| `NAR006` | an assignment that shadows a module name, so the module value silently never changes |
| `NAR007` | `and` inside `or` without parentheses |
| `NAR008` | a multi-line statement butted against the next with no blank line |
| `NAR009` | a missing module docstring, or a runnable module with no usage example |
| `NAR010` | a `FIXME` in code that runs, which is a merge blocker rather than a danger sign |

`NAR000` is not a style rule. It reports a file that could not be read or parsed.

## What is in this repository

| path | contents |
|---|---|
| `skill/` | the deliverable: `SKILL.md`, `tooling.md`, `checks.py`, `verify.py`, `pyproject-snippet.toml` |
| `skill/GAPS.md` | gaps found by writing real programs against the skill, and what each rule became |
| `benchmark/decisions.jsonl` | all 105 decisions, each with its reasoning and evidence |
| `benchmark/round1/` | 24 forced-choice snippet questions |
| `benchmark/round2b/` | side-by-side comparisons that settled specific rules |
| `benchmark/round3/` | two problems in three architectures each, style held constant |
| `benchmark/round4/` | five comparisons that settled the reported gaps |
| `validation/` | held-out tasks, three arms each: no guidance, prior style doc, skill |
| `experiment/length/` | does the style make code longer — four tasks, two arms |

## Status

Ready for real work. Two things are worth knowing before you rely on it.

**The blind validation is not finished.** Six implementations exist across two held-out tasks, but
the reported line counts compromised the blinding. The counts went out before the rating, which
makes each arm identifiable. No one judged the comparison that matters: skill against the prior
style doc.

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
