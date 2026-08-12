# Gap 6 — ruff SIM103 versus symmetric guard clauses

Q06 prefers guard clauses and early return. `SIM103` demands the last of a run of guards become a
returned negation. `SIM114` is already disabled; `SIM103` is not mentioned anywhere.

Three whole working programs from `validation/v1_log_triage/skill.py`. All three produce
byte-identical reports (`md5sum` matched).

## V1 — what ruff demands (what exists today)

```python
def selected(entry: LogEntry, selection: Selection) -> bool:
    # Both bounds are inclusive. A record with no `duration_ms` is unaffected by either.
    if severityFor(entry.level) < severityFor(selection.min_level):
        return False
    if selection.since is not None and entry.timestamp < selection.since:
        return False
    return selection.until is None or entry.timestamp <= selection.until
```

Two guards read as rejections; the third reads as an acceptance, inverted. Three sibling conditions,
two spellings.

## V2 — symmetric guards

```python
    if severityFor(entry.level) < severityFor(selection.min_level):
        return False
    if selection.since is not None and entry.timestamp < selection.since:
        return False
    if selection.until is not None and entry.timestamp > selection.until:
        return False
    return True
```

`ruff check` reports, exactly:

```
SIM103 Return the negated condition directly
   --> c2_symmetric.py:239:5
239 | /     if selection.until is not None and entry.timestamp > selection.until:
240 | |         return False
241 | |     return True
    | |_______________^
help: Inline condition

Found 1 error.
No fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).
```

## V3 — a form that satisfies both

```python
    return all(
        (
            severityFor(entry.level) >= severityFor(selection.min_level),
            selection.since is None or entry.timestamp >= selection.since,
            selection.until is None or entry.timestamp <= selection.until,
        ),
    )
```

Three parallel positive clauses, no `if` for SIM103 to fire on. Clean everywhere. Cost: `ruff
format` will not keep `all((...))` under 8 lines and the double parenthesis is noise; and it
evaluates `severityFor` unconditionally, where V1 and V2 short-circuit.

## Measured

| | V1 ruff-satisfied | V2 symmetric | V3 `all()` |
|---|---|---|---|
| `ruff check` | clean | **SIM103, 1 error** | clean |
| `checks.py` / `pylint` / `mypy --strict` / `vermin` | clean | clean | clean |
| whole file, lines | 497 | 499 | 499 |
| function body, lines | 5 | 6 | 7 |
| spellings for 3 sibling conditions | **2** | **1** | **1** |
| short-circuits | yes | yes | **no** |
| report byte-identical | — | yes | yes |

## Does SIM103's fix misbehave the way SIM114's did? Constructed and tested.

**It is never applied by the documented command.** This is the load-bearing difference and it was
verified directly:

| | fix availability under `ruff check --fix` |
|---|---|
| `SIM114` | `[*] 1 fixable with the --fix option` — **safe, silently applied** |
| `SIM103` | `No fixes available (1 hidden fix can be enabled with --unsafe-fixes)` — **never applied** |

So SIM103 cannot silently rewrite anything. It can only fail the build. That is a different hazard
from SIM114's.

**Narrowing loss is structurally impossible for SIM103.** It rewrites only a terminal `if ...:
return <bool>` immediately followed by `return <bool>` — there is no code after it to lose narrowing.
Tested against a preceding `isinstance` guard: the fix produced `return not len(value) < 3` and left
the narrowing guard untouched; `mypy --strict` clean.

**The unsafe fix does change behaviour, in one case, and mypy catches it.** Forcing
`--unsafe-fixes` on three constructed functions:

```python
if values: return True / return False             ->  return bool(values)        # correct
if len(value) < 3: return False / return True     ->  return not len(value) < 3  # correct, ugly
if not value.strip(): return False / return True  ->  return value.strip()       # WRONG
```

The third drops the boolean wrapper. Measured at runtime:

```
usable('  '):  before=False (bool)   after='' (str)      identical=False
usable('abc'): before=True  (bool)   after='abc' (str)   identical=False
```

`mypy --strict` catches it: `error: Incompatible return value type (got "str", expected "bool")
[return-value]`. Since this style annotates every return, the toolchain closes the hole — but only
because of the annotation, and only if someone ran `--unsafe-fixes` in the first place.

On the real `selected()` the unsafe fix produces
`return not (selection.until is not None and entry.timestamp > selection.until)` — correct, mypy
clean, and a double negative over a compound condition.

**One thing I could not reproduce.** Three constructions of SIM114's documented narrowing loss
(`isinstance` merge over `re.sub`, over an overloaded call, over a plain union) were all accepted by
mypy in their merged form. The SIM114 rationale may rest on a case I did not find. It does not
affect the SIM103 conclusion, but the gap report's premise that *SIM103 has the same character as
SIM114* is **not** supported: SIM114's fix is safe and automatic, SIM103's is neither.

## Recommendation

**Disable `SIM103`, for a different reason than SIM114 was disabled.**

SIM114 was disabled because its autofix silently rewrote correct code. SIM103's autofix never runs,
so it cannot do that. SIM103 should be disabled because its *demand* is wrong for this style: it
requires the last of a run of parallel guards to be spelled differently from its siblings. That is
the rote diffing the P0 principle exists to eliminate — three sibling conditions in two spellings,
the last of which the reader must invert mentally to check it matches. Under the stated tiebreak
(*when two rules conflict, the one that spares the reader diffing wins*), Q06's symmetry wins.

Disabling it also makes V2 legal, the cheapest of the three: same short-circuiting as V1, one
spelling, no `all()` scaffolding, 6 body lines.

**The counter-argument, stated fairly.** V1 is one line shorter and already passes. `if X: return
False` followed by `return True` really is a longer way to write `return not X`, and a reviewer who
has not internalised the symmetry argument will read V2 as a missed simplification. Disabling a rule
for a stylistic preference is also a different class of decision from disabling one for a broken
autofix — the current `ignore` list contains only the latter, so SIM103 would be the first entry
justified by taste rather than a tool defect. V3 needs no config change and satisfies both, at the
price of 8 formatter-imposed lines and lost short-circuiting.

---

**Question: is `SIM103` disabled on the strength of the symmetry argument alone, given its autofix
is verified never to run under `ruff check --fix`?**
