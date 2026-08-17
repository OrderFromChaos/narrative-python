# NAR008 vs. a data literal and the line that consumes it

Real code. Each variant is the whole of `writeRecord` inside a runnable 84–96 line program that counts
event names and writes a JSONL report. All seven ran on the same 5,000-line fixture and emit
**byte-identical output** (770 bytes, 5 records). Toolchain is `verify.py --no-fix` against
`pyproject-snippet.toml`; only the `checks.py` column ever differs, so this is decided on layout, not
lint. Signatures appear as written — four positional args, one per line (NAR003).

## The pair under dispute

```python
# V1 -- NAR008 as mandated. `ruff format` explodes the literal; the blank line is then required.
    record = {
        'event': name,
        'count': count,
        'share': round(count / total, 4),
        'unit': UNIT,
        'schema': SCHEMA,
        'producer': 'writeRecord',
        'stability': STABILITY,
    }

    line = json.dumps(record, sort_keys=True)
    handle.write(line + '\n')
    return len(line) + 1

# V2 -- identical, blank deleted. checks.py says, exactly:
#   v2_grouped.py:83: NAR008 9-line statement is followed immediately by another
#     -- no blank line after a statement spanning 3+ lines
```

## Four refactors, and which actually dissolve it

```python
# V3a -- buildRecord() helper. The literal becomes a `return`, last in its block, and NAR008 fires
#        only on a statement FOLLOWED by another. Silent by construction, not by shortening.
    line = json.dumps(buildRecord(name, count, total), sort_keys=True)
    handle.write(line + '\n')
    return len(line) + 1


def buildRecord(name: str, count: int, total: int) -> dict[str, object]:
    return {'event': name, ...}           # still 9 lines after ruff format

# V3b -- frozen dataclass. Four constant fields become defaults, so CONSTRUCTION is one line.
    record = EventRecord(name, count, round(count / total, 4))
    line = json.dumps(asdict(record), sort_keys=True)

@dataclass(frozen=True)
class EventRecord:
    event: str
    count: int
    share: float
    unit: str = UNIT
    schema: str = SCHEMA
    producer: str = 'writeRecord'
    stability: str = STABILITY

# V3c -- inline the literal into the call that consumes it. DOES NOT WORK.
    line = json.dumps({...}, sort_keys=True)     # 12 lines, still followed by handle.write
#   v3c_inline.py:86: NAR008 12-line statement is followed immediately by another

# V5 -- the `# fmt: off` fence the style already allows for word-list literals (R2b-B2).
    # fmt: off
    record = {'event': name, 'count': count, 'share': round(count / total, 4), 'unit': UNIT,
              'schema': SCHEMA, 'producer': 'writeRecord', 'stability': STABILITY}
    # fmt: on
    line = json.dumps(record, sort_keys=True)
```

## Measured

| | V1 blank | V2 grouped | V3a helper | V3b dataclass | V3c inline | V5 fmt:off | V6 noqa |
|---|---|---|---|---|---|---|---|
| whole file, lines | 90 | **89** | 92 | 96 | 91 | **84** | 89 |
| defs below `main`, lines | 30 | 29 | 30 | 29 | 31 | **24** | 29 |
| ruff / pylint / mypy / vermin | pass | pass | pass | pass | pass | pass | pass |
| `checks.py` | clean | **NAR008** | clean | clean | **NAR008** | clean | clean |
| output vs V1 | — | identical | identical | identical | identical | identical | identical |

`asdict()` is not free: 200,000 records on 3.10.18 cost **2.75 µs/record** as a dict literal against
**9.82 µs** through `EventRecord` + `asdict` — **3.58×**. Irrelevant for a 5-line report, material on a
hot path.

## R4-05's framing: extends, but by accident

"No equivalent refactor here" is **refuted twice** — V3a and V3b both pass and neither is contrived.
But neither works the way R4-05 worked. R4-05 *shortened* the statement. V3a does not: the literal is
still nine lines, merely moved where NAR008 structurally cannot see it. V3b is the only variant that
genuinely shortens it, by moving four of seven fields into field defaults — honest only if they are
constant per record, costing the most lines (96) and 3.58× per record.

The escape is **positional, not structural**: the same nine-line literal is legal as a `return` and
illegal as an assignment. NAR008's exemption surface, not the code's shape, decides whether the tension
appears.

## The narrowed rule, and whether it is safe

In a copy of `checks.py` (`checks_nar008.py`, itself passing the full toolchain): `consumesBinding(first,
second)` exempts the pair when `second` loads a name `first` bound. `boundNames` covers `Assign`,
`AnnAssign`, `AugAssign`, `with ... as`, `for ... in`. 25 lines.

| | round3 + experiment (10 files) | all 26 conformant repo files |
|---|---|---|
| findings, current rule | 0 | 0 |
| findings, narrowed rule | **0** | **0** |
| pairs where first spans 3+ lines | 426 | 1,217 |
| of those, currently blank-separated | 364 | 987 |
| blanks the narrowing makes optional | 21 | **43 (4%)** |

**No finding count changes**, and the narrowing only ever removes a finding, so it cannot break a
conformant file. Of the 43, 28 precede a simple statement and 15 a compound one. The simple ones are
the disputed case verbatim, already in the reference implementations — 11 build-then-consume sites:

```
a_procedural.py:407  record.update(fields)                    after a 5-line `record = {...}`   x5
narrative.py:409     return json.dumps(payload, default=str)  after a multi-line payload dict   x4
a_procedural.py:310  return header, raw[HEADER_SIZE:]         after a 7-line ScanHeader(...)    x2
```

Two of the 43 are a `def` after a module constant — unreachable, because `ruff format` inserts two
blank lines before a top-level `def` (verified), so NAR008 never owned that case.

The 15 compound ones are the over-reach. `a_procedural.py:292`: a 4-line `struct.unpack` binds seven
names, followed by a deliberately grouped pair of guards that read them. The blank there is right; the
narrowed rule stops *requiring* it, and still permits it.

## Recommendation

Narrow it. Zero findings change across 26 files, and it closes the gap that makes the rule arbitrary.
V2 becomes the mandated form; V5 stays available for the packed case.

Counter-argument, stated fairly: the reference implementations hit this exact shape **eleven times** and
paid the blank line every time without complaint — real evidence the rule is not painful. And the
narrowing is loose: any second statement mentioning any bound name qualifies, including a 20-line `for`
loop that merely iterates the thing. A tighter test (second statement is simple, and its only free name
is one the first bound) covers all eleven real cases and none of the fifteen compound ones. Not
implemented, because the loose version already measures clean — which is weaker evidence than it looks,
since the corpus has zero NAR008 findings to move.

**Question: is NAR008 a rule about statement length, or about which statements share a thought? If the
second, the implementation measures a proxy, and `consumesBinding` patches the proxy rather than
replacing it.**
