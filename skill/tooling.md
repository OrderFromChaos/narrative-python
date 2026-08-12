# Tooling — what enforces what

Every claim here was verified by running the tool against a fixture that deliberately violates the
rule. A rule you enabled is not a rule that fires.

Verified with ruff 0.16.2, pylint 4.0.7, mypy 2.3.0, Python 3.14.

## The split

| Layer | Owns |
|---|---|
| `ruff format` | all whitespace, line breaking, quote normalisation |
| `ruff check` | imports, annotations presence, bugbear, quotes, banned APIs, bare except |
| `pylint` (naming only) | `mixedCase` functions — **no other linter can require this** |
| `mypy --strict` | type correctness |
| `checks.py` | the six residual rules no tool implements |

Run order matters: `ruff check --fix`, then `ruff format`, then `pylint`, `mypy`, `checks.py`.

## The config

**`pyproject-snippet.toml` is the config.** It is not reproduced here — a second copy drifts, and
this one already had: it was missing `N806`, `lines-after-imports` and `variable-rgx`, and still
said `py313` after the floor moved to 3.10. Read the file.

What follows explains *why* each non-obvious setting is there. Every claim was checked by running
the tool against a fixture that violates the rule.

`disallow_any_explicit` is not part of `strict`, so leaving it false is the default — it is written
out in the snippet because it is a deliberate decision, not an oversight.

**`global-statement` (W0603) must stay disabled.** It was briefly enabled as an "inventory of
module-state touch points", which was a mistake: `NAR001` *requires* a `global` declaration on
mutation while W0603 *complains* about every `global`. Conformant code could never be pylint-clean,
which makes the gate unusable. Found by running the two against the same file. If you want the
inventory, `grep -rn '^\s*global '` gives it without breaking the gate.

## The one thing no tool catches at all

The `global` rule (R2b-G1) is about **mutation**, not reference — `global XYZ` is a warning sign at
the top of a function that says "this has side effects on module state". Read-only access is
exempt.

Python already enforces half of this for free: you cannot *rebind* a module name without `global`,
because omitting it silently gives you a local instead. That half is self-policing.

The other half is not enforced by anything:

```python
SAMPLE_CONFIG: dict[str, int] = {}


def loadConfig(data: dict[str, int]) -> None:
    SAMPLE_CONFIG.clear()        # module state changed
    SAMPLE_CONFIG.update(data)   # module state changed
    SAMPLE_CONFIG['x'] = 1       # module state changed
```

No `global`, no error, module state mutated. Verified that **`ruff check --select ALL` and
`pylint --enable=all` both report nothing** on this file. That gap is `NAR001`, and it is the
highest-value check in the set.

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

## Gotchas found while verifying

**`ruff format` collapses a 4-arg signature back onto one line** unless it carries a magic trailing
comma. Verified: with the trailing comma present the explosion is preserved exactly; without it the
signature is joined. So the doc's ">3 args goes multiline" rule survives only because of the
trailing comma. `COM812` is therefore *enabled*, against ruff's general advice to disable it
alongside the formatter — here it is the mechanism that makes the rule stick.

**Nothing forces the split in the first place.** A 4-arg signature written on one line under 120
columns is untouched by both `ruff check` and `ruff format`. That is `NAR003` in `checks.py`.

**`multiline-quotes = 'single'` is rejected by the formatter** — it warns and enforces double.
Set it to `'double'`. No real cost: the style avoids `"""` for data strings anyway (implicit
concatenation in parens instead, Q03), so multiline quotes only ever appear in docstrings.

**`ruff format` deletes the blank line between `class X:` and its first method**, and collapses two
blank lines between methods to one. Both were given up deliberately rather than fight the
formatter. The style is now: 2 blank lines between top-level definitions, 1 between methods, none
after the `class` statement — i.e. the formatter's defaults.

**mypy reports `import-not-found` for banned libraries** before ruff gets to say why. Read the ruff
message, not the mypy one.

**Two blank lines after the import block is an isort setting, not a formatter setting.** This one
is backwards from expectation: `ruff format` *preserves* two blank lines quite happily. It is
`ruff check`'s `I001` whose autofix deletes the second one, because isort's `lines-after-imports`
defaults to 1 before a statement. Without `lines-after-imports = 2`, `ruff check --fix` silently
undoes the rule every time. Both rewrite agents hit this independently (R3a-14).

**A constant moved inside a function needs two escapes.** Keeping `ALL_CAPS` on a function-local
constant (R3a-12) trips ruff `N806` and pylint `C0103` once per constant — 24 of each across three
files. Hence `N806` in the ignore list, and on the pylint side:

```toml
variable-rgx = '^([a-z_][a-z0-9_]*|[A-Z][A-Z0-9_]*)$'
```

Use `variable-rgx`, **not** `good-names-rgxs`: it relaxes only *locals*. Verified that a mixedCase
local, a mixedCase argument and a mixedCase attribute are all still flagged, so nothing else is
lost. Ruff stops flagging mixedCase locals once `N806` is ignored, but pylint still catches them,
so coverage survives (R3a-13).

**`SIM114`'s autofix makes code worse and is disabled.** Applied to two adjacent `elif` branches
with the same body, it produced:

```python
elif (
    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    and node is not func
    or isinstance(node, ast.ExceptHandler)
    and node.name
):
```

Semantically correct — `and` binds tighter than `or` — but the reader now has to apply operator
precedence to recover two cases that were plainly separate before. That is exactly the rote parsing
the no-diffing principle (R2b-P0) exists to eliminate.

Adding explicit parentheses fixes the readability but **loses type narrowing**, which is the
stronger objection. The loss is not universal — it needs a specific shape, and a later attempt to
reproduce it with three other constructions found nothing. It requires the merged branches to
narrow **the same attribute access to different types**: here `node.name` is `str` on an
`ast.FunctionDef` but `str | None` on an `ast.ExceptHandler`. Merged, mypy widens `node` back to a
union and the attribute with it:

```
checks.py:161: error: Argument 1 to "add" of "set" has incompatible type "str | None"; expected "str"
```

The two separate `elif` branches each narrowed `node` to one type, so `node.name` was `str`. So the
answer to "can I have merging *and* explicitness" is: only where the checker keeps its narrowing.
Here it does not, and narrowing wins (R2b-B5). `NAR007` enforces the parentheses for the cases where
merging is fine.

**`ruff format` puts one item per line in any collection literal that does not fit on one line.**
Removing the trailing comma does not prevent it — verified, both forms explode identically. The
only escape is a `# fmt: off` / `# fmt: on` fence, which is reserved for word-list-shaped literals
where packing genuinely reads better (R2b-B2).
