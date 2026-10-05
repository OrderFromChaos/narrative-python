# Narrative

**Makes Python Claude outputs pleasing to read: ~33% less code, zero mypy findings, and
human-like comments.**

## What you get

- ✂️ **A third less code to review.** Programs Claude writes (based on a realistic spec) with the skill have
  33% fewer executable lines. With a highly detailed output spec contract, the savings are 9%.
- ✅ **Passes mypy --strict.** Contains an opinionated linting pipeline including ruff, pylint, `mypy --strict`, 17 custom AST checks, and NLP checks for inanimate agent verbs and cut subjects.
- 🎯 **No loss in spec correctness.** Guided and unguided programs pass the same blind conformance tests.
- 💬 **Comments a reviewer wants.** Most of Claude's writing tics fall to the human rate or below, and comments are added for good reasons only.
- 🔧 **Does not cause catastrophic tech debt problems.** Two consecutive change requests cost 329 changed lines with the
  skill against 365 without it, over 14 files against 12.
- ⚡ **One command for the whole toolchain.** `verify.py` runs every tool in the right order, and
  exits 2 when a tool is missing, so a missing tool never passes as a clean run.
- 🌐 **Transferrable to other languages.** The rules and checks are for Python, but the principles carry over. In my
  experience, asking Claude to take the good parts of `/narrative` into another language works
  well.

Rules come from 433 human-selected choices between real working programs.

⚠️ This skill has an opinionated ordering for code (`main()` first, then the steps it calls in call order, then the types). This does produce readable and pleasing code, but may lead to code differences between your PRs and the rest of your codebase. It will not force migrate the rest of your codebase to this style unless you tell it to.

## Before and after

The caption of a map preview card from [gtnh-seedlib](https://github.com/OrderedSet86/gtnh-seedlib/blob/a2e868884ac8e4bb4ab4eb5460bdd849e523fd1a/tools/make_preview.py#L68).
Both versions draw the same image.

**Without the skill:**

```python
def caption(card: Image.Image, title: str, subtitle: str) -> None:
    """Draw the title block over a bottom-up gradient scrim.

    The scrim is not decoration. The text sits over whatever terrain happens to be at the bottom
    of the crop -- snow, desert, a village roof -- and light-on-light is unreadable on the one
    surface where it matters most.
    """
    scrim_h = 240
    scrim = Image.new("L", (1, scrim_h))
    for y in range(scrim_h):
        # Ramp to 94% rather than fully opaque: the map should still read through the darkest
        # part. The exponent stays near-linear on purpose -- a steeper curve keeps the scrim
        # nearly clear until it is level with the text, which is exactly where it is needed.
        scrim.putpixel((0, y), int(240 * (y / (scrim_h - 1)) ** 1.15))
    scrim = scrim.resize((CARD_W, scrim_h))
    card.paste(Image.new("RGB", (CARD_W, scrim_h), BG), (0, CARD_H - scrim_h), scrim)

    d = ImageDraw.Draw(card)
    d.text((48, CARD_H - 118), title, font=_font("DejaVuSans-Bold.ttf", 46), fill=FG)
    d.text((48, CARD_H - 58), subtitle, font=_font("DejaVuSans.ttf", 24), fill=DIM)
    # A thin accent rule anchors the text block to the left edge so it does not float.
    d.rectangle((48, CARD_H - 140, 48 + 76, CARD_H - 136), fill=ACCENT)
```

**With the skill:**

```python
def caption(card: Image.Image, title: str, subtitle: str) -> None:
    """Draw the title, the subtitle and an accent rule at the card's bottom left, over a dark scrim."""
    SCRIM_HEIGHT = 240
    SCRIM_PEAK_ALPHA = 240  # 94% opaque at the card's bottom edge
    SCRIM_EXPONENT = 1.15
    TEXT_LEFT = 48
    TITLE_TOP = CARD_H - 118
    TITLE_FONT_SIZE = 46
    SUBTITLE_TOP = CARD_H - 58
    SUBTITLE_FONT_SIZE = 24
    RULE_TOP = CARD_H - 140
    RULE_WIDTH = 76
    RULE_THICKNESS = 4

    # without the scrim, light text is unreadable over snow or desert at the card's bottom edge
    alphas = [int(SCRIM_PEAK_ALPHA * (y / (SCRIM_HEIGHT - 1)) ** SCRIM_EXPONENT) for y in range(SCRIM_HEIGHT)]
    scrim_column = Image.new('L', (1, SCRIM_HEIGHT))
    scrim_column.putdata(alphas)
    scrim_mask = scrim_column.resize((CARD_W, SCRIM_HEIGHT))
    card.paste(Image.new('RGB', scrim_mask.size, BG), (0, CARD_H - SCRIM_HEIGHT), scrim_mask)

    draw = ImageDraw.Draw(card)
    draw.text((TEXT_LEFT, TITLE_TOP), title, font=_font('DejaVuSans-Bold.ttf', TITLE_FONT_SIZE), fill=FG)
    draw.text((TEXT_LEFT, SUBTITLE_TOP), subtitle, font=_font('DejaVuSans.ttf', SUBTITLE_FONT_SIZE), fill=DIM)
    draw.rectangle((TEXT_LEFT, RULE_TOP, TEXT_LEFT + RULE_WIDTH, RULE_TOP + RULE_THICKNESS), fill=ACCENT)
```

## Claude's comments, with and without the skill

`human code` is the CPython standard library and the mypy, pylint and astroid sources. `Claude, with the skill` is ten
runs of the shipped skill, one on each of ten tasks, with 95% CIs. Values indicate rate/100 comment blocks.

| | Claude, no skill | human code | Claude, with the skill |
|---|---|---|---|
| comment blocks (n=) | 2,578 | 21,977 | 84 |
| median words | 24 | 9 | 11 [10, 11] |
| p90 words | 83 | 29 | 17 [15, 20] |
| more than one sentence (%) | 45.0 | 14.8 | 8.3 [4.1, 16.2] |
| `, not` contrast | 10.7 | 0.4 | 1.2 [0.2, 6.4] |
| dash | 23.9 | 1.0 | 0.0 [0.0, 4.4] |
| `every`, `never`, `whole`, `exactly` | 31.1 | 1.5 | 6.0 [2.6, 13.2] |
| `the one` / `one place` | 2.2 | 0.1 | 1.2 [0.2, 6.4] |
| `deliberately`, `on purpose`, `by design` | 2.1 | 0.1 | 0.0 [0.0, 4.4] |
| `rather than` / `instead of` | 18.2 | 1.1 | 0.0 [0.0, 4.4] |
| `, so` between clauses | 32.9 | 2.9 | 14.3 [8.4, 23.3] |
| semicolon | 18.5 | 2.3 | 0.0 [0.0, 4.4] |
| agent verb: `finds`, `knows`, `wants`, `decides`, `owns` | 2.3 | 0.3 | 0.0 [0.0, 4.4] |
| container verb: `holds`, `carries`, `keeps`, `names` | 11.3 | 1.8 | 0.0 [0.0, 4.4] |
| intensifier: `genuine`, `actually`, `really`, `truly` | 8.3 | 1.4 | 0.0 [0.0, 4.4] |
| article before an identifier: `the foo()` | 2.8 | 0.5 | 0.0 [0.0, 4.4] |
| `because` | 9.2 | 2.3 | 1.2 [0.2, 6.4] |
| passive voice | 26.0 | 12.5 | 8.3 [4.1, 16.2] |
| changelog: `now`, `no longer`, `used to` | 2.9 | 2.4 | 0.0 [0.0, 4.4] |
| hedge: `usually`, `probably`, `might` | 0.3 | 2.0 | 0.0 [0.0, 4.4] |
| first person: `we`, `our`, `I` | 2.0 | 16.4 | 0.0 [0.0, 4.4] |
| `TODO`, `NOTE`, `FIXME` | 0.1 | 3.6 | 0.0 [0.0, 4.4] |

The skill brings most rows to the human rate or below.

## Install

Clone the repository and run the installer from its root:

```bash
git clone git@github.com:OrderFromChaos/narrative-python.git
cd narrative-python

./install.sh
```

`install.sh` copies the skill's nine files to `~/.claude/skills/narrative`, or to a path you give
it. Invoke the skill as `/narrative`, or let Claude
load it when a task involves Python.

**To update, run `git pull && ./install.sh`.**

## Dependencies

`checks.py` needs only the standard library, so it runs with any `python3` at 3.11 or later:

```bash
python3 ~/.claude/skills/narrative/checks.py src/
python3 ~/.claude/skills/narrative/checks.py src/ --select NAR001 --select NAR009
```

The rest of the toolchain goes into a project-local environment, with the interpreter pinned.
Without `--python`, `uv` uses the first interpreter in its search order, and `mypy` then checks your
code against a different standard library.

```bash
uv venv .lintenv --python 3.11
uv pip install --python .lintenv/bin/python -r ~/.claude/skills/narrative/requirements-lock.txt
echo '.lintenv/' >> .gitignore
```

| package | version | job |
|---|---|---|
| `ruff` | 0.16.3 | formatting, imports, annotations, bugbear, quotes, banned APIs |
| `pylint` | 4.0.7 | `mixedCase` function names, which no other linter can require |
| `mypy` | 2.3.1 | type correctness under `--strict` |
| `vermin` | 1.8.0 | the Python 3.11 floor |
| `hypothesis` | 6.165.10 | property tests, which the style requires |
| `pendulum` | 3.2.0 | dates and times |
| `spacy`, `en_core_web_md` | 3.8.16, 3.8.0 | the sentence parse behind `agentverbs.py` (`NAR017`) |

Then merge `pyproject-snippet.toml` into your project's `pyproject.toml`, or copy it for a new
project. Several settings differ from the tool defaults, and `tooling.md` gives the reason for each.

```bash
cp ~/.claude/skills/narrative/pyproject-snippet.toml pyproject.toml   # new project
```

## Verify

Run `verify.py` from your project root, and not the tools one by one:

```bash
cd your-project                                          # both defaults are relative
python3 ~/.claude/skills/narrative/verify.py .           # rewrites files: runs --fix and format
python3 ~/.claude/skills/narrative/verify.py . --no-fix  # reports only, changes nothing
```

It checks every Python file below the path. It runs `ruff check --fix`, `ruff format`, `pylint`,
`mypy --strict`, `checks.py`, `vermin` and `agentverbs.py`, in that order, because that order
converges. When a tool fails, it prints that tool's output.

| exit | meaning |
|---|---|
| 0 | every tool passed |
| 1 | at least one tool reported a finding |
| 2 | the toolchain or the config is missing, so nothing was checked |

## Comments and docstrings

Comments and docstrings are written for a smart, experienced developer with the file open. Skill uses trade vocabulary when appropriate.

By default, Claude's comments tend to record the reasoning behind the code: edge cases, alternatives and spec
gaps. `SKILL.md` instead starts with a test: what information does this comment give over
the code itself? Two rules follow. The reasoning belongs in the session user messages, and a comment
that a professional reader would get from the code below it is cut.

After a passing run, `verify.py` prints every comment and docstring summary, so the agent double checks its work.

## The nineteen lint custom rules

| rule | finding |
|---|---|
| `NAR001` | module state changed with no `global`. Ruff and pylint report nothing on this at any setting |
| `NAR002` | `hasattr(self, ...)`, which means an attribute exists only on some paths |
| `NAR003` | more than three positional arguments on one `def` line |
| `NAR004` | no docstring on a complex function (more than three parameters, or a long body), or no `Raises:` on one that raises |
| `NAR005` | an annotation with more than four names below the outermost |
| `NAR006` | an assignment that shadows a module name |
| `NAR007` | `and` inside `or` without parentheses |
| `NAR009` | no module docstring, or a runnable module with no usage example |
| `NAR010` | a `FIXME` in code that runs |
| `NAR011` | a docstring body indented past the docstring's column, which `ruff format` flattens |
| `NAR012` | a decision id in a comment or docstring |
| `NAR013` | a dash or a semicolon between clauses in a comment or docstring |
| `NAR014` | `deliberately`, `on purpose`, `by design` or `intentionally` in a comment or docstring |
| `NAR015` | changelog wording in a comment or docstring: `no longer`, `previously`, `it used to` |
| `NAR016` | `holds`, `carries` and their forms in a comment or docstring |
| `NAR017` | an agent verb on a subject that cannot act: `a period ranks`, `the report names it` |
| `NAR018` | a possessive `own` in a comment or docstring |
| `NAR019` | a return contract written as a comment at the top of a function body |
| `NAR020` | a clause with its subject cut before `, so`: `Named, so a recreated container gets it back` |

`NAR000` is code for a file that could not be read or parsed.

## What is in this repository

| path | contents |
|---|---|
| `skill/` | the nine files of the skill. `architecture.md` has the multi-module rules |
| `install.sh` | the list of files in the skill, and the installer |
| `verify_docs.py` | checks that every decision id and rule code in the documents exists |
| `benchmark/decisions.jsonl` | all 433 decisions, each with its reasoning and evidence |
| `benchmark/round1/` to `round10/` | the rounds that produced the decisions. `benchmark/README.md` describes each |
| `benchmark/GAPS.md` | gaps found by writing real programs against the skill, and the rule each one became |
| `validation/` | held-out tasks, in three arms each: no guidance, the earlier style doc, the skill |
| `experiment/length/` | whether the style makes code longer: four tasks, two arms |

## Measured code effects

The style has four goals. Three of them are measurable with an agent harness.

| goal | result |
|---|---|
| 1. shorter than unguided code | **yes.** 33% fewer SLOC against an ordinary spec, 9% fewer against a detailed output contract |
| 2. more readable than unguided code | **cannot be agent measured.** (But definitely passes my human review...) |
| 3. doesn't create future tech debt | **fewer lines, more files.** A two-step change costs 329 lines against 365, over 14 files against 12. This is an acceptable null result - one of these files is `vocabulary.py` |
| 4. no worse against the spec | **yes, on twenty blind tests.** Both arms pass 20 of 20 |

The test task is a billing reconciler. In the table below, V5 names the outputs and does not specify them (aka realistic spec). V6 fixes the report schema, the ordering, the exit codes and the join to the byte,
so the remaining difference is style.

| | modules | lines | code lines | ruff | format | pylint | mypy | checks |
|---|---|---|---|---|---|---|---|---|
| V5 `base` | 12 | 1317 | 879 | 321 | FAIL | 36 | 0 | 14 |
| V5 **`full`** | 12 | **963** | **590** | **0** | **ok** | **0** | **0** | **0** |
| V6 `base` | 14 | 1380 | 831 | 93 | FAIL | 32 | 2 | 2 |
| V6 **`full`** | 14 | **1316** | **752** | **0** | **ok** | **0** | **0** | **0** |

**33% below unguided** is what the skill gives on typical specs. **9% below unguided** for unrealistically specific specs. The rest comes from the guided agent choosing a narrower report. In V5, `full`'s report has
three top-level keys and `base`'s has eight, and both are correct readings of the spec. (I would count this as a YAGNI win - not pre-emptively designing unasked features.)

**Bugs.** A conformance suite written by a blinded agent scores
both arms **20 of 20**.

**Tech debt.** Five change requests, each at a different seam, were applied to
each arm by an agent that saw only that arm and that change.

| | `base` files / lines | `full` files / lines |
|---|---|---|
| C1: a 3rd cost format | **5 / 137** | 7 / 234 |
| C5: a 4th cost format | 7 / 228 | **7 / 95** |
| **the cycle** | **12** / 365 | 14 / **329** |
| C2: a fourth finding kind, across every layer | 6 / 115 | **5 / 106** |
| C3: a new rules field | **2 / 48** | 4 / 59 |
| C4: a new column in three outputs | **5 / 90** | 6 / 92 |

At C1 the guided agent extracted a shared parser, and paid more lines for it at the time. At C5 the
unguided agent reached the same design, because the spec requires identical rejection messages
across formats. Both pay about 95 lines for a fifth format. The guided arm touches more files in
three of the five changes, the same number in one, and fewer in one. In C1, C3 and C5, some of its
files changed only to re-paste a stale docstring sample (required by rule `R9-08`).

## License

Apache-2.0. See `LICENSE`. `skill/words.json` has word lists derived from WordNet 3.0, under the
WordNet license, whose text is in the file.
