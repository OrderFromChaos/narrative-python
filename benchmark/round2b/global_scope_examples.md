# Doc §9 follow-up — how far does the `global` declaration rule reach?

Real code, not a snippet: these functions are lifted verbatim from
`benchmark/round3/p1_scan_ingest/a_procedural.py`, the variant written to follow your doc.

The file has 20 module-level names. **Two are rebound** (`DB_CONNECTION`, `SAMPLE_CONFIG`).
The other 18 are constants that can never change.

## Measured cost over the whole file

| | R1: declare every module name read | R2: declare only names that are rebound |
|---|---|---|
| `global` names declared | **26** | **5** |
| functions carrying a `global` line | **10 of 11** | **5 of 11** |

A third option — "exempt `ALL_CAPS` constants, declare the rest" — **does not work in this style.**
Your doc mandates `ALL_CAPS` for module-level state generally, so `DB_CONNECTION` and
`SAMPLE_CONFIG` are `ALL_CAPS` too. Casing cannot separate constant from mutable here. Dropped.

---

## Case 1 — reads one constant, rebinds nothing

```python
# R1
def logEvent(level: str, event: str, **fields: object) -> None:
    global LOG_PATH
    record: dict[str, object] = {
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
        'level': level,
        'event': event,
    }
    record.update(fields)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Reopened per record: a batch killed mid-run still leaves a complete, parseable log behind.
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')


# R2
def logEvent(level: str, event: str, **fields: object) -> None:
    record: dict[str, object] = {
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
        'level': level,
        'event': event,
    }
    record.update(fields)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Reopened per record: a batch killed mid-run still leaves a complete, parseable log behind.
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')
```

---

## Case 2 — the worst case: 8 constants, nothing rebound

```python
# R1
def parseHeader(raw: bytes) -> ScanHeader:
    global HEADER_FORMAT, HEADER_SIZE, MAGIC, REASON_BAD_MAGIC, REASON_BAD_SAMPLE_REF
    global REASON_TRUNCATED_HEADER, REASON_UNSUPPORTED_VERSION, SUPPORTED_VERSIONS
    # Rejections travel as ValueError(reason_code, detail); the batch loop reads args[0] to route the file.
    if len(raw) < HEADER_SIZE:
        raise ValueError(REASON_TRUNCATED_HEADER, f'{len(raw)} bytes, need {HEADER_SIZE}')
    magic, version, scan_id, sample_bytes, pixel_count, repetitions, checksum = struct.unpack(
        HEADER_FORMAT,
        raw[:HEADER_SIZE],
    )
    if magic != MAGIC:
        raise ValueError(REASON_BAD_MAGIC, repr(magic))
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(REASON_UNSUPPORTED_VERSION, str(version))
    ...


# R2
def parseHeader(raw: bytes) -> ScanHeader:
    # Rejections travel as ValueError(reason_code, detail); the batch loop reads args[0] to route the file.
    if len(raw) < HEADER_SIZE:
        raise ValueError(REASON_TRUNCATED_HEADER, f'{len(raw)} bytes, need {HEADER_SIZE}')
    ...
```

Note what R1 costs here beyond two lines: the declaration is a hand-maintained list that must stay
in sync with the body. Add one `raise ValueError(REASON_X, ...)` and you must remember to extend
the `global` line — and nothing enforces it, because `global` on a read-only name is a no-op to the
interpreter. It is a comment that looks like code.

---

## Case 3 — mixed: rebinds one name, reads three constants

```python
# R1
def validateHeader(header: ScanHeader, payload: bytes) -> str:
    global SAMPLE_CONFIG, REASON_CHECKSUM_MISMATCH, REASON_PIXEL_COUNT_MISMATCH
    global REASON_UNKNOWN_SAMPLE
    entry = SAMPLE_CONFIG.get(header.sample_ref)
    ...


# R2
def validateHeader(header: ScanHeader, payload: bytes) -> str:
    global SAMPLE_CONFIG
    entry = SAMPLE_CONFIG.get(header.sample_ref)
    ...
```

R2's single line now carries information: *this function touches shared mutable state.* Under R1
that signal is diluted — `SAMPLE_CONFIG` sits in a list of four names, three of which are inert.

---

## Case 4 — genuinely rebinding. Identical under both.

```python
def loadConfig(config_path: pathlib.Path) -> None:
    global SAMPLE_CONFIG
    raw = json.loads(config_path.read_text(encoding='utf-8'))
    SAMPLE_CONFIG = {ref: (int(entry['pixel_count']), str(entry['site_code'])) for ref, entry in raw.items()}
    logEvent('info', 'config_loaded', config_path=str(config_path), sample_count=len(SAMPLE_CONFIG))
```

---

## The argument for R2

Your R2b-E4 principle: *0% of the reader's mental effort on rote diffing, 100% on design.* Under R1,
10 of 11 functions open with a name list the reader must diff against the body to learn anything —
and the answer is almost always "nothing is mutated here." Under R2 the presence of a `global` line
is itself the signal, and it appears exactly 5 times, on exactly the functions that can change
shared state.

The counter-argument is locality: R1 tells you at a glance every module name a function depends on,
without scanning the body. That is real. Whether it is worth 26 declarations, 21 of which are inert
and unenforceable, is your call.
