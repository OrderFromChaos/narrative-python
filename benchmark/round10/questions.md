# Round 10 — comments

**Answer as if you had infinite time and effort.** Pick the version you would want to find in the
file a year from now, not the one you would type under deadline.

The code in every option is identical. Options differ in one respect of the comment. If two things
differ at once, say so: that is a bug in the question.

Claude wrote every comment. In batches 1 and 3, one option per question is Claude's comment
verbatim. Snippets are excerpts from longer functions, so names defined outside the excerpt exist.

Valid answers:
- a letter
- `depends`, with the condition in one line, recorded as a conditional rule
- `neither`, with your own comment, recorded verbatim

Answer format: `3 B`, `7 depends: ...`, `9 neither: # ...`. Reasons are quoted verbatim into
`decisions.jsonl` and are the most useful part of an answer.

Don't read `key.md` before answering. It lists the dimension each question tests.

---

## Batch 1

### R10-Q01

```python
# A
    CHECKSUM_MASK = 0xFFFFFFFF

    entry = SAMPLE_CONFIG.get(header.sample_ref)
    if entry is None:
        raise rejectionFor(RejectionReason.UNKNOWN_SAMPLE, header.sample_ref)
    if header.pixel_count != entry.expected_pixels:
        detail = f'header {header.pixel_count}, config {entry.expected_pixels}'
        raise rejectionFor(RejectionReason.PIXEL_COUNT_MISMATCH, detail)

# B
    CHECKSUM_MASK = 0xFFFFFFFF

    # Reads SAMPLE_CONFIG and does not change it, so no `global` here.
    entry = SAMPLE_CONFIG.get(header.sample_ref)
    if entry is None:
        raise rejectionFor(RejectionReason.UNKNOWN_SAMPLE, header.sample_ref)
    if header.pixel_count != entry.expected_pixels:
        detail = f'header {header.pixel_count}, config {entry.expected_pixels}'
        raise rejectionFor(RejectionReason.PIXEL_COUNT_MISMATCH, detail)
```

---

### R10-Q02

```python
# A
def configureLogging(verbose: bool) -> None:
    global LOG
    # Logs go to stderr as JSONL so that the report on stdout stays pipeable (Q08).
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)

# B
def configureLogging(verbose: bool) -> None:
    global LOG
    # Logs go to stderr as JSONL so that the report on stdout stays pipeable.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)
```

---

### R10-Q03

```python
# A
    for number, line in enumerate(report_path.read_text(encoding='utf-8').splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_MARKER):
            continue

        fields = line.split(FIELD_SEPARATOR)
        if len(fields) != FIELD_COUNT:
            raise rejectEntry(report_path, f'line {number}', f'expected {FIELD_COUNT} tab-separated fields')
        path_text, size_text = fields

        try:
            size_bytes = parseSizeBytes(size_text)
        except MalformedSizeError as exc:
            raise rejectEntry(report_path, f'line {number}', str(exc)) from exc
        entries.append(UsageEntry(path=Path(path_text), size_bytes=size_bytes, team=None, host=None))

# B
    for number, line in enumerate(report_path.read_text(encoding='utf-8').splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_MARKER):
            continue

        # split
        fields = line.split(FIELD_SEPARATOR)
        if len(fields) != FIELD_COUNT:
            raise rejectEntry(report_path, f'line {number}', f'expected {FIELD_COUNT} tab-separated fields')
        path_text, size_text = fields

        # size
        try:
            size_bytes = parseSizeBytes(size_text)
        except MalformedSizeError as exc:
            raise rejectEntry(report_path, f'line {number}', str(exc)) from exc
        entries.append(UsageEntry(path=Path(path_text), size_bytes=size_bytes, team=None, host=None))
```

---

### R10-Q04

```python
# A
    # Matched by text rather than parsed. The floor is 3.11 so `tomllib` is available, and this
    # tool that enforces the floor must not itself break it.
    required = (
        (r'\[tool\.ruff\]', '[tool.ruff]'),
        (r'\[tool\.ruff\.lint\]', '[tool.ruff.lint]'),
        (r'function-naming-style', '[tool.pylint.basic] function-naming-style'),
        (r'strict\s*=\s*true', '[tool.mypy] strict = true'),
    )

# B
    # Matched by text rather than parsed. The floor is now 3.11 so `tomllib` is available, and this
    # tool that enforces the floor must not itself break it.
    required = (
        (r'\[tool\.ruff\]', '[tool.ruff]'),
        (r'\[tool\.ruff\.lint\]', '[tool.ruff.lint]'),
        (r'function-naming-style', '[tool.pylint.basic] function-naming-style'),
        (r'strict\s*=\s*true', '[tool.mypy] strict = true'),
    )
```

Judge only the word `now`.

---

### R10-Q05

```python
# A
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name

    # FIXME: archive into dated subdirectories once the archive holds more than a day of scans.
    attempt = 1
    while target.exists():
        target = dest_dir / f'{source.stem}.{attempt}{source.suffix}'
        attempt += 1

# B
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name

    # TODO: archive into dated subdirectories once the archive holds more than a day of scans.
    attempt = 1
    while target.exists():
        target = dest_dir / f'{source.stem}.{attempt}{source.suffix}'
        attempt += 1
```

The function runs on every ingest.

---

### R10-Q06

```python
# A
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)  # raises ValueError on junk
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

# B
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
```

---

### R10-Q07

```python
# A
    named: dict[str, str] = {}
    for field in SCAN_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            raise rejectInventory(scan_path, f'resource {index} names no {field}')
        named[field] = value

# B
    # One loop over SCAN_FIELDS rather than four near-identical checks.
    named: dict[str, str] = {}
    for field in SCAN_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            raise rejectInventory(scan_path, f'resource {index} names no {field}')
        named[field] = value
```

---

### R10-Q08

```python
# A
        # `raises` was a trigger and is not any more. SKILL.md routes raise sites through a
        # reject*() helper, so the guards that call it all contain `raise` while being two lines
        # long -- the trigger fired hardest on the functions with the simplest contracts.
        reasons = []
        if body_lines > MAX_BODY_LINES_WITHOUT_DOCSTRING:
            reasons.append(f'{body_lines} body lines')
        if arity > MAX_ARGS_ON_ONE_LINE:
            reasons.append(f'{arity} parameters')

# B
        reasons = []
        if body_lines > MAX_BODY_LINES_WITHOUT_DOCSTRING:
            reasons.append(f'{body_lines} body lines')
        if arity > MAX_ARGS_ON_ONE_LINE:
            reasons.append(f'{arity} parameters')
```

Keep or delete as a whole.

---

### R10-Q09

```python
# A
    ruff = toolPath(lint_bin, 'ruff')
    ruff_cmd = [ruff, 'check', '--no-cache', '--output-format=concise']
    ruff_ok, ruff_out = runTool(ruff_cmd, staged)
    fmt_ok, _ = runTool([ruff, 'format', '--no-cache', '--check'], staged)

# B
    ruff = toolPath(lint_bin, 'ruff')
    # NOT `-q`: quiet suppresses the very lines this counts, so a failing file scored zero.
    ruff_cmd = [ruff, 'check', '--no-cache', '--output-format=concise']
    ruff_ok, ruff_out = runTool(ruff_cmd, staged)
    fmt_ok, _ = runTool([ruff, 'format', '--no-cache', '--check'], staged)
```

---

### R10-Q10

```python
# A
### vocabulary #########################################################################

### `executemany` takes one sequence per row and rejects a dataclass with
### `ProgrammingError: parameters are of unsupported type`, so the row shape gets a name instead.
FindingRow = tuple[str, str, str, str, str, str]

# B
### vocabulary #########################################################################

FindingRow = tuple[str, str, str, str, str, str]
```

---

### R10-Q11

```python
# A
def everyFinding(outcomes: Iterable[ManifestOutcome]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for outcome in outcomes:
        findings.extend(outcome.findings)

    return tuple(findings)

# B
def everyFinding(outcomes: Iterable[ManifestOutcome]) -> tuple[Finding, ...]:
    # Every finding hangs off the manifest it came from, so a flat view has to be built. This is the
    # one place that builds it, and both the coordinator above and the report module call it.
    findings: list[Finding] = []
    for outcome in outcomes:
        findings.extend(outcome.findings)

    return tuple(findings)
```

---

### R10-Q12

```python
# A
# A `.lock` file is what a package installer writes, so its packages came from the index that
# installer was pointed at.
_ASSUMED_SOURCE = SourceName('pypi')

# B
# A `.lock` file is what a package installer writes, so its packages came from the index that
# installer was pointed at. Change this where the fleet installs from somewhere else.
_ASSUMED_SOURCE = SourceName('pypi')
```

---

## Batch 2 - comment content

Determines which topics to include in comments. Some questions here are paraphrased from comments
Claude wrote in private projects.

All options use the English style from batch 3, provisionally:

- one-line comment: lowercase start, no period. Several lines: sentences (R10-Q26, R10-Q35)
- cause first, then the action, joined by `so` (R10-seed-10)
- articles dropped where nothing is lost (R10-seed-10). One example so far, so say if it overreaches
- contractions; imperative; no `we`; no article before an identifier; `name()` for a callable
- possessives and noun compounds over relative clauses; the general case, not one instance
- no `is what`, no `its own`, no dash, no code or abstract noun acting as an agent

R10-Q18 withdrawn: covered by R10-Q07.

### R10-Q13

```python
# A
    seen_ids: set[ResourceId] = set()
    # one day of exports per run, so seen_ids stays small
    for record in records:
        if record.resource_id in seen_ids:
            duplicates.append(record)
            continue
        seen_ids.add(record.resource_id)

# B
    seen_ids: set[ResourceId] = set()
    # TODO: bound seen_ids, grows with every id read
    for record in records:
        if record.resource_id in seen_ids:
            duplicates.append(record)
            continue
        seen_ids.add(record.resource_id)
```

---

### R10-Q14

```python
# A
def writeReports(findings_by_team: Mapping[TeamName, list[Finding]], report_dir: Path) -> None:
    # one file per team rather than one combined file, so readers don't filter by team
    for team, findings in findings_by_team.items():
        (report_dir / f'{team}.json').write_text(renderReport(findings), encoding='utf-8')

# B
def writeReports(findings_by_team: Mapping[TeamName, list[Finding]], report_dir: Path) -> None:
    # finance signs off each team's bill separately, so one file per team
    for team, findings in findings_by_team.items():
        (report_dir / f'{team}.json').write_text(renderReport(findings), encoding='utf-8')
```

---

### R10-Q15

```python
# A
    # finance signs off each team's bill separately, so one file per team
    for team, findings in findings_by_team.items():
        (report_dir / f'{team}.json').write_text(renderReport(findings), encoding='utf-8')

# B
    # Finance signs off each team's bill separately, so one file per team. Merge the files if
    # finance moves to a single sign-off.
    for team, findings in findings_by_team.items():
        (report_dir / f'{team}.json').write_text(renderReport(findings), encoding='utf-8')
```

---

### R10-Q16

```python
# A
def rollingMeanError(readings: Sequence[Reading], window: int) -> float:
    # signed, not absolute: calibration looks for bias in one direction
    recent = readings[-window:]

    return math.fsum(reading.error for reading in recent) / len(recent)

# B
def rollingMeanError(readings: Sequence[Reading], window: int) -> float:
    # Signed, not absolute: calibration looks for bias in one direction, and averaging magnitudes
    # would hide the sign and make noise look like drift.
    recent = readings[-window:]

    return math.fsum(reading.error for reading in recent) / len(recent)

# C
def rollingMeanError(readings: Sequence[Reading], window: int) -> float:
    # signed, not absolute
    recent = readings[-window:]

    return math.fsum(reading.error for reading in recent) / len(recent)
```

Judge how many steps of reason to keep.

---

### R10-Q17

```python
# A
    # Don't quote values. The driver binds parameters apart from the SQL text, so added quotes end
    # up in the stored value.
    connection.execute(
        'INSERT INTO finding (kind, resource_id, sku) VALUES (?, ?, ?)',
        (finding.kind.value, finding.resource_id, finding.sku),
    )

# B
    # don't quote values, driver handles escaping
    connection.execute(
        'INSERT INTO finding (kind, resource_id, sku) VALUES (?, ?, ?)',
        (finding.kind.value, finding.resource_id, finding.sku),
    )
```

A is exact about the mechanism. B is shorter and looser.

---

### R10-Q19

```python
# A
    # boundaries is always sorted, so bisect_left() finds the exact bucket
    index = bisect.bisect_left(boundaries, value)

    return buckets[index]

# B
    # assumes boundaries is sorted, so bisect_left() finds the exact bucket
    index = bisect.bisect_left(boundaries, value)

    return buckets[index]
```

Nothing in this function sorts `boundaries`.

---

### R10-Q20

```python
# A
    # file can change between calls, so not cached
    policy_text = policy_path.read_text(encoding='utf-8')

# B
    # file can change between calls, so deliberately not cached
    policy_text = policy_path.read_text(encoding='utf-8')
```

---

### R10-Q21

```python
# A
def _sku_mismatch(
    billed: dict[str, BillingLine],
    found: dict[str, ScannedResource],
) -> list[Finding]:
    """Find matched pairs whose skus differ.

    Exact, case-sensitive comparison. Never sets the exit code, whatever the cost.
    """

# B
def _sku_mismatch(
    billed: dict[str, BillingLine],
    found: dict[str, ScannedResource],
) -> list[Finding]:
    """Find matched pairs whose skus differ.

    Exact, case-sensitive comparison, so Compute-Std and compute-std differ. Never sets the exit
    code, whatever the cost.
    """
```

---

### R10-Q22

```python
# A
def computeFindingKey(finding: Finding) -> str:
    # SQLite treats NULLs as distinct, so a UNIQUE index over nullable columns would let a re-run
    # insert a duplicate row.
    fields: list[object] = [

# B
def computeFindingKey(finding: Finding) -> str:
    # SQLite treats NULLs as distinct, so a UNIQUE index over nullable columns would let a re-run
    # insert a duplicate row. The digest covers the NULLs, and the primary key rejects duplicates.
    fields: list[object] = [
```

---

### R10-Q23

```python
# A
        self.connection.execute(CREATE_FINDING)
        # account_id added to the schema in this change, so older tables lack it
        columns = {row[1] for row in self.connection.execute('PRAGMA table_info(finding)')}
        if 'account_id' not in columns:
            self.connection.execute(ADD_ACCOUNT_ID)

# B
        self.connection.execute(CREATE_FINDING)
        # databases written before account_id existed lack the column
        columns = {row[1] for row in self.connection.execute('PRAGMA table_info(finding)')}
        if 'account_id' not in columns:
            self.connection.execute(ADD_ACCOUNT_ID)
```

---

### R10-Q24

```python
# A
def read_row(row: dict[str, str | None], number: int, source: str) -> BillingLine:
    """Validate one record keyed by the names in COLUMNS.

    Also used by the ledger reader, so both finance formats accept and reject the same records.
    Raises ValueError naming the bad field.
    """

# B
def read_row(row: dict[str, str | None], number: int, source: str) -> BillingLine:
    """Validate one record keyed by the names in COLUMNS.

    Raises ValueError naming the bad field.
    """
```

---

## Batch 3 - comment English

Determines sentence form in comments. Options in a question differ only in wording.

### R10-Q25

```python
# A
    over: ByteCount  # the bytes above the quota, and 0 when the team is within the quota

# B
    over: ByteCount  # bytes over quota; 0 when within
```

---

### R10-Q26

```python
# A
    # Both bounds inclusive.
    selected = [entry for entry in entries if start <= entry.timestamp <= end]

# B
    # both bounds inclusive
    selected = [entry for entry in entries if start <= entry.timestamp <= end]
```

---

### R10-Q27

```python
# A
    # Amounts are in cents.
    total = sum(line.amount for line in invoice.lines)

# B
    # NOTE: amounts are in cents.
    total = sum(line.amount for line in invoice.lines)
```

---

### R10-Q28

```python
# A
    # Do not sort here: the report lists files in the order they were read.
    for path in discovered_paths:

# B
    # Don't sort here: the report lists files in the order they were read.
    for path in discovered_paths:
```

---

### R10-Q29

```python
# A
    # Retry once: the endpoint drops the first request after an idle period.
    response = postWithRetry(session, url, payload, attempts=2)

# B
    # We retry once: the endpoint drops the first request after an idle period.
    response = postWithRetry(session, url, payload, attempts=2)
```

---

### R10-Q30

```python
# A
    if settings.debug:
        # The `middleware/auto_login.py` loads a fixture user in development.
        request.user = loadFixtureUser()

# B
    if settings.debug:
        # `middleware/auto_login.py` loads a fixture user in development.
        request.user = loadFixtureUser()
```

---

### R10-Q31

```python
# A
    if settings.debug:
        # In development, sign the request in as the fixture user.
        request.user = loadFixtureUser()

# B
    if settings.debug:
        # In development, the middleware finds the fixture user and signs the request in as it.
        request.user = loadFixtureUser()

# C
    if settings.debug:
        # In development, the middleware loads the fixture user and signs the request in as it.
        request.user = loadFixtureUser()
```

---

### R10-Q32

```python
# A
        # --purge deletes the cache directory's files.
        if arguments.purge:
            purgeCache(cache_dir)

# B
        # --purge deletes the files the cache directory holds.
        if arguments.purge:
            purgeCache(cache_dir)
```

---

### R10-Q33

```python
# A
def severityFor(outcome: Outcome) -> LogLevel:
    # A rejection is a data problem someone has to look at; a duplicate is the idempotent path.
    match outcome:

# B
def severityFor(outcome: Outcome) -> LogLevel:
    # A rejection is a data problem someone has to look at. A duplicate is the idempotent path.
    match outcome:

# C
def severityFor(outcome: Outcome) -> LogLevel:
    # A rejection is a data problem someone has to look at -- a duplicate is the idempotent path.
    match outcome:
```

---

### R10-Q34

```python
# A
    IDLE_TIMEOUT_S = 30  # the vendor closes idle sockets at 60 s

# B
    # the vendor closes idle sockets at 60 s
    IDLE_TIMEOUT_S = 30
```

---

### R10-Q35

```python
# A
    # fromisoformat() rejects a trailing Z before Python 3.11.
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'

# B
    # fromisoformat rejects a trailing Z before Python 3.11.
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'

# C
    # `fromisoformat` rejects a trailing Z before Python 3.11.
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
```

---

### R10-Q36

```python
# A
    # Read-only: this tool must NEVER write to the readings it audits.
    connection = sqlite3.connect(f'file:{database_path}?mode=ro', uri=True)

# B
    # Read-only: this tool must never write to the readings it audits.
    connection = sqlite3.connect(f'file:{database_path}?mode=ro', uri=True)
```

---

### R10-Q37

```python
# A
        # Raising is not a trigger. SKILL.md routes raise sites through a reject*() helper, so the
        # guards that call it all contain `raise` while being two lines long -- a raise trigger
        # fires hardest on the functions with the simplest contracts.
        reasons = []

# B
        # `raises` was a trigger and is not any more. SKILL.md routes raise sites through a
        # reject*() helper, so the guards that call it all contain `raise` while being two lines
        # long -- the trigger fired hardest on the functions with the simplest contracts.
        reasons = []
```

Withdrawn: covered by R10-Q04 and R10-Q08.

---

### R10-Q38

```python
# A
    # The export is UTF-8.
    text = export_path.read_text(encoding='utf-8')

# B
    # The vendor documents no encoding; UTF-8 is assumed.
    text = export_path.read_text(encoding='utf-8')
```

---

### R10-Q39

```python
# A
    # A file with a malformed row is left out of the report.
    if outcome.malformed_rows:
        continue

# B
    # A malformed row costs its file a place in the report.
    if outcome.malformed_rows:
        continue
```

---

### R10-Q40

```python
# A
    # A blank line is what separates two records.
    records = text.split('\n\n')

# B
    # A blank line separates two records.
    records = text.split('\n\n')
```

---

### R10-Q41

```python
# A
    # Each worker opens its own connection.
    with sqlite3.connect(database_path) as connection:

# B
    # Each worker opens a connection.
    with sqlite3.connect(database_path) as connection:
```

`sqlite3` connections can't be shared across threads, so the difference matters here.

---

## Batch 4 - topics on neither list

Determines whether **Valid comment topics** is a closed list. Every comment below is on neither
**Valid comment topics** nor **Invalid topics** in `SKILL.md`. The comments are written in the batch
3 English.

Answer `keep` or `cut` for each. For a `keep`, name the topic, for example `42 keep: numerical
precision`.

### R10-Q42

```python
def meanError(readings: Sequence[Reading]) -> float:
    # fsum(): errors are small differences of large values, and sum() loses their low digits
    return math.fsum(reading.error for reading in readings) / len(readings)
```

---

### R10-Q43

```python
    # RFC 4180 section 2.6: a quoted field may contain line breaks
    reader = csv.reader(io.StringIO(text, newline=''))
```

---

### R10-Q44

```python
    # constant-time comparison, so response timing doesn't reveal the token
    if not hmac.compare_digest(supplied_token, expected_token):
        raise rejectRequest('bad token')
```

---

### R10-Q45

```python
    with self._lock:
        # _entries and _bytes_used change together; read both under the lock
        self._entries[key] = value
        self._bytes_used += len(value)
```

---

### R10-Q46

```python
SIZE_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)([KMGT]?)$')  # number, then an optional binary unit suffix
```

---

### R10-Q47

```python
@pytest.mark.parametrize(('error', 'expected'), [
    (1.59, Status.OK),
    (1.6, Status.OK),  # exactly the warn threshold
    (1.61, Status.WARN),
])
```

---

### R10-Q48

```python
    known_ids = set(existing_ids)  # one membership test per row, over millions of rows
    fresh = [row for row in rows if row.resource_id not in known_ids]
```

---

### R10-Q49

```python
@dataclass(frozen=True)
class BillingLine:
    resource_id: ResourceId
    region: RegionName | None  # None when the export leaves the field empty
```

---

### R10-Q50

```python
        try:
            result = plugin.run(batch)
        except Exception:  # noqa: BLE001
            # plugins are third-party code; one failing plugin must not stop the batch
            LOG.exception('plugin.failed', extra={'plugin': plugin.name})
            continue
```

---

### R10-Q51

```python
WARN_THRESHOLD = 1.6  # calibration spec CAL-7, section 3
```

---

### R10-Q52

```python
    # vendor ticket VND-412: the export ends lines with \r\n despite its documentation
    text = text.replace('\r\n', '\n')
```

---

### R10-Q53

```python
    store.migrate()
    # migrate before load: load reads the account_id column
    findings = store.load()
```

---

### R10-Q54

```python
    if not entries:
        # an empty report is a valid run with nothing to reconcile
        return Report.empty()
```

---

### R10-Q55

```python
    # walk backwards so deleting an item doesn't shift the indexes still to visit
    for index in range(len(items) - 1, -1, -1):
        if items[index].expired:
            del items[index]
```
