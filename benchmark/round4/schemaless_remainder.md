# Gap 4 — a dataclass with a genuinely schemaless remainder

Real code from `validation/v1_log_triage/skill.py`. Three whole working programs, each run over the
same fixture, each report reloaded and diffed against the input. All three are clean under
`ruff check`, `ruff format --check`, `pylint`, `mypy --strict`, `checks.py` and `vermin -t=3.10`.

## The three `LogEntry` forms and their gate

```python
# V1 — flattened to a JSON string (what exists today)
class LogEntry:                                     class LogEntry:          # V2 — one mapping
    timestamp: datetime                                 timestamp: datetime
    level: LogLevel                                     level: LogLevel
    event: EventName                                    event: EventName
    duration: Milliseconds | None                       extra: Mapping[str, object]
    detail: str                                         source: Path
    source: Path                                        line: int
    line: int

# V3 — typed subset + remainder
class LogEntry:
    timestamp: datetime
    level: LogLevel
    event: EventName
    duration: Milliseconds | None      # the one extra field the program computes on
    extra: Mapping[str, object]        # everything else, verbatim
    source: Path
    line: int
```

The gate differs in one line: V1 writes
`detail=json.dumps(extra, sort_keys=True) if extra else ''`, V3 writes `extra=extra`.

## Measured

| | V1 flat string | V2 one mapping | V3 typed + remainder |
|---|---|---|---|
| whole file, lines | **497** | **508** (+11) | **500** (+3) |
| extras round-tripped through the report | 20/20 | 20/20 | 20/20 |
| extra `json.loads` calls a consumer needs | **6** | 0 | 0 |
| extras addressable in the report (`jq`) | **no** — `.detail` is a string | `.extra.batch` | `.extra.batch` |
| `checks.py` NAR005 findings | 0 | **0** | **0** |
| `mypy --strict`, naive `entry.extra['user_id']` | error | error | error |
| lines to make that read type-check | **10** | **6** | **6** |
| passes through `Any` | **yes** (`json.loads`) | no | no |
| `hash(entry)` | works | **TypeError** | **TypeError** |

**Q02 is not violated by V2 or V3.** `decisions.jsonl` records Q02's options verbatim as
`["dict of parsed fields", "frozen dataclass"]`, choice `frozen dataclass`. The choice was about
what holds the *record*. In all three variants `LogEntry` is still a frozen dataclass; V2 and V3
differ only in the type of one field.

**NAR005 is not violated either.** `Mapping[str, object]` is depth 1. Probed directly: NAR005 fires
first at depth 3 (`dict[str, dict[str, list[int]]]`). Nothing here is close.

## What each costs downstream

Downstream wants the distinct `user_id`s. Naive, under `mypy --strict`, all three fail:

```
V1: error: Invalid index type "str" for "str"; expected type "SupportsIndex | slice[...]"  [index]
V2: error: Set comprehension has incompatible type Set[object]; expected Set[str]  [misc]
V3: error: Set comprehension has incompatible type Set[object]; expected Set[str]  [misc]
```

Making them pass is where they diverge:

```python
# V1 — 10 lines, and every guarantee ends at `json.loads`
    for entry in entries:
        if not entry.detail:
            continue
        decoded = json.loads(entry.detail)   # -> Any (mypy: Revealed type is "Any")
        if isinstance(decoded, dict):
            user = decoded.get('user_id')
            if isinstance(user, str):
                users.add(user)

# V2 / V3 — 6 lines, no Any anywhere
    for entry in entries:
        user = entry.extra.get('user_id')
        if isinstance(user, str):
            users.add(user)
```

The second principle in the style — *prefer what the type checker and IDE can follow* — is measured
on exactly this axis. V1 launders every extra field through `Any`. V2 and V3 keep them at `object`,
which is checkable.

## Two traps found while measuring, both real

**Splatting the remainder destroys the report's own provenance.** Writing `**entry.extra` into the
entry's JSON object looks natural and is wrong. A log line carrying `"source": "upstream-kafka",
"line": 42` overwrote the report's record of which file and line the entry came from — verified,
both fields clobbered. `'extra': dict(entry.extra)` is required. V1 is immune by construction; this
is a cost V2 and V3 carry and must be written down.

**`frozen=True` plus a mapping field is no longer hashable.** `hash(entry)` raises
`TypeError: unhashable type: 'dict'` in V2 and V3, and works in V1. The program does not hash
`LogEntry` today, so all three run — but `set(entries)` or `Counter(entries)` would fail at runtime
with no linter warning. The frozen dataclass silently stops honouring the contract `frozen=True`
implies.

## Where V2 loses to V3

V2 has no typed `duration`. `buildReport` must re-narrow it out of `extra` with an `isinstance`
check even though the gate already proved it was a number — the proof does not survive the field's
type. That, plus two small helpers to format it, is the whole +11 lines. V3 costs +3 and keeps the
proof.

## Recommendation

**V3.** Promote the fields the program computes on to typed attributes; put the genuinely
schemaless remainder in one `Mapping[str, object]` field. It costs 3 lines over the status quo,
removes `Any` from the downstream path, keeps the extras addressable in the JSON report, and
violates neither Q02 nor NAR005 as those rules are actually written.

**The counter-argument, stated fairly.** V1 is the only variant where the report's JSON schema is
fixed and flat — every entry has the same seven keys, so the report is a stable table. V2 and V3
make the report's shape depend on its input, which is exactly what a schema is for. V1 also stays
hashable and cannot suffer the key-collision trap. If the report is consumed by something that
expects a fixed schema, V1's string is a feature, not a loss — and the measurement above shows it
loses no *values*, only direct addressability.

---

**Question: does a `Mapping[str, object]` field inside a frozen dataclass satisfy Q02, or does Q02
forbid a dict-typed field as well as a dict-typed record?**
