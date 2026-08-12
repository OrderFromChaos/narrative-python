# R2-09 follow-up — when does a block become its own function?

You said the real criterion is a judgement call: whether you might want it separately later, plus
whether extracting makes the code more readable. That is not yet a rule. These four cases are
chosen to sit on different sides of it. For each: **extract or leave inline?**

---

## E1 — a 6-line block used once, with an obvious name

```python
def ingestFile(path: Path) -> Outcome:
    raw = path.read_bytes()

    # Recompute the checksum over the payload and compare against the header
    payload = raw[HEADER_BYTES:]
    computed = 0
    for offset in range(0, len(payload), 4):
        computed = (computed + int.from_bytes(payload[offset:offset + 4], 'little')) & 0xFFFFFFFF
    if computed != header.checksum:
        return Outcome.QUARANTINED

    ...
```

vs.

```python
def computeChecksum(payload: bytes) -> int:
    total = 0
    for offset in range(0, len(payload), 4):
        total = (total + int.from_bytes(payload[offset:offset + 4], 'little')) & 0xFFFFFFFF
    return total


def ingestFile(path: Path) -> Outcome:
    raw = path.read_bytes()
    if computeChecksum(raw[HEADER_BYTES:]) != header.checksum:
        return Outcome.QUARANTINED
    ...
```

*The extracted version is pure, trivially testable, and the name is not a restatement of the steps.
But it is called exactly once and adds a level of indirection to reading `ingestFile`.*

---

## E2 — a 3-line block used once, name restates the code

```python
def openDatabase(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute(CREATE_SCANS_TABLE_SQL)
    return conn
```

vs.

```python
def applyPragmas(conn: sqlite3.Connection) -> None:
    conn.execute('PRAGMA journal_mode=WAL')


def createSchema(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_SCANS_TABLE_SQL)


def openDatabase(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    applyPragmas(conn)
    createSchema(conn)
    return conn
```

*This is the shape one reviewer called "LLM residue" — one-line helpers called once. Is it?*

---

## E3 — a 40-line block that does one nameable thing but needs 5 locals from its caller

```python
def ingestDirectory(input_dir: Path) -> int:
    conn = openDatabase(input_dir / 'scans.db')
    config = loadConfig(input_dir / 'sites.json')
    archive_dir = input_dir / 'archive'
    quarantine_dir = input_dir / 'quarantine'
    outcomes: list[Outcome] = []

    # --- 40 lines: iterate, parse, validate, insert, move, tally ---
    for path in sorted(input_dir.glob('*.scan')):
        ...

    return 1 if any(o is Outcome.QUARANTINED for o in outcomes) else 0
```

Extracting the loop body means either a 6-parameter function, or bundling
`conn`/`config`/`archive_dir`/`quarantine_dir` into a context object, or a class.

*Does the parameter-passing cost change the answer? If bundling is the price of extraction, is
bundling itself justified?*

---

## E4 — duplicated twice, but the two copies are drifting

```python
# in ingestFile()
site = CONFIG.get(header.sample_ref)
if site is None:
    logEvent('unknown_sample_ref', sample_ref=header.sample_ref)
    return Outcome.QUARANTINED

# in revalidateArchived() — same three lines, but logs a different event name
site = CONFIG.get(header.sample_ref)
if site is None:
    logEvent('revalidate_unknown_ref', sample_ref=header.sample_ref)
    return Outcome.QUARANTINED
```

*Your doc says DRY, with a caveat for when deduplication makes things harder to understand.
Extracting means passing the event name in as a parameter. Is that still DRY, or is it a shared
function with a knob, which is worse than two honest copies?*
