# R2-08 follow-up — an `Enum` that has to be ordered

Real code, not a snippet: each variant is `validation/v1_log_triage/skill.py` edited in place. All
four run on 3.10.18, produce byte-identical reports (`100 lines scanned, 60 kept` at
`--min-level WARNING`), and expose the same `--min-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`.

The constraint stack: `Literal` and `StrEnum` banned (R2-08), `case _` banned (Q18), and R2-10 bars
a module-level constant whose *value* names an Enum member — which kills `LEVEL_ORDER = (...)` in
the constant block at the top of the file.

## V1 — exhaustive match (what exists), 13 lines

```python
def severityFor(level: LogLevel) -> int:
    match level:
        case LogLevel.DEBUG:
            return logging.DEBUG
        ...
        case LogLevel.CRITICAL:
            return logging.CRITICAL
        # No `case _`: a new member then fails mypy with "Missing return statement" (Q18).

# call site
    if severityFor(entry.level) < severityFor(selection.min_level):
```

## V2 — `IntEnum`, 0 lines of ordering machinery

```python
class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    ...
    CRITICAL = logging.CRITICAL

# call site
    if entry.level < selection.min_level:
```

`severityFor` disappears. But `.value` is now `20`, not `'INFO'`, so **three boundaries have to
change from `.value` to `.name`**: the argparse `choices=`/`default=`, the lookup in `levelFrom`,
and the JSON writer in `entryAsJson`. Miss the third and the report silently changes shape.

## V3 — a mapping, placed where R2-10 permits it: 9 lines

R2-10 is an *ordering* rule, not a placement rule. It only forbids naming a member before the class
exists. Immediately after the class, inside `### vocabulary`, is legal — and is the **only** legal
module-level home, since the top-of-file constant block runs first.

```python
### vocabulary #########################################################################
class LogLevel(Enum):
    DEBUG = 'DEBUG'
    ...

# Legal only here: R2-10 forbids a module-level value that names an Enum member before the Enum
# exists, so this cannot join the constant block at the top of the file.
SEVERITY_BY_LEVEL = {
    LogLevel.DEBUG: logging.DEBUG,
    ...
}

# call site -- no dispatch function at all
    if SEVERITY_BY_LEVEL[entry.level] < SEVERITY_BY_LEVEL[selection.min_level]:
```

V3b, for completeness: the same dict moved *inside* `severityFor` as a function-local `ALL_CAPS`
constant (R3a-12, `N806` already ignored). It is legal and it is the worst option — see the table.

## Measured

| | V1 match | V2 IntEnum | V3 mapping | V3b local dict |
|---|---|---|---|---|
| ordering machinery, lines | 13 | **0** | 9 | 11 |
| whole file, lines | 497 | **482** | 493 | 495 |
| other sites that must change | 0 | **3** (`.value`→`.name`) | 0 | 0 |
| ruff / format / pylint / mypy / vermin | pass | pass | pass | pass |
| `checks.py` | 0 | 0 | 0 | **NAR008** (line 252) |
| **add `TRACE`, don't handle it → mypy** | **`error: Missing return statement [return]`** (b1_match_plus.py:242) | clean | clean | clean |
| ...and at runtime | `TypeError: '<' not supported between 'int' and 'NoneType'` | **correct output** | `KeyError: <LogLevel.TRACE>` | `KeyError: <LogLevel.TRACE>` |
| per comparison (3.12, best of 7 × 10⁶) | 141.7 ns | **13.2 ns** | 119.8 ns | 904.4 ns |
| 200k-record run, best of 5 | 1289 ms | 1245 ms | 1262 ms | — |
| 200k-record run, spread across 5 | 1289–1361 | 1245–1335 | 1262–1318 | — |

Three things that table settles:

1. **Only V1 fails the type checker**, and it fails with the exact message Q18 promises. V3 and V3b
   type-check clean and blow up at runtime on the first record — the failure moves from `mypy` to
   production. That is the whole reason the `match` exists and the mapping does not replace it.
2. **V2 has nothing to forget.** `TRACE = 5` and the program is correct. It is not that mypy misses
   an error; there is no error to miss. This is a different answer from V3's.
3. **The performance argument in GAPS is wrong.** The mapping is 15% faster per comparison than the
   `match` (119.8 vs 141.7 ns) — not the order of magnitude "a function call per comparison"
   implies, because the dict lookup still pays `Enum.__hash__`. End to end on 200k records the gap
   between all three is smaller than the run-to-run spread of any one of them. There is no
   performance case here at any size this tool sees. V3b, the "obvious" cheap placement, is **6.4×
   slower** than V1 because it rebuilds the dict per call.

## Is `IntEnum` compatible with R2-08?

**It was never asked about.** R2-08 says "`Enum`, not `Literal`, not `StrEnum`" and cites nothing
about `IntEnum`. Do not read it as settled either way. What is measurable:

- `IntEnum` is 3.4+, so the 3.10 floor is fine — `vermin -t=3.10` reports 3.10 on the IntEnum file.
- It has **exactly the character StrEnum was rejected for**, one type down. `LogLevel.INFO == 20` is
  `True`. `json.dumps({'level': LogLevel.INFO})` emits `{"level": 20}` silently; under `Enum` the
  same call raises `TypeError: Object of type LogLevel is not JSON serializable`. R2-08's
  "`.value` at serialisation boundaries" exists so the boundary is *visible*; `IntEnum` removes the
  error that enforces it.
- Text rendering is not stable across the supported range: on **3.10** `str(LogLevel.INFO)` is
  `'LogLevel.INFO'` but `f'{LogLevel.INFO}'` is `'20'`; on 3.12 both are `'20'`. Verified on both.
  A log line or report column built with an f-string changes meaning when the interpreter moves.

## Recommendation

Keep V1. It is the only variant where adding a member is caught before it ships, it costs 13 lines
once, and the cost it was accused of is unmeasurable. If the ordering is wanted at more than one
call site, V3's placement rule is worth writing down anyway — *a constant whose value names an Enum
member is legal in `### vocabulary` after that Enum, and nowhere else* — because right now agents
read R2-10 as a flat ban and contort around it.

Counter-argument, stated fairly: V2 is 15 lines shorter, has no dispatch function to read, and is
the representation the domain actually has — syslog severities *are* ordered integers, and modelling
them as opaque names plus a translation table is a fiction the code then has to maintain. Against
that: three boundary edits, a silently-serialisable member, and version-dependent `str()`.

**Question: does R2-08 extend to `IntEnum` — and if not, does the exhaustive `match` survive once
you accept that `IntEnum` has nothing to forget rather than merely failing to catch it?**
