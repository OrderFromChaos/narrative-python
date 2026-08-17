# Narrative Python

A Python house style, and a Claude Code skill that writes and reviews against it.

A module reads as a document: `main()` is the thesis, the workflow functions are the argument in
call order, and the types are a glossary at the back under a `### vocabulary` divider.

The module leaves nothing for the reader to infer. Side effects carry a `global` marker, dispatch
over a closed set is exhaustive, `__init__` declares every attribute, and one boundary gate parses
untrusted input into a frozen dataclass.

Every rule cites the decision that produced it. The decisions came from 86 forced choices between
real working programs, not from preference stated in the abstract.

## Install

The skill is four files in one directory.

```bash
mkdir -p ~/.claude/skills/narrative
cp skill/SKILL.md skill/tooling.md skill/checks.py skill/pyproject-snippet.toml \
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
uv pip install --python .lintenv/bin/python ruff pylint mypy vermin
echo '.lintenv/' >> .gitignore
```

| tool | version verified | what it owns |
|---|---|---|
| `ruff` | 0.16.3 | formatting, imports, annotations, bugbear, quotes, banned APIs |
| `pylint` | 4.0.7 | `mixedCase` function names — **no other linter can require this** |
| `mypy` | 2.3.1 | type correctness under `--strict` |
| `vermin` | 1.8.0 | the Python 3.10 floor |

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

Order matters. `ruff check --fix` and `ruff format` disagree in one direction and converge in the
other. If you run format first, it leaves findings that the next check re-introduces.

```bash
.lintenv/bin/ruff check --fix src/ && .lintenv/bin/ruff format src/
.lintenv/bin/pylint --rcfile=pyproject.toml src/
.lintenv/bin/mypy --strict src/
python3 ~/.claude/skills/narrative/checks.py src/
.lintenv/bin/vermin --no-tips -t=3.10- --violations src/
```

The trailing hyphen in `-t=3.10-` is required. Without it `vermin` asserts an exact match and fails
any file that happens to use no 3.10-only feature.

## The nine custom rules

`checks.py` implements what no off-the-shelf tool does.

| rule | catches |
|---|---|
| `NAR001` | module state mutated with no `global` — **ruff and pylint report nothing on this at any setting** |
| `NAR002` | `hasattr(self, ...)`, meaning an attribute is conditionally defined |
| `NAR003` | more than three *positional* arguments on one `def` line |
| `NAR004` | no docstring where the contract is complex: raises, >3 parameters, or long |
| `NAR005` | an annotation nested deeper than 2, which means the code needs a dataclass |
| `NAR006` | an assignment that shadows a module name, so the module value silently never changes |
| `NAR007` | `and` inside `or` without parentheses |
| `NAR008` | a multi-line statement butted against the next with no blank line |
| `NAR009` | a missing module docstring, or a runnable module with no usage example |

## What is in this repository

| path | contents |
|---|---|
| `skill/` | the deliverable — `SKILL.md`, `tooling.md`, `checks.py`, `pyproject-snippet.toml` |
| `skill/GAPS.md` | gaps found by writing real programs against the skill, and what each rule became |
| `benchmark/decisions.jsonl` | all 86 decisions, each with its reasoning and evidence |
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

**Does the style make code longer?** Measured over four tasks against unguided Claude: 14% more
total lines, and **6.5% less actual logic**. The extra is documentation and blank lines. On one of
the four the styled version had 22% less logic than the unguided one.

| | unguided | Narrative |
|---|---|---|
| total | 899 | 1027 |
| code | 612 | **572** |
| docstring | 140 | 162 |
| comment | 5 | 66 |
| blank | 142 | 227 |
