# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## P3 snapshot pruner: 15 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/2c45b307-8896-41d7-82f3-ba661d8eb852/scratchpad/newrules/p3`

### 1. snapshot_pruner/__main__.py:106

```python
     98     if failed:
     99         return EXIT_FAILURE
    100     if plan.problems:
    101         return EXIT_PROBLEMS
    102     return EXIT_SUCCESS
    103 
    104 
    105 def parseInstant(raw_now: str) -> DateTime:
>>  106     # pendulum.parse() returns a Duration for P1D and a naive DateTime for 2028-11-05. Reject both
    107     try:
    108         now = pendulum.parse(raw_now, tz=None)
    109     except ValueError as exc:
    110         raise argparse.ArgumentTypeError(f'not an ISO 8601 instant: {raw_now}') from exc
    111     if not isinstance(now, DateTime) or now.tzinfo is None:
    112         raise argparse.ArgumentTypeError(f'not an instant with a UTC offset: {raw_now}')
    113     return now
    114 
    115 
    116 def deleteSnapshots(snapshots: Collection[Snapshot]) -> tuple[Path, ...]:
```

### 2. snapshot_pruner/history.py:80

```python
     72         policy.monthly,
     73         applied,
     74     )
     75 
     76     try:
     77         with closing(sqlite3.connect(history_path)) as connection, connection:
     78             for statement in SCHEMA:
     79                 connection.execute(statement)
>>   80             # INSERT OR IGNORE returns no row for a repeat run
     81             run_row = connection.execute(INSERT_RUN, run_values).fetchone()
     82             if run_row is None:
     83                 return 0
     84             rows = _buildDecisionRows(plan, run_id=run_row[0])
     85             connection.executemany('INSERT INTO decisions VALUES (?, ?, ?, ?, ?)', rows)
     86             return len(rows)
     87     except sqlite3.Error as exc:
     88         _LOG.error('history.unwritable', extra={'history_path': str(history_path), 'error': str(exc)})
     89         raise HistoryError(f'{history_path}: {exc}') from exc
     90 
```

### 3. snapshot_pruner/history.py:115

```python
    107         _DecisionRow(run_id, problem.path.name, problem.kind.value, None, None) for problem in plan.problems
    108     ]
    109     return keep_rows + delete_rows + problem_rows
    110 
    111 
    112 ### vocabulary #########################################################################
    113 
    114 
>>  115 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
    116 class _DecisionRow(NamedTuple):
    117     run_id: int
    118     file: str
    119     decision: str
    120     local: str | None
    121     rules: str | None
```

### 4. snapshot_pruner/policy_file.py:58

```python
     50     if raw_timezone not in pendulum.timezones():
     51         raise _rejectPolicy(policy_path, 'unknown timezone', raw_timezone)
     52 
     53     raw_keep = document['keep']
     54     rule_names = {rule.value for rule in PeriodRule}
     55     if not isinstance(raw_keep, dict) or set(raw_keep) != rule_names:
     56         raise _rejectPolicy(policy_path, 'malformed', f'keep is not an object with the keys {sorted(rule_names)}')
     57     for rule_name, count in raw_keep.items():
>>   58         # bool subclasses int. Reject it too
     59         if isinstance(count, bool) or not isinstance(count, int) or count < 0:
     60             raise _rejectPolicy(policy_path, 'malformed', f'keep.{rule_name} is not a non-negative integer')
     61 
     62     policy = Policy(
     63         timezone=TimezoneName(raw_timezone),
     64         hourly=raw_keep[PeriodRule.HOURLY.value],
     65         daily=raw_keep[PeriodRule.DAILY.value],
     66         weekly=raw_keep[PeriodRule.WEEKLY.value],
     67         monthly=raw_keep[PeriodRule.MONTHLY.value],
     68     )
```

### 5. snapshot_pruner/retention_rules.py:48

```python
     40 
     41 def listKeepRuleNames(kept: Kept) -> tuple[str, ...]:
     42     """Name the rules a snapshot is kept under, in the order hourly, daily, weekly, monthly, newest."""
     43     newest = (_NEWEST_RULE_NAME,) if kept.newest else ()
     44     return tuple(rule.value for rule in kept.rules) + newest
     45 
     46 
     47 def _selectNewestPerPeriod(snapshots: Sequence[Snapshot], rule: PeriodRule, count: int) -> set[Snapshot]:
>>   48     # snapshots are newest first. The first snapshot seen in a period is the period's newest
     49     selected: set[Snapshot] = set()
     50     seen_periods: set[tuple[int, ...]] = set()
     51     for snapshot in snapshots:
     52         if len(seen_periods) == count:
     53             break
     54         period = _computePeriodKey(snapshot.local, rule)
     55         if period not in seen_periods:
     56             seen_periods.add(period)
     57             selected.add(snapshot)
     58     return selected
```

### 6. snapshot_pruner/retention_rules.py:64

```python
     56             seen_periods.add(period)
     57             selected.add(snapshot)
     58     return selected
     59 
     60 
     61 def _computePeriodKey(local: DateTime, rule: PeriodRule) -> tuple[int, ...]:
     62     match rule:
     63         case PeriodRule.HOURLY:
>>   64             # the key has no UTC offset. When DST ends, both copies of the repeated hour are one period
     65             return (local.year, local.month, local.day, local.hour)
     66         case PeriodRule.DAILY:
     67             return (local.year, local.month, local.day)
     68         case PeriodRule.WEEKLY:
     69             # 2029-12-31 is in ISO week 1 of 2030. Pair the week with the ISO year
     70             iso_date = local.isocalendar()
     71             return (iso_date.year, iso_date.week)
     72         case PeriodRule.MONTHLY:
     73             return (local.year, local.month)
     74 
```

### 7. snapshot_pruner/retention_rules.py:69

```python
     61 def _computePeriodKey(local: DateTime, rule: PeriodRule) -> tuple[int, ...]:
     62     match rule:
     63         case PeriodRule.HOURLY:
     64             # the key has no UTC offset. When DST ends, both copies of the repeated hour are one period
     65             return (local.year, local.month, local.day, local.hour)
     66         case PeriodRule.DAILY:
     67             return (local.year, local.month, local.day)
     68         case PeriodRule.WEEKLY:
>>   69             # 2029-12-31 is in ISO week 1 of 2030. Pair the week with the ISO year
     70             iso_date = local.isocalendar()
     71             return (iso_date.year, iso_date.week)
     72         case PeriodRule.MONTHLY:
     73             return (local.year, local.month)
     74 
     75 
     76 def _lookUpKeepCount(policy: Policy, rule: PeriodRule) -> int:
     77     match rule:
     78         case PeriodRule.HOURLY:
     79             return policy.hourly
```

### 8. snapshot_pruner/snapshot_listing.py:53

```python
     45         entries = sorted(snapshot_dir.iterdir())
     46     except OSError as exc:
     47         raise _rejectSnapshotDir(snapshot_dir, str(exc.strerror)) from exc
     48 
     49     snapshots: list[Snapshot] = []
     50     problems: list[Problem] = []
     51     for entry in entries:
     52         name_match = _SNAPSHOT_NAME.fullmatch(entry.name)
>>   53         # is_file() follows symbolic links. Check is_symlink() too
     54         if name_match is None or entry.is_symlink() or not entry.is_file():
     55             _LOG.debug('snapshot_dir.skipped', extra={'file': entry.name})
     56             continue
     57 
     58         instant = _parseInstant(name_match)
     59         if instant is None:
     60             _LOG.debug('snapshot.unparseable', extra={'file': entry.name})
     61             problems.append(Problem(entry, ProblemKind.UNPARSEABLE))
     62         elif instant > now:
     63             _LOG.debug('snapshot.future', extra={'file': entry.name})
```

### 9. snapshot_pruner/snapshot_listing.py:68

```python
     60             _LOG.debug('snapshot.unparseable', extra={'file': entry.name})
     61             problems.append(Problem(entry, ProblemKind.UNPARSEABLE))
     62         elif instant > now:
     63             _LOG.debug('snapshot.future', extra={'file': entry.name})
     64             problems.append(Problem(entry, ProblemKind.FUTURE))
     65         else:
     66             snapshots.append(Snapshot(entry, instant.in_timezone(timezone)))
     67 
>>   68     # Datetimes that share a tzinfo compare by wall clock. The two 01:30 at the end of DST compare
>>   69     # equal. Sort by timestamp().
     70     newest_first = sorted(snapshots, key=lambda snapshot: snapshot.local.timestamp(), reverse=True)
     71     return Inventory(snapshots=tuple(newest_first), problems=tuple(problems))
     72 
     73 
     74 def _rejectSnapshotDir(snapshot_dir: Path, reason: str) -> SnapshotDirError:
     75     _LOG.error('snapshot_dir.rejected', extra={'snapshot_dir': str(snapshot_dir), 'reason': reason})
     76     return SnapshotDirError(f'{snapshot_dir}: {reason}')
     77 
     78 
     79 def _parseInstant(name_match: re.Match[str]) -> DateTime | None:
```

### 10. snapshot_pruner/vocabulary.py:40

```python
     32     daily: int
     33     weekly: int
     34     monthly: int
     35 
     36 
     37 @dataclass(frozen=True)
     38 class Snapshot:
     39     path: Path
>>   40     local: DateTime  # the instant in the policy's timezone
     41 
     42 
     43 @dataclass(frozen=True)
     44 class Problem:
     45     path: Path
     46     kind: ProblemKind
     47 
     48 
     49 @dataclass(frozen=True)
     50 class Inventory:
```

### 11. snapshot_pruner/vocabulary.py:51

```python
     43 @dataclass(frozen=True)
     44 class Problem:
     45     path: Path
     46     kind: ProblemKind
     47 
     48 
     49 @dataclass(frozen=True)
     50 class Inventory:
>>   51     snapshots: tuple[Snapshot, ...]  # newest first
     52     problems: tuple[Problem, ...]  # sorted by file name
     53 
     54 
     55 @dataclass(frozen=True)
     56 class Kept:
     57     snapshot: Snapshot
     58     rules: tuple[PeriodRule, ...]
     59     newest: bool
     60 
     61 
```

### 12. snapshot_pruner/vocabulary.py:52

```python
     44 class Problem:
     45     path: Path
     46     kind: ProblemKind
     47 
     48 
     49 @dataclass(frozen=True)
     50 class Inventory:
     51     snapshots: tuple[Snapshot, ...]  # newest first
>>   52     problems: tuple[Problem, ...]  # sorted by file name
     53 
     54 
     55 @dataclass(frozen=True)
     56 class Kept:
     57     snapshot: Snapshot
     58     rules: tuple[PeriodRule, ...]
     59     newest: bool
     60 
     61 
     62 @dataclass(frozen=True)
```

### 13. snapshot_pruner/vocabulary.py:64

```python
     56 class Kept:
     57     snapshot: Snapshot
     58     rules: tuple[PeriodRule, ...]
     59     newest: bool
     60 
     61 
     62 @dataclass(frozen=True)
     63 class Retention:
>>   64     keep: tuple[Kept, ...]  # newest first
     65     delete: tuple[Snapshot, ...]  # newest first
     66 
     67 
     68 @dataclass(frozen=True)
     69 class Plan:
     70     """The decision on every snapshot in a directory as of one instant.
     71 
     72     Entries of keep and delete are newest first. Entries of problems are sorted by file name.
     73     """
     74 
```

### 14. snapshot_pruner/vocabulary.py:65

```python
     57     snapshot: Snapshot
     58     rules: tuple[PeriodRule, ...]
     59     newest: bool
     60 
     61 
     62 @dataclass(frozen=True)
     63 class Retention:
     64     keep: tuple[Kept, ...]  # newest first
>>   65     delete: tuple[Snapshot, ...]  # newest first
     66 
     67 
     68 @dataclass(frozen=True)
     69 class Plan:
     70     """The decision on every snapshot in a directory as of one instant.
     71 
     72     Entries of keep and delete are newest first. Entries of problems are sorted by file name.
     73     """
     74 
     75     now: DateTime
```

### 15. tests/test_pruner.py:24

```python
     16 from snapshot_pruner import planPrune
     17 from snapshot_pruner.retention_rules import judgeSnapshots
     18 from snapshot_pruner.vocabulary import Policy, ProblemKind, Snapshot, TimezoneName
     19 
     20 
     21 FIXTURE_DIR = Path(__file__).resolve().parent.parent / 'fixture'
     22 FIXTURE_NOW = pendulum.datetime(2028, 11, 5, 8, 0, 0, tz='UTC')
     23 TIMEZONE = TimezoneName('America/New_York')
>>   24 # the range spans the DST changes of 2028-03-12 and 2028-11-05 in America/New_York
     25 FIRST_INSTANT_S = int(pendulum.datetime(2028, 1, 1, tz='UTC').timestamp())
     26 LAST_INSTANT_S = int(pendulum.datetime(2029, 1, 1, tz='UTC').timestamp())
     27 
     28 instants = st.lists(st.integers(FIRST_INSTANT_S, LAST_INSTANT_S), unique=True, max_size=60)
     29 keep_counts = st.integers(0, 5)
     30 
     31 
     32 @given(instants, keep_counts, keep_counts, keep_counts, keep_counts)
     33 def testEverySnapshotIsKeptOrDeletedOnce(
     34     timestamps: list[int],
```

## P5 config auditor: 7 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/2c45b307-8896-41d7-82f3-ba661d8eb852/scratchpad/newrules/p5`

### 16. config_audit/checks.py:86

```python
     78     for key, value in table.items():
     79         path = prefix.appendKey(key)
     80         yield path, value
     81         if isinstance(value, Mapping):
     82             yield from _walkKeys(value, path)
     83 
     84 
     85 def _validPercentage(value: TomlValue | None) -> TypeGuard[int]:
>>   86     # bool subclasses Python int. Reject it too
     87     return isinstance(value, int) and not isinstance(value, bool) and PERCENT_MIN <= value <= PERCENT_MAX
     88 
     89 
     90 def _describeBadPercentage(value: TomlValue | None) -> str:
     91     if value is None:
     92         return 'missing'
     93     value_type = classifyTomlType(value)
     94     if value_type is TomlType.INTEGER:
     95         return f'{value} is outside {PERCENT_MIN} to {PERCENT_MAX}'
     96     return f'a {value_type.value}, not an integer'
```

### 17. config_audit/inputs.py:142

```python
    134     return {key: _convertValue(raw_value) for key, raw_value in raw_table.items()}
    135 
    136 
    137 def _convertValue(raw_value: object) -> TomlValue:
    138     if isinstance(raw_value, dict):
    139         return _convertTable(raw_value)
    140     if isinstance(raw_value, list):
    141         return tuple(_convertValue(item) for item in raw_value)
>>  142     # pendulum.instance() sets UTC on a value with no offset. tz=None leaves TOML local times without one
    143     if isinstance(raw_value, (datetime, date, time)):
    144         return pendulum.instance(raw_value, tz=None)
    145     if isinstance(raw_value, (str, int, float)):
    146         return raw_value
    147     # no other value type is in tomllib's conversion table
    148     raise TypeError(f'tomllib returned a {type(raw_value).__name__}')
```

### 18. config_audit/inputs.py:147

```python
    139         return _convertTable(raw_value)
    140     if isinstance(raw_value, list):
    141         return tuple(_convertValue(item) for item in raw_value)
    142     # pendulum.instance() sets UTC on a value with no offset. tz=None leaves TOML local times without one
    143     if isinstance(raw_value, (datetime, date, time)):
    144         return pendulum.instance(raw_value, tz=None)
    145     if isinstance(raw_value, (str, int, float)):
    146         return raw_value
>>  147     # no other value type is in tomllib's conversion table
    148     raise TypeError(f'tomllib returned a {type(raw_value).__name__}')
```

### 19. config_audit/merge.py:38

```python
     30 
     31 
     32 ### vocabulary #########################################################################
     33 
     34 
     35 class _LayerMerger:
     36     def __init__(self) -> None:
     37         self.config: dict[str, TomlValue] = {}
>>   38         # the last layer to set each key, or to set a key below it
     39         self.origins: dict[KeyPath, LayerName] = {}
     40         self.type_changes: list[Finding] = []
     41 
     42     def mergeTable(
     43         self,
     44         target: dict[str, TomlValue],
     45         layer_table: TomlTable,
     46         prefix: KeyPath,
     47         layer: LayerName,
     48     ) -> None:
```

### 20. config_audit/toml_types.py:11

```python
      3 from __future__ import annotations
      4 
      5 from pendulum import Date, DateTime, Time
      6 
      7 from config_audit.vocabulary import TomlType, TomlValue
      8 
      9 
     10 def classifyTomlType(value: TomlValue) -> TomlType:
>>   11     # bool subclasses Python int. Test it first
     12     if isinstance(value, bool):
     13         return TomlType.BOOLEAN
     14     if isinstance(value, int):
     15         return TomlType.INTEGER
     16     if isinstance(value, float):
     17         return TomlType.FLOAT
     18     if isinstance(value, str):
     19         return TomlType.STRING
     20     # pendulum DateTime subclasses Date. Test it first
     21     if isinstance(value, DateTime):
```

### 21. config_audit/toml_types.py:20

```python
     12     if isinstance(value, bool):
     13         return TomlType.BOOLEAN
     14     if isinstance(value, int):
     15         return TomlType.INTEGER
     16     if isinstance(value, float):
     17         return TomlType.FLOAT
     18     if isinstance(value, str):
     19         return TomlType.STRING
>>   20     # pendulum DateTime subclasses Date. Test it first
     21     if isinstance(value, DateTime):
     22         return TomlType.DATETIME
     23     if isinstance(value, Date):
     24         return TomlType.DATE
     25     if isinstance(value, Time):
     26         return TomlType.TIME
     27     if isinstance(value, tuple):
     28         return TomlType.ARRAY
     29     return TomlType.TABLE
```

### 22. config_audit/vocabulary.py:74

```python
     66 class KeyPath:
     67     keys: tuple[str, ...]
     68 
     69     def appendKey(self, key: str) -> KeyPath:
     70         return KeyPath((*self.keys, key))
     71 
     72     def __str__(self) -> str:
     73         BARE_KEY = re.compile(r'[A-Za-z0-9_-]+')
>>   74         # a TOML key with characters outside A-Za-z0-9_- is written in quotes
     75         return '.'.join(key if BARE_KEY.fullmatch(key) else json.dumps(key, ensure_ascii=False) for key in self.keys)
     76 
     77 
     78 @dataclass(frozen=True, order=True)
     79 class Version:
     80     major: int
     81     minor: int
     82     patch: int
     83 
     84     def __str__(self) -> str:
```

## P8 cache server: 13 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/2c45b307-8896-41d7-82f3-ba661d8eb852/scratchpad/newrules/p8`

### 23. memcache_server/cache.py:44

```python
     36 LOG = logging.getLogger(__name__)
     37 
     38 
     39 class Cache:
     40     def __init__(self, max_bytes: int) -> None:
     41         self.max_bytes = max_bytes
     42         self.used_bytes = 0
     43         self.last_cas_unique = 0
>>   44         self.items: OrderedDict[CacheKey, Item] = OrderedDict()  # least recently used first
>>   45         # a heapq heap. dropExpired() skips an entry of a replaced or removed item
     46         self.expiries: list[_Expiry] = []
     47 
     48     def store(self, command: StorageCommand, data: bytes) -> StoreOutcome:
     49         if self.tooLarge(command.key, len(data)):
     50             return StoreOutcome.TOO_LARGE
     51         refusal = _computeRefusal(command, self.liveItem(command.key))
     52         if refusal is not None:
     53             return refusal
     54         deadline = _computeDeadline(command.exptime)
     55         if _expired(deadline):
```

### 24. memcache_server/cache.py:110

```python
    102         self.makeRoom(size)
    103         self.items[key] = item
    104         self.used_bytes += size
    105         if item.deadline is None:
    106             return
    107 
    108         MAX_EXPIRIES_PER_ITEM = 2
    109         heapq.heappush(self.expiries, _Expiry(item.deadline, item.cas_unique, key))
>>  110         # rebuild from the live items once stale entries outnumber them
    111         if len(self.expiries) > MAX_EXPIRIES_PER_ITEM * len(self.items):
    112             self.expiries = [
    113                 _Expiry(live.deadline, live.cas_unique, live_key)
    114                 for live_key, live in self.items.items()
    115                 if live.deadline is not None
    116             ]
    117             heapq.heapify(self.expiries)
    118 
    119     def makeRoom(self, size: int) -> None:
    120         if self.used_bytes + size <= self.max_bytes:
```

### 25. memcache_server/cache.py:123

```python
    115                 if live.deadline is not None
    116             ]
    117             heapq.heapify(self.expiries)
    118 
    119     def makeRoom(self, size: int) -> None:
    120         if self.used_bytes + size <= self.max_bytes:
    121             return
    122         self.dropExpired()
>>  123         # store() and applyDelta() reject an item over max_bytes. The cache is never empty at popitem()
    124         while self.used_bytes + size > self.max_bytes:
    125             key, item = self.items.popitem(last=False)
    126             evicted_size = _computeItemSize(key, len(item.data))
    127             self.used_bytes -= evicted_size
    128             LOG.info('cache.evicted', extra={'key': key.decode('ascii', 'backslashreplace'), 'size': evicted_size})
    129 
    130     def dropExpired(self) -> None:
    131         while self.expiries and _expired(self.expiries[0].deadline):
    132             expiry = heapq.heappop(self.expiries)
    133             item = self.items.get(expiry.key)
```

### 26. memcache_server/cache.py:173

```python
    165     return Deadline(time.monotonic() + exptime - time.time())
    166 
    167 
    168 def _expired(deadline: Deadline | None) -> bool:
    169     return deadline is not None and deadline <= time.monotonic()
    170 
    171 
    172 def _numeric(data: bytes) -> bool:
>>  173     # int() raises ValueError past 4,300 digits. Check the length first
    174     return data.isdigit() and len(data) <= MAX_COUNTER_DIGITS and int(data) < COUNTER_MODULUS
    175 
    176 
    177 def _computeCounterValue(value: int, amount: int, direction: Direction) -> int:
    178     match direction:
    179         case Direction.INCR:
    180             return (value + amount) % COUNTER_MODULUS
    181         case Direction.DECR:
    182             return max(value - amount, 0)
    183 
```

### 27. memcache_server/protocol.py:135

```python
    127     if len(raw_key) > MAX_KEY_BYTES:
    128         raise _rejectCommand('key too long')
    129     if any(byte in CONTROL_BYTES for byte in raw_key):
    130         raise _rejectCommand('key contains a control character')
    131     return CacheKey(raw_key)
    132 
    133 
    134 def _parseUnsigned(token: bytes, limit: int, field_name: str) -> int:
>>  135     # bytes.isdigit() is true for ASCII digits only
    136     if not token.isdigit() or int(token) >= limit:
    137         raise _rejectCommand(f'bad {field_name}')
    138     return int(token)
    139 
    140 
    141 def _parseExptime(token: bytes) -> int:
    142     magnitude = token.removeprefix(b'-')
    143     if not magnitude.isdigit() or int(magnitude) >= INT64_LIMIT:
    144         raise _rejectCommand('bad exptime')
    145     return int(token)
```

### 28. memcache_server/server.py:57

```python
     49         listener = await asyncio.start_server(functools.partial(_acceptClient, cache, client_tasks), HOST, port)
     50     except OSError as exc:
     51         LOG.error('server.listen_failed', extra={'host': HOST, 'port': port, 'error': exc.strerror})
     52         raise ListenError(exc.strerror) from exc
     53     LOG.info('server.listening', extra={'host': HOST, 'port': port, 'max_bytes': cache.max_bytes})
     54 
     55     await stop.wait()
     56     listener.close()
>>   57     # wait_closed() waits for open client connections since Python 3.12.1. Cancel the clients first
     58     for task in client_tasks:
     59         task.cancel()
     60     await asyncio.gather(*client_tasks, return_exceptions=True)
     61     await listener.wait_closed()
     62     LOG.info('server.stopped')
     63 
     64 
     65 def _acceptClient(
     66     cache: Cache,
     67     client_tasks: set[asyncio.Task[None]],
```

### 29. memcache_server/server.py:148

```python
    140         case ArithmeticCommand():
    141             return _executeArithmetic(cache, command)
    142         case QuitCommand():
    143             return None
    144 
    145 
    146 async def _executeStorage(cache: Cache, command: StorageCommand, reader: asyncio.StreamReader) -> bytes:
    147     if cache.tooLarge(command.key, command.byte_count):
>>  148         # the announced byte count is unbounded. Discard the block in chunks
    149         await _discardBytes(reader, command.byte_count)
    150         data = None
    151     else:
    152         data = await reader.readexactly(command.byte_count)
    153     if await _skipPastLineEnd(reader) > 0:
    154         return b'CLIENT_ERROR bad data chunk\r\n'
    155 
    156     outcome = StoreOutcome.TOO_LARGE if data is None else cache.store(command, data)
    157     reply = outcome.value + b'\r\n'
    158     match outcome:
```

### 30. memcache_server/server.py:210

```python
    202     Returns:
    203         The number of bytes before the `\\r\\n`. 0 means a well-formed end of data block.
    204     """
    205     skipped = 0
    206     while True:
    207         try:
    208             line = await reader.readuntil(b'\r\n')
    209         except asyncio.LimitOverrunError as exc:
>>  210             # readuntil() leaves an over-limit line in the buffer. Drop exc.consumed bytes of it and retry
    211             await reader.readexactly(exc.consumed)
    212             skipped += exc.consumed
    213             continue
    214         return skipped + len(line) - 2
    215 
    216 
    217 def _applyNoreply(reply: bytes, noreply: bool) -> bytes:
    218     # under noreply, a normal reply is dropped. An error reply is sent anyway
    219     return b'' if noreply else reply
```

### 31. memcache_server/server.py:218

```python
    210             # readuntil() leaves an over-limit line in the buffer. Drop exc.consumed bytes of it and retry
    211             await reader.readexactly(exc.consumed)
    212             skipped += exc.consumed
    213             continue
    214         return skipped + len(line) - 2
    215 
    216 
    217 def _applyNoreply(reply: bytes, noreply: bool) -> bytes:
>>  218     # under noreply, a normal reply is dropped. An error reply is sent anyway
    219     return b'' if noreply else reply
```

### 32. memcache_server/vocabulary.py:12

```python
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from typing import NewType
      8 
      9 
     10 CacheKey = NewType('CacheKey', bytes)
     11 CasUnique = NewType('CasUnique', int)
>>   12 Deadline = NewType('Deadline', float)  # a time.monotonic() reading
     13 
     14 
     15 class StoreMode(Enum):
     16     SET = 'set'
     17     ADD = 'add'
     18     REPLACE = 'replace'
     19     CAS = 'cas'
     20 
     21 
     22 class Direction(Enum):
```

### 33. memcache_server/vocabulary.py:48

```python
     40 
     41 @dataclass(frozen=True)
     42 class StorageCommand:
     43     mode: StoreMode
     44     key: CacheKey
     45     flags: int
     46     exptime: int
     47     byte_count: int
>>   48     cas_unique: CasUnique | None  # None unless mode is CAS
     49     noreply: bool
     50 
     51 
     52 @dataclass(frozen=True)
     53 class RetrievalCommand:
     54     keys: tuple[CacheKey, ...]
     55     with_cas: bool
     56 
     57 
     58 @dataclass(frozen=True)
```

### 34. memcache_server/vocabulary.py:85

```python
     77 Command = StorageCommand | RetrievalCommand | DeleteCommand | ArithmeticCommand | QuitCommand
     78 
     79 
     80 @dataclass(frozen=True)
     81 class Item:
     82     flags: int
     83     data: bytes
     84     cas_unique: CasUnique
>>   85     deadline: Deadline | None  # None when the item never expires
     86 
     87 
     88 class UnknownCommandError(RuntimeError):
     89     pass
     90 
     91 
     92 class MalformedCommandError(RuntimeError):
     93     pass
     94 
     95 
```

### 35. replay_fixture.py:111

```python
    103     for step in steps:
    104         if step.sent:
    105             connection.sendall(step.text.encode() + b'\r\n')
    106             continue
    107         try:
    108             raw_reply = reply_stream.readline()
    109         except TimeoutError:
    110             mismatches.append(f'line {step.number}: expected {step.text!r}, got no reply')
>>  111             # after a timeout, every read from a socket file object raises OSError
    112             return mismatches
    113         reply = raw_reply.removesuffix(b'\r\n').decode(errors='backslashreplace')
    114         if not raw_reply.endswith(b'\r\n') or not matchingReply(reply, step.text):
    115             mismatches.append(f'line {step.number}: expected {step.text!r}, got {raw_reply!r}')
    116 
    117     try:
    118         trailing = reply_stream.read()
    119     except TimeoutError:
    120         mismatches.append('server kept the connection open after the session ended')
    121         return mismatches
```
