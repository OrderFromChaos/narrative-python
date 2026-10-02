# Proposed rules from the payroll review (R10-rating8)

Six proposals. Each shows the wording, where it goes, and the comments it comes from. Reply with the
numbers you approve and any edits.

## 1. Raw and parsed names

**Where:** `SKILL.md`, naming rules.

> **Raw and parsed forms get different names.** Prefix the raw form with `raw_`: `raw_at: str` from
> the file, `at: DateTime` once parsed. Never `at` beside `parsed.at`.

**From:** comment 5, where the raw `at` and the parsed `parsed.at` shared a name.

## 2. Paths are `Path`

**Where:** `SKILL.md`, types.

> **A file path is a `Path`** from the boundary inward. A `str` path only where an outside API
> requires one, or for an argument echoed exactly as typed, named `raw_…`: `raw_input_dir`.

**From:** comments 1, 16 and 17, where file names were `str`.

## 3. Money as integer cents

**Where:** `SKILL.md`, types.

> **Money is integer cents**, named `…_cents`: parse to `int` at the input, format at the output.
> A computation that yields fractions of a cent, such as rate × minutes × multiplier, stays in
> integers or `Fraction` and rounds once, with the rounding mode explicit. No `float` or `Decimal`
> arithmetic on amounts.

**From:** comment 4.

## 4. pendulum for time

**Where:** `SKILL.md`, types; `requirements-lock.txt`.

> **Dates and times use `pendulum`**, unless the repository already builds on `datetime`.

Also pins pendulum in `requirements-lock.txt`. The lint environment runs `mypy --strict`, which fails
on an import it cannot resolve; hypothesis is pinned there for the same reason.

**From:** comments 14 and 18.

## 5. uv

**Where:** `tooling.md`.

> **uv** manages environments and packages: `uv venv`, `uv add`, `uv run`. Not pip or virtualenv
> directly.

**From:** your note. `verify.py` already prints `uv` commands when the toolchain is missing.

## 6. Lint check `NAR016`: container verbs

**Where:** `checks.py`, and the lint paragraph in `SKILL.md`, **Comments**.

**Flags:** `carry`, `carries`, `carried`, `carrying`, `hold`, `holds`, `held`, `holding` in comments
and docstrings.

**Message:** `container verb in a comment or docstring -- state the fact without making the subject
hold or carry it`

**Evidence:**

| source | comments | hits | sense |
|---|---|---|---|
| round 10 Claude corpus | 478 records | 103 | nearly all the container sense: `the format carries a cost`, `a file holds a whole number of bytes` |
| CPython stdlib | 12,969 | 22 | all literal: `the lock was held`, `[5] holds` |

A literal use is silenced with `# noqa: NAR016`.

**From:** comments 18 and 19 (`always carries a UTC offset`, `when the line carried no string
badge`), written although the agent-verb rule already names `carries`.
