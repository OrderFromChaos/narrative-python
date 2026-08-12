# Gap 5 — NAR008 versus deliberately grouped guards

R3a-01 says deliberately grouped short guards stay grouped. NAR008 forces a blank line after any
statement spanning 3+ lines. Q23 says log at the raise site *and* the handle site — which makes
every guard 3 lines. `selectionFrom` is the real collision.

Three whole working programs, lifted from `validation/v1_log_triage/skill.py`. All three produce
byte-identical reports (`md5sum` matched) and byte-identical log output on both rejection paths.

## V1 — NAR008 as-is (what exists today)

```python
def selectionFrom(since: str | None, until: str | None, min_level: str) -> Selection:
    # The one gate where the raw CLI strings become the frozen object every later stage consults.
    start = parseTimestamp(since) if since else None
    end = parseTimestamp(until) if until else None
    level = levelFrom(min_level)

    if level is None:
        LOG.debug('selection_rejected', extra={'reason': 'unknown level', 'value': min_level})
        raise TriageError(f'unknown minimum level: {min_level}')

    if start is not None and end is not None and start > end:
        LOG.debug('selection_rejected', extra={'reason': 'inverted window'})
        raise TriageError(f'--since {start.isoformat()} is after --until {end.isoformat()}')

    return Selection(start, end, level)
```

## V2 — guards kept grouped, as R3a-01 asks

```python
    if level is None:
        LOG.debug('selection_rejected', extra={'reason': 'unknown level', 'value': min_level})
        raise TriageError(f'unknown minimum level: {min_level}')
    if start is not None and end is not None and start > end:
        LOG.debug('selection_rejected', extra={'reason': 'inverted window'})
        raise TriageError(f'--since {start.isoformat()} is after --until {end.isoformat()}')
```

`python3 checks.py b2_grouped.py` reports, exactly:

```
b2_grouped.py:89: NAR008 3-line statement is followed immediately by another -- no blank line after a statement spanning 3+ lines

1 findings over 1 files (0.20 per 100 lines)
```

Note what NAR008's own docstring in `checks.py` claims:

> The rule is deliberately conservative — it fires only after a statement of three or more lines,
> so deliberately grouped one- and two-line guards stay grouped.

That reasoning holds only while a guard is two lines. Q23 makes it three. The conservatism was
calibrated against `if ...: raise`, and log-then-raise moved the code past the threshold.

## V3 — log-and-return-the-exception, so each guard is 2 lines again

```python
    if level is None:
        raise rejectSelection('unknown level', f'unknown minimum level: {min_level}')
    if start is not None and end is not None and start > end:
        raise rejectSelection('inverted window', f'--since {start.isoformat()} is after --until {end.isoformat()}')

    return Selection(start, end, level)


def rejectSelection(reason: str, message: str) -> TriageError:
    # Mirrors `rejectLine`: one place logs the generic fact, and the handler in `main` logs what
    # it meant there (Q23).
    LOG.debug('selection_rejected', extra={'reason': reason})
    return TriageError(message)
```

This is not an invented pattern. `rejectLine` already exists in the same file, doing exactly this
for `parseRecord`'s six raise sites — it is already the house idiom, applied everywhere except
here.

## Measured

| | V1 blank lines | V2 grouped | V3 helper |
|---|---|---|---|
| `checks.py` NAR008 findings | **0** | **1** (line 89) | **0** |
| guards visually grouped (R3a-01) | **no** | yes | **yes** |
| whole file, lines | 497 | 496 | 501 (+4) |
| guard block, lines | 7 | 6 | **4** |
| `ruff` / `ruff format` / `pylint` / `mypy --strict` / `vermin` | clean | clean | clean |
| report byte-identical | — | yes | yes |
| log output byte-identical | — | yes | yes |

V3 is the only variant where both rules are satisfied at once. It costs 4 lines at the module level
and *removes* 3 from the function.

## Recommendation

**The rules do not actually collide — V3 dissolves the conflict, and the codebase already knew
how.** Neither rule needs to yield. The collision is an artefact of inlining `LOG.debug` at the
raise site; the moment logging moves into a `reject*()` helper that returns the exception, guards
are 2 lines, they group, NAR008 is silent, and Q23 is still honoured (the helper logs the generic
fact, `main`'s handler logs what it meant).

This also answers gap 1 from the same report: log-and-return-the-exception is not merely
*acceptable*, it is what keeps R3a-01 and NAR008 compatible. The skill should say so.

**The counter-argument, stated fairly.** V3 adds a second one-purpose helper to a file that already
has `rejectLine`, and the style warns that *a one-line helper called once is residue* (R2b-E2).
`rejectSelection` is called twice, so it clears that bar — but only just, and a file with four
`reject*` helpers would be worse than four blank lines. There is also a real cost: the raise site no
longer shows what gets logged. A reader of `selectionFrom` must jump to `rejectSelection` to learn
that the rejection is recorded at DEBUG. V1 puts that on screen.

If V3 is rejected, then a rule must yield, and the evidence favours **NAR008 yielding to R3a-01**:
NAR008 exists to separate logically self-contained blocks, and two validity checks on the same
object are one block by construction. NAR008 would need an exemption for consecutive `if`
statements whose bodies end in `raise` or `return`.

---

**Question: should log-then-raise guards be refactored into a `reject*()` helper (V3), or should
NAR008 gain an exemption for consecutive guard statements ending in `raise`?**
