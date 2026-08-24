# Tooling: what enforces what

Every claim here was tested by running the tool against a fixture that breaks the rule. **Enabling a
rule does not make it fire — test it.**

Tested with ruff 0.16.3, pylint 4.0.7, mypy 2.3.1 and vermin 1.8.0, against the 3.11 floor.

## The split

| Layer | Owns |
|---|---|
| `ruff format` | all whitespace, line breaking, quote normalisation |
| `ruff check` | imports, annotations presence, bugbear, quotes, banned APIs, bare except |
| `pylint` (naming only) | `mixedCase` functions — **no other linter can require this** |
| `mypy --strict` | type correctness |
| `checks.py` | the nine residual rules no tool implements |
| `verify.py` | running all of the above correctly, with the toolchain and config guards |

Run order matters: `ruff check --fix`, then `ruff format`, then `pylint`, `mypy`, `checks.py`.
`verify.py` runs them in that order, so use it rather than reproducing the sequence.

## The config

**`pyproject-snippet.toml` is the config. Read the file rather than this section for the settings
themselves**, because a second copy of them drifts. What follows explains *why* each non-obvious
setting is there.

`disallow_any_explicit` is not part of `strict`, so a false value is the default. The snippet states
it because it is a deliberate decision, not an oversight.

**`global-statement` (W0603) must stay disabled.** `NAR001` *requires* a `global` declaration on
mutation and W0603 *complains* about every `global`, so conformant code could never be pylint-clean
and the gate would be unusable. If you want an inventory of module-state touch points,
`grep -rn '^\s*global '` gives it without breaking the gate.

## The one thing no tool catches at all

The `global` rule (R2b-G1) is about **mutation**, not reference. `global XYZ` is a warning sign at
the top of a function that says "this has side effects on module state". Read-only access is
exempt.

Python already enforces half of this for free: you cannot *rebind* a module name without `global`,
because if you omit it, Python silently gives you a local instead. That half is self-policing.

Nothing enforces the other half:

```python
SAMPLE_CONFIG: dict[str, int] = {}


def loadConfig(data: dict[str, int]) -> None:
    SAMPLE_CONFIG.clear()        # module state changed
    SAMPLE_CONFIG.update(data)   # module state changed
    SAMPLE_CONFIG['x'] = 1       # module state changed
```

No `global`, no error, module state mutated. Verified that **`ruff check --select ALL` and
`pylint --enable=all` both report the undeclared mutation nowhere.** Each tool does report other
things about the file, such as a missing docstring and a non-conforming function name. Neither
reports the mutation. That gap is `NAR001`, and it is the highest-value check in the set.

`NAR006` covers the adjacent bug: a bare `NAME = x` that shadows a module-level name creates a
local, so the module value silently never changes.

## Verified firing

| Rule | Tool | Code | Confirmed |
|---|---|---|---|
| `mixedCase` function/method names | pylint | `C0103` | flags `snake_case_function` |
| PascalCase classes | pylint | `C0103` / ruff `N801` | flags `scanSession` |
| snake_case locals and args | pylint / ruff | `C0103` / `N806` | flags `reallyLongLocal` |
| Attribute assigned outside `__init__` | pylint | `W0201` | flags `self.frame_buffer` |
| Relative imports | ruff | `TID252` | flags `from . import sibling` |
| Import grouping and order | ruff | `I001` | fires |
| Missing annotations | ruff + mypy | `ANN001/201/204`, `no-untyped-def` | both fire |
| Double quotes | ruff | `Q000` | fires |
| Bare `except:` | ruff | `E722` | fires |
| Mutable default arg | ruff | `B006` | fires |
| `pydantic` import | ruff | `TID251` | fires with the custom message |
| Trailing comma on a split construct | ruff | `COM812` | fires, autofixable |

## Gotchas

**`ruff format` collapses a 4-arg signature back onto one line** unless it carries a magic trailing
comma. With the comma the formatter keeps the explosion exactly; without it the formatter joins the
signature.

So the ">3 args goes multiline" rule in `SKILL.md` survives only because of the trailing comma.
`COM812` is therefore *enabled*, against the general ruff advice to disable it alongside the
formatter. Here `COM812` is the mechanism that makes the rule stick.

**Nothing forces the split in the first place.** Neither `ruff check` nor `ruff format` touches a
4-arg signature written on one line under 120 columns. That is `NAR003` in `checks.py`.

**The formatter rejects `multiline-quotes = 'single'`.** It warns and enforces double. Set it to
`'double'`. No real cost: the style avoids `"""` for data strings anyway (implicit concatenation in
parens instead, Q03), so multiline quotes only ever appear in docstrings.

**`ruff format` deletes the blank line between `class X:` and its first method**, and collapses two
blank lines between methods to one. Take the formatter defaults rather than fight them: 2 blank
lines between top-level definitions, 1 between methods, none after the `class` statement.

**mypy reports `import-not-found` for banned libraries** before ruff gets to say why. Read the ruff
message, not the mypy one.

**Two blank lines after the import block is an isort setting, not a formatter setting.** This one
is backwards from expectation: `ruff format` *preserves* two blank lines quite happily.

The autofix of `I001` in `ruff check` deletes the second one, because the isort setting
`lines-after-imports` defaults to 1 before a statement. Without `lines-after-imports = 2`,
`ruff check --fix` silently undoes the rule every time (R3a-14).

**A constant moved inside a function needs two escapes.** An `ALL_CAPS` name on a function-local
constant (R3a-12) trips ruff `N806` and pylint `C0103`, once per constant, which reaches double
figures in any file that follows the placement rule. Hence `N806` in the ignore list, and on the
pylint side:

```toml
variable-rgx = '^([a-z_][a-z0-9_]*|[A-Z][A-Z0-9_]*)$'
```

Use `variable-rgx`, **not** `good-names-rgxs`: it relaxes only *locals*, so pylint still flags a
mixedCase local, a mixedCase argument and a mixedCase attribute.

Ruff stops flagging mixedCase locals once the config ignores `N806`, but pylint still catches them,
so coverage survives (R3a-13).

**The `SIM114` autofix makes code worse, so the config disables it.** Applied to two adjacent
`elif` branches with the same body, it produced:

```python
elif (
    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    and node is not func
    or isinstance(node, ast.ExceptHandler)
    and node.name
):
```

The result is semantically correct, because `and` binds tighter than `or`. But the reader now has to
apply operator precedence to recover two cases that were plainly separate before, which is the rote
parsing the no-diffing principle (R2b-P0) exists to eliminate.

Explicit parentheses fix the readability and **lose type narrowing**, which is the stronger
objection. **The loss needs a specific shape: the merged branches must narrow the same attribute
access to different types.** Here `node.name` is `str` on an `ast.FunctionDef` and `str | None` on
an `ast.ExceptHandler`, so merging widens `node` back to a union and the attribute with it:

```
error: Argument 1 to "add" of "set" has incompatible type "str | None"; expected "str"
```

Two separate `elif` branches each narrow `node` to one type, so `node.name` is `str`. Merge only
where the checker keeps its narrowing; where it does not, narrowing wins (R2b-B5). `NAR007` enforces
the parentheses for the cases where merging is fine.

**`ruff format` puts one item per line in any collection literal that does not fit on one line**,
with or without a trailing comma.

The only escape is a `# fmt: off` / `# fmt: on` fence. Keep that fence for word-list-shaped
literals where packing genuinely reads better (R2b-B2).
