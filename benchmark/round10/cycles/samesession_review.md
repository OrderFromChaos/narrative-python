# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. Only comments added or changed by the cleanup are listed (text absent from the phase-1 file). The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## old skill, snapprune: 6 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/d4835795-a251-427c-9a15-2017f1fa2ff7/scratchpad/samesession/p3_old/snapprune`

### 1. ledger.py:104

```python
     96 
     97 
     98 class _RunKey(NamedTuple):
     99     now: str
    100     snapshot_dir: str
    101     policy: str
    102 
    103 
>>  104 # executemany() would reject a dataclass row: parameters are of unsupported type
    105 class _DecisionRow(NamedTuple):
    106     now: str
    107     snapshot_dir: str
    108     policy: str
    109     file: str
    110     decision: str
    111     rules: str | None
    112     local: str | None
    113     deleted: int
    114     recorded_at: str
```

### 2. planner.py:93

```python
     85         problems=tuple(problems),
     86         non_snapshots=listing.non_snapshots,
     87     )
     88     return plan
     89 
     90 
     91 def _parseInstant(raw_now: str) -> DateTime:
     92     try:
>>   93         # without tz=None, pendulum reads an instant with no offset as UTC
     94         parsed = pendulum.parse(raw_now, tz=None)
     95     except ValueError as exc:
     96         raise _rejectPlanInput('now is not ISO 8601', raw_now) from exc
     97     if not isinstance(parsed, DateTime):
     98         raise _rejectPlanInput('now is not an instant', raw_now)
     99     if parsed.tzinfo is None:
    100         raise _rejectPlanInput('now has no UTC offset', raw_now)
    101     return parsed.in_timezone('UTC')
    102 
    103 
```

### 3. planner.py:122

```python
    114     except OSError as exc:
    115         raise _rejectPlanInput(f'snapshot directory cannot be listed: {exc}', str(snapshot_dir)) from exc
    116 
    117     snapshots: list[_Snapshot] = []
    118     unparseable: list[str] = []
    119     non_snapshots: list[str] = []
    120     for entry in entries:
    121         name_match = _SNAPSHOT_NAME.fullmatch(entry.name)
>>  122         # is_file() alone would admit a symbolic link, and links are never snapshots
    123         if name_match is None or entry.is_symlink() or not entry.is_file():
    124             non_snapshots.append(entry.name)
    125             continue
    126 
    127         try:
    128             instant = pendulum.from_format(name_match.group(1), 'YYYYMMDD[T]HHmmss', tz='UTC')
    129         except ValueError:
    130             unparseable.append(entry.name)
    131             continue
    132         snapshots.append(_Snapshot(entry.name, instant))
```

### 4. planner.py:154

```python
    146                 periods_seen.add(period)
    147                 rules_by_file[snapshot.file_name].append(rule)
    148     return {file_name: tuple(rules) for file_name, rules in rules_by_file.items()}
    149 
    150 
    151 def _computePeriodKey(local: DateTime, rule: PeriodRule) -> tuple[int, ...]:
    152     match rule:
    153         case PeriodRule.HOURLY:
>>  154             # start_of('hour') would split an hour repeated at a DST change into two periods
    155             return (local.year, local.month, local.day, local.hour)
    156         case PeriodRule.DAILY:
    157             return (local.year, local.month, local.day)
    158         case PeriodRule.WEEKLY:
    159             iso_date = local.isocalendar()
    160             return (iso_date.year, iso_date.week)
    161         case PeriodRule.MONTHLY:
    162             return (local.year, local.month)
    163 
    164 
```

### 5. policy.py:51

```python
     43         raise _rejectPolicy(policy_path, f'not JSON: {exc}') from exc
     44 
     45     if not isinstance(raw_policy, dict) or set(raw_policy) != {'timezone', 'keep'}:
     46         raise _rejectPolicy(policy_path, "top level must have the keys 'timezone' and 'keep' and no others")
     47     raw_timezone = raw_policy['timezone']
     48     if not isinstance(raw_timezone, str):
     49         raise _rejectPolicy(policy_path, 'timezone is not a string')
     50     try:
>>   51         # catching InvalidTimezone alone would let a malformed name such as '../x' crash the run
     52         timezone = pendulum.timezone(raw_timezone)
     53     except ValueError as exc:
     54         raise _rejectPolicy(policy_path, f'unknown timezone {raw_timezone!r}') from exc
     55 
     56     raw_keep = raw_policy['keep']
     57     rule_names = {rule.value for rule in PeriodRule}
     58     if not isinstance(raw_keep, dict) or set(raw_keep) != rule_names:
     59         raise _rejectPolicy(policy_path, f'keep must have the keys {sorted(rule_names)} and no others')
     60     for rule_name, count in raw_keep.items():
     61         # without the bool test, JSON true passes as 1
```

### 6. policy.py:61

```python
     53     except ValueError as exc:
     54         raise _rejectPolicy(policy_path, f'unknown timezone {raw_timezone!r}') from exc
     55 
     56     raw_keep = raw_policy['keep']
     57     rule_names = {rule.value for rule in PeriodRule}
     58     if not isinstance(raw_keep, dict) or set(raw_keep) != rule_names:
     59         raise _rejectPolicy(policy_path, f'keep must have the keys {sorted(rule_names)} and no others')
     60     for rule_name, count in raw_keep.items():
>>   61         # without the bool test, JSON true passes as 1
     62         if isinstance(count, bool) or not isinstance(count, int) or count < 0:
     63             raise _rejectPolicy(policy_path, f'keep.{rule_name} is not a non-negative integer')
     64 
     65     return Policy(
     66         timezone=timezone,
     67         hourly=raw_keep['hourly'],
     68         daily=raw_keep['daily'],
     69         weekly=raw_keep['weekly'],
     70         monthly=raw_keep['monthly'],
     71     )
```

## old skill, layeraudit: 7 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/d4835795-a251-427c-9a15-2017f1fa2ff7/scratchpad/samesession/p5_old/layeraudit`

### 7. checks.py:29

```python
     21                 Finding(FindingKind.SECRET, path, layer_name, f'non-empty string value set in {layer_name}'),
     22             )
     23     findings.extend(_checkFlags(merged))
     24     findings.extend(_checkExperiments(merged))
     25     return findings
     26 
     27 
     28 def _walkKeys(table: TomlTable, *, prefix: str) -> Iterator[tuple[KeyPath, str, object]]:
>>   29     # a key inside an array of tables has no dotted path, so arrays are not entered
     30     for key, value in table.items():
     31         path = KeyPath(f'{prefix}{key}')
     32         yield path, key, value
     33         if isinstance(value, dict):
     34             yield from _walkKeys(value, prefix=f'{path}.')
     35 
     36 
     37 def _buildDeprecationFinding(path: KeyPath, merged: MergedEnvironment, inputs: AuditInputs) -> Finding:
     38     deprecated_key = inputs.deprecated_keys[path]
     39     removed_in = deprecated_key.removed_in.text
```

### 8. checks.py:78

```python
     70 
     71 
     72 def _buildRolloutFinding(path: KeyPath, merged: MergedEnvironment, detail: str) -> Finding:
     73     return Finding(FindingKind.BAD_ROLLOUT, path, merged.last_layer_by_path[path], detail)
     74 
     75 
     76 def _describeBadPercentage(value: object) -> str | None:
     77     """Return why value is not an integer from 0 to 100, or None when it is one."""
>>   78     # without the bool test, TOML true passes as the integer 1
     79     if isinstance(value, bool) or not isinstance(value, int):
     80         return f'is a {identifyTomlType(value).value} ({value!r}), not an integer'
     81     if not 0 <= value <= 100:
     82         return f'{value} is outside 0..100'
     83     return None
     84 
     85 
     86 def _checkExperiments(merged: MergedEnvironment) -> list[Finding]:
     87     experiments = merged.config.get('experiments')
     88     if experiments is None:
```

### 9. inputs.py:83

```python
     75     except tomllib.TOMLDecodeError as error:
     76         raise _rejectInput(str(toml_path), f'invalid TOML: {error}') from error
     77     except OSError as error:
     78         raise _rejectInput(str(toml_path), f'cannot read: {error}') from error
     79     return {key: _convertDates(value) for key, value in document.items()}
     80 
     81 
     82 def _convertDates(value: object) -> object:
>>   83     # datetime.date() would also match a datetime, so the datetime case comes first
     84     match value:
     85         case datetime.datetime():
     86             return pendulum.instance(value, tz=None)
     87         case datetime.date():
     88             return pendulum.Date(value.year, value.month, value.day)
     89         case datetime.time():
     90             return pendulum.Time(value.hour, value.minute, value.second, value.microsecond)
     91         case list():
     92             return [_convertDates(item) for item in value]
     93         case dict():
```

### 10. inputs.py:128

```python
    120         for layer_name in raw_layer_names:
    121             if _unusableAsFileName(layer_name):
    122                 raise _rejectInput('layers.toml', f'environments.{name} has an invalid layer name {layer_name!r}')
    123         environments[EnvironmentName(name)] = tuple(LayerName(layer_name) for layer_name in raw_layer_names)
    124     return environments
    125 
    126 
    127 def _unusableAsFileName(layer_name: str) -> bool:
>>  128     # without these tests, a layer name such as '../x' would read a file outside the input directory
    129     return not layer_name or '/' in layer_name or '\\' in layer_name or layer_name.startswith('.')
    130 
    131 
    132 def _parseDeprecatedKeys(deprecated_document: TomlTable) -> dict[KeyPath, DeprecatedKey]:
    133     entries = deprecated_document.get('key', [])
    134     if not isinstance(entries, list):
    135         raise _rejectInput('deprecated.toml', 'key must be an array of tables')
    136     deprecated_keys: dict[KeyPath, DeprecatedKey] = {}
    137     for index, entry in enumerate(entries):
    138         source = f'deprecated.toml: key[{index}]'
```

### 11. merging.py:55

```python
     47                     continue
     48                 earlier_type, new_type = identifyTomlType(earlier), identifyTomlType(value)
     49                 if earlier_type != new_type:
     50                     detail = (
     51                         f'{earlier_type.value} in {self.last_layer_by_path[path]}, {new_type.value} in {layer_name}'
     52                     )
     53                     self.findings.append(Finding(FindingKind.TYPE_CHANGE, path, layer_name, detail))
     54 
>>   55             # without the copy, a later merge into this table would write into the layer, which later environments read
     56             target[key] = copy.deepcopy(value)
     57             self.recordLastLayer(value, path, layer_name)
     58 
     59     def recordLastLayer(self, value: object, path: KeyPath, layer_name: LayerName) -> None:
     60         self.last_layer_by_path[path] = layer_name
     61         if isinstance(value, dict):
     62             for key, child in value.items():
     63                 self.recordLastLayer(child, KeyPath(f'{path}.{key}'), layer_name)
```

### 12. toml_types.py:16

```python
      8 
      9 
     10 def identifyTomlType(value: object) -> TomlType:
     11     """Return the TOML type of a value from tomllib, with dates and times converted to pendulum.
     12 
     13     Raises:
     14         TypeError: value is not a TOML value.
     15     """
>>   16     # int() would also match a bool, and Date() a DateTime, so each subclass comes first
     17     match value:
     18         case bool():
     19             return TomlType.BOOLEAN
     20         case int():
     21             return TomlType.INTEGER
     22         case float():
     23             return TomlType.FLOAT
     24         case str():
     25             return TomlType.STRING
     26         case pendulum.DateTime():
```

### 13. vocabulary.py:14

```python
      6 from collections.abc import Mapping
      7 from dataclasses import dataclass, field
      8 from enum import Enum
      9 from typing import Any, NewType
     10 
     11 
     12 EnvironmentName = NewType('EnvironmentName', str)
     13 LayerName = NewType('LayerName', str)
>>   14 KeyPath = NewType('KeyPath', str)  # dotted, such as 'flags.search_v2.rollout'
     15 TomlTable = dict[str, Any]
     16 
     17 
     18 class InputError(RuntimeError):
     19     pass
     20 
     21 
     22 class FindingKind(Enum):
     23     TYPE_CHANGE = 'type change'
     24     REMOVED_KEY = 'removed key'
```

## old skill, minicached: 6 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/d4835795-a251-427c-9a15-2017f1fa2ff7/scratchpad/samesession/p8_old/minicached`

### 14. cache.py:27

```python
     19     Key,
     20     Outcome,
     21     StoreCommand,
     22     StoreMode,
     23 )
     24 
     25 
     26 _ITEM_OVERHEAD_BYTES = 50
>>   27 _MAX_RELATIVE_EXPTIME = 2_592_000  # 30 days, and a larger exptime is a Unix time
     28 
     29 LOG = logging.getLogger(__name__)
     30 
     31 
     32 class Cache:
     33     def __init__(self, max_bytes: int) -> None:
     34         self._max_bytes = max_bytes
     35         self._items: OrderedDict[Key, Item] = OrderedDict()
     36         self._used_bytes = 0
     37         self._last_cas = 0
```

### 15. commands.py:56

```python
     48     tokens = [token for token in line.split(b' ') if token]
     49     name = tokens[0] if tokens else b''
     50     arguments, noreply = _splitNoreply(tokens[1:])
     51 
     52     match name:
     53         case b'set' | b'add' | b'replace' | b'cas':
     54             return _parseStoreCommand(StoreMode(name.decode('ascii')), arguments, noreply=noreply)
     55         case b'get' | b'gets':
>>   56             # arguments would drop a key named noreply
     57             raw_keys = tokens[1:]
     58             if not raw_keys:
     59                 raise _rejectCommand('missing key')
     60             return RetrieveCommand(tuple(_parseKey(raw_key) for raw_key in raw_keys), with_cas=name == b'gets')
     61         case b'delete':
     62             if len(arguments) != 1:
     63                 raise _rejectCommand('bad command line format')
     64             return DeleteCommand(_parseKey(arguments[0]), noreply)
     65         case b'incr' | b'decr':
     66             if len(arguments) != 2:
```

### 16. server.py:69

```python
     61 
     62     async with asyncio.TaskGroup() as connections:
     63 
     64         def acceptConnection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
     65             writers.add(writer)
     66             task = connections.create_task(_Connection(reader, writer, cache).run())
     67             task.add_done_callback(lambda _: writers.discard(writer))
     68 
>>   69         # + 1 for the '\r' before the '\n' of a full-length line
     70         server = await asyncio.start_server(acceptConnection, _HOST, port, limit=_MAX_LINE_LENGTH + 1)
     71         LOG.info('server.listening', extra={'host': _HOST, 'port': port, 'max_bytes': max_bytes})
     72         await stop.wait()
     73 
     74         LOG.info('server.stopping')
     75         server.close()
     76         # close() would hang shutdown on a client that has stopped reading
     77         for writer in writers:
     78             writer.transport.abort()
     79     await server.wait_closed()
```

### 17. server.py:76

```python
     68 
     69         # + 1 for the '\r' before the '\n' of a full-length line
     70         server = await asyncio.start_server(acceptConnection, _HOST, port, limit=_MAX_LINE_LENGTH + 1)
     71         LOG.info('server.listening', extra={'host': _HOST, 'port': port, 'max_bytes': max_bytes})
     72         await stop.wait()
     73 
     74         LOG.info('server.stopping')
     75         server.close()
>>   76         # close() would hang shutdown on a client that has stopped reading
     77         for writer in writers:
     78             writer.transport.abort()
     79     await server.wait_closed()
     80 
     81 
     82 class _Connection:
     83     def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, cache: Cache) -> None:
     84         self._reader = reader
     85         self._writer = writer
     86         self._cache = cache
```

### 18. server.py:138

```python
    130         try:
    131             line = await self._reader.readuntil(b'\n')
    132         except asyncio.IncompleteReadError:
    133             return None
    134         except asyncio.LimitOverrunError as error:
    135             raise _LineTooLongError from error
    136 
    137         line = line.removesuffix(b'\n').removesuffix(b'\r')
>>  138         # the stream limit alone would admit one byte more on a line ended by a bare '\n'
    139         if len(line) > _MAX_LINE_LENGTH:
    140             raise _LineTooLongError
    141         return line
    142 
    143     async def _sendReply(self, reply: bytes) -> None:
    144         self._writer.write(reply)
    145         await self._writer.drain()
    146 
    147     async def _computeReply(self, command: Request) -> bytes:
    148         match command:
```

### 19. server.py:169

```python
    161                     return _formatOutcome(result, noreply=command.noreply)
    162                 return b'' if command.noreply else _encodeLine(str(result))
    163 
    164     async def _readBlock(self, length: int) -> bytes | None:
    165         """Read a data block and its line end, or skip to the next line and return None on a mismatch."""
    166         chunk = await self._reader.readexactly(length + len(_CRLF))
    167         if chunk.endswith(_CRLF):
    168             return chunk[:length]
>>  169         # skipping unconditionally would discard the next command when the chunk ends a line
    170         if not chunk.endswith(b'\n'):
    171             await self._skipLine()
    172         return None
    173 
    174     async def _skipLine(self) -> None:
    175         while True:
    176             try:
    177                 await self._reader.readuntil(b'\n')
    178                 return
    179             except asyncio.LimitOverrunError as error:
```

## new skill, snapprune: 7 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/d4835795-a251-427c-9a15-2017f1fa2ff7/scratchpad/samesession/p3_new/snapprune`

### 20. __main__.py:110

```python
    102     parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH, help='SQLite run history (default: %(default)s)')
    103     parser.add_argument('-v', '--verbose', action='store_true', help='log every step to stderr')
    104     return parser.parse_args()
    105 
    106 
    107 def parseNow(raw_now: str) -> DateTime | None:
    108     """Parse --now, or log the fault and return None."""
    109     try:
>>  110         # without tz=None, pendulum.parse() reads a value with no offset as UTC
    111         now = pendulum.parse(raw_now, tz=None)
    112     except ValueError as exc:
    113         LOG.error('now.unparseable', extra={'now': raw_now, 'error': str(exc)})
    114         return None
    115     if not isinstance(now, DateTime) or now.utcoffset() is None:
    116         LOG.error('now.not_an_instant', extra={'now': raw_now})
    117         return None
    118     return now
    119 
    120 
```

### 21. deletion.py:27

```python
     19     """Delete each snapshot that is still a regular file.
     20 
     21     Returns:
     22         The names that could not be deleted.
     23     """
     24     failed: set[str] = set()
     25     for judged in doomed:
     26         snapshot_path = snapshot_dir / judged.name
>>   27         # without this recheck, a symbolic link swapped in after the scan is deleted
     28         if snapshot_path.is_symlink() or not snapshot_path.is_file():
     29             _LOG.debug('snapshot.not_regular_file', extra={'snapshot': str(snapshot_path)})
     30             failed.add(judged.name)
     31             continue
     32         try:
     33             snapshot_path.unlink()
     34         except OSError as exc:
     35             _LOG.debug('snapshot.delete_failed', extra={'snapshot': str(snapshot_path), 'error': str(exc)})
     36             failed.add(judged.name)
     37             continue
```

### 22. history.py:104

```python
     96         sort_keys=True,
     97     )
     98     return hashlib.sha256(canonical.encode()).hexdigest()
     99 
    100 
    101 ### vocabulary ###########################################################################################
    102 
    103 
>>  104 # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
    105 class _DecisionRow(NamedTuple):
    106     run_id: int | None
    107     file: str
    108     decision: str
    109     local: str | None
    110     rules: str | None
    111     problem: str | None
```

### 23. policy_file.py:74

```python
     66     raw_keep = raw_policy.get('keep')
     67     if not isinstance(raw_keep, dict):
     68         raise _rejectPolicy(policy_json_path, 'keep is not an object', repr(raw_keep))
     69     if set(raw_keep) != {rule.value for rule in Rule}:
     70         raise _rejectPolicy(policy_json_path, 'keep does not name the four rules', ', '.join(sorted(raw_keep)))
     71     keep: list[Quota] = []
     72     for rule in Rule:
     73         raw_count = raw_keep[rule.value]
>>   74         # without the bool test, JSON true passes as 1
     75         if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
     76             raise _rejectPolicy(policy_json_path, f'keep.{rule.value} is not a non-negative integer', repr(raw_count))
     77         keep.append(Quota(rule=rule, count=raw_count))
     78     return Policy(timezone=timezone, keep=tuple(keep))
     79 
     80 
     81 def _rejectPolicy(policy_json_path: Path, reason: str, detail: str) -> PolicyError:
     82     _LOG.error('policy.rejected', extra={'policy_path': str(policy_json_path), 'reason': reason, 'detail': detail})
     83     return PolicyError(f'{policy_json_path}: {reason}: {detail}')
```

### 24. retention.py:69

```python
     61             seen_periods.add(period)
     62             selected.add(snapshot.name)
     63     return selected
     64 
     65 
     66 def _computePeriodKey(rule: Rule, local: DateTime) -> tuple[int, ...]:
     67     match rule:
     68         case Rule.HOURLY:
>>   69             # an aware local.start_of('hour') would split the repeated hour of a DST change into two periods
     70             return (local.year, local.month, local.day, local.hour)
     71         case Rule.DAILY:
     72             return (local.year, local.month, local.day)
     73         case Rule.WEEKLY:
     74             iso_year, iso_week, _iso_weekday = local.isocalendar()
     75             return (iso_year, iso_week)
     76         case Rule.MONTHLY:
     77             return (local.year, local.month)
```

### 25. scan.py:21

```python
     13 import re
     14 from pathlib import Path
     15 
     16 import pendulum
     17 
     18 from snapprune.vocabulary import Listing, Snapshot
     19 
     20 
>>   21 # \d would admit non-ASCII digits, which int() accepts
     22 _SNAPSHOT_NAME = re.compile(r'db-([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z\.tar\.zst')
     23 
     24 
     25 def listSnapshots(snapshot_dir: Path) -> Listing:
     26     """List the directory's entries.
     27 
     28     Raises:
     29         OSError: the directory cannot be listed.
     30     """
     31     snapshots: list[Snapshot] = []
```

### 26. vocabulary.py:60

```python
     52     snapshots: tuple[Snapshot, ...]
     53     unparseable: tuple[str, ...]
     54     ignored: tuple[str, ...]
     55 
     56 
     57 @dataclass(frozen=True)
     58 class JudgedSnapshot:
     59     name: str
>>   60     local: DateTime  # in the policy's timezone
     61     rules: frozenset[Rule]
     62     newest: bool
     63 
     64     @property
     65     def kept(self) -> bool:
     66         return bool(self.rules) or self.newest
     67 
     68 
     69 @dataclass(frozen=True)
     70 class FlaggedFile:
```

## new skill, layeraudit: 8 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/d4835795-a251-427c-9a15-2017f1fa2ff7/scratchpad/samesession/p5_new/layeraudit`

### 27. checks.py:140

```python
    132 
    133 def _describeTomlType(value: object) -> str:
    134     toml_type = classifyTomlType(value)
    135     article = 'an' if toml_type in (TomlType.INTEGER, TomlType.ARRAY) else 'a'
    136     return f'{article} {toml_type.value}'
    137 
    138 
    139 def _describePercentageProblem(value: object, name: str) -> str | None:
>>  140     # without the bool test, TOML true passes as 1
    141     if isinstance(value, bool) or not isinstance(value, int):
    142         return f'{name} {json.dumps(convertTomlToJson(value))} is {_describeTomlType(value)}, not an integer'
    143     if not _ROLLOUT_MIN <= value <= _ROLLOUT_MAX:
    144         return f'{name} {value} is outside {_ROLLOUT_MIN}..{_ROLLOUT_MAX}'
    145     return None
```

### 28. inputs.py:76

```python
     68 
     69 def _convertDatesToPendulum(value: object) -> object:
     70     match value:
     71         case dict():
     72             return {key: _convertDatesToPendulum(item) for key, item in value.items()}
     73         case list():
     74             return [_convertDatesToPendulum(item) for item in value]
     75         case datetime.datetime():
>>   76             # without tz=value.tzinfo, a local datetime gains a UTC offset absent from the file
     77             return pendulum.instance(value, tz=value.tzinfo)
     78         case datetime.date():
     79             return pendulum.Date(value.year, value.month, value.day)
     80         case datetime.time():
     81             return pendulum.Time(value.hour, value.minute, value.second, value.microsecond)
     82     return value
     83 
     84 
     85 def _parseEnvironments(raw_environments: object) -> dict[str, tuple[LayerName, ...]]:
     86     # without the pattern, a file outside the input directory is read for a layer such as '../secrets'
```

### 29. inputs.py:86

```python
     78         case datetime.date():
     79             return pendulum.Date(value.year, value.month, value.day)
     80         case datetime.time():
     81             return pendulum.Time(value.hour, value.minute, value.second, value.microsecond)
     82     return value
     83 
     84 
     85 def _parseEnvironments(raw_environments: object) -> dict[str, tuple[LayerName, ...]]:
>>   86     # without the pattern, a file outside the input directory is read for a layer such as '../secrets'
     87     LAYER_NAME_PATTERN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]*')
     88     where = f'{_LAYERS_FILE}: environments'
     89 
     90     if not isinstance(raw_environments, dict):
     91         raise _rejectInput(where, 'expected a table of environments')
     92 
     93     environments: dict[str, tuple[LayerName, ...]] = {}
     94     for name, layers in raw_environments.items():
     95         if not isinstance(layers, list) or not all(isinstance(layer, str) for layer in layers):
     96             raise _rejectInput(f'{where}.{name}', 'expected an array of layer names')
```

### 30. merge.py:57

```python
     49 
     50                 earlier_type = classifyTomlType(earlier)
     51                 later_type = classifyTomlType(value)
     52                 if earlier_type != later_type:
     53                     detail = f'{earlier_type.value} in {self.origin[path]}, {later_type.value} in {layer}'
     54                     self.type_changes.append(Finding(FindingKind.TYPE_CHANGE, formatDottedPath(path), layer, detail))
     55                 self.forgetOriginBelow(path)
     56 
>>   57             # without the copy, merging a later layer changes the parsed layer file for every other environment
     58             target[key] = copy.deepcopy(value)
     59             self.recordOrigin(path, value, layer)
     60 
     61     def forgetOriginBelow(self, path: KeyPath) -> None:
     62         stale = [known for known in self.origin if len(known) > len(path) and known[: len(path)] == path]
     63         for known in stale:
     64             del self.origin[known]
     65 
     66     def recordOrigin(self, path: KeyPath, value: object, layer: LayerName) -> None:
     67         self.origin[path] = layer
```

### 31. values.py:25

```python
     17 
     18 
     19 def classifyTomlType(value: object) -> TomlType:
     20     """Return the TOML type of a value from a parsed document.
     21 
     22     Raises:
     23         TypeError: The value is of a type that no TOML document produces.
     24     """
>>   25     # with int() or Date() first, a boolean or a datetime matches its base class
     26     match value:
     27         case bool():
     28             return TomlType.BOOLEAN
     29         case int():
     30             return TomlType.INTEGER
     31         case float():
     32             return TomlType.FLOAT
     33         case str():
     34             return TomlType.STRING
     35         case pendulum.DateTime():
```

### 32. vocabulary.py:12

```python
      4 
      5 import re
      6 from collections.abc import Mapping
      7 from dataclasses import dataclass
      8 from enum import Enum
      9 from typing import NewType
     10 
     11 
>>   12 # a segment such as '[0]' indexes an element of an array of tables
     13 KeyPath = tuple[str, ...]
     14 TomlTable = Mapping[str, object]
     15 LayerName = NewType('LayerName', str)
     16 
     17 
     18 class InputError(RuntimeError):
     19     """The input directory cannot be audited."""
     20 
     21 
     22 class TomlType(Enum):
```

### 33. vocabulary.py:84

```python
     76     path: str
     77     layer: LayerName
     78     detail: str
     79 
     80 
     81 @dataclass(frozen=True)
     82 class MergedConfig:
     83     config: TomlTable
>>   84     # the last layer that set each key, or any key below it
     85     origin: Mapping[KeyPath, LayerName]
     86     type_changes: tuple[Finding, ...]
     87 
     88     def lookupLayer(self, path: KeyPath) -> LayerName:
     89         # a path inside an array of tables belongs to the layer that set the array
     90         for end in range(len(path), 0, -1):
     91             layer = self.origin.get(path[:end])
     92             if layer is not None:
     93                 return layer
     94         raise KeyError(path)
```

### 34. vocabulary.py:89

```python
     81 @dataclass(frozen=True)
     82 class MergedConfig:
     83     config: TomlTable
     84     # the last layer that set each key, or any key below it
     85     origin: Mapping[KeyPath, LayerName]
     86     type_changes: tuple[Finding, ...]
     87 
     88     def lookupLayer(self, path: KeyPath) -> LayerName:
>>   89         # a path inside an array of tables belongs to the layer that set the array
     90         for end in range(len(path), 0, -1):
     91             layer = self.origin.get(path[:end])
     92             if layer is not None:
     93                 return layer
     94         raise KeyError(path)
     95 
     96 
     97 @dataclass(frozen=True)
     98 class EnvironmentAudit:
     99     name: str
```

## new skill, minicached: 10 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/d4835795-a251-427c-9a15-2017f1fa2ff7/scratchpad/samesession/p8_new/minicached`

### 35. cache.py:46

```python
     38 _LOG = logging.getLogger(__name__)
     39 
     40 
     41 class Cache:
     42     """Items bounded by a byte limit, evicted least recently used first."""
     43 
     44     def __init__(self, max_bytes: int) -> None:
     45         self._max_bytes = max_bytes
>>   46         self._items: OrderedDict[Key, Item] = OrderedDict()  # least recently used first
     47         self._expiry_heap: list[tuple[float, CasValue, Key]] = []
     48         self._used_bytes = 0
     49         self._last_cas = CasValue(0)
     50 
     51     def storable(self, key: Key, data_length: int) -> bool:
     52         return _computeItemSize(key, data_length) <= self._max_bytes
     53 
     54     def storeItem(self, command: StorageCommand, data: bytes) -> StoreOutcome:
     55         if not self.storable(command.key, len(data)):
     56             return StoreOutcome.TOO_LARGE
```

### 36. cache.py:130

```python
    122         if item.expires_at is not None:
    123             heapq.heappush(self._expiry_heap, (item.expires_at, item.cas, key))
    124             self._compactExpiryHeap()
    125 
    126     def _purgeExpired(self, now: float) -> None:
    127         while self._expiry_heap and self._expiry_heap[0][0] <= now:
    128             _, cas, key = heapq.heappop(self._expiry_heap)
    129             item = self._items.get(key)
>>  130             # without the cas test, a rewritten key expires at the time of its earlier version
    131             if item is not None and item.cas == cas:
    132                 self._remove(key)
    133 
    134     def _evictLeastRecent(self) -> None:
    135         key, item = self._items.popitem(last=False)
    136         size = _computeItemSize(key, len(item.data))
    137         self._used_bytes -= size
    138         _LOG.info('cache.evicted', extra={'key': key.decode('utf-8', 'backslashreplace'), 'size_bytes': size})
    139 
    140     def _compactExpiryHeap(self) -> None:
```

### 37. cache.py:143

```python
    135         key, item = self._items.popitem(last=False)
    136         size = _computeItemSize(key, len(item.data))
    137         self._used_bytes -= size
    138         _LOG.info('cache.evicted', extra={'key': key.decode('utf-8', 'backslashreplace'), 'size_bytes': size})
    139 
    140     def _compactExpiryHeap(self) -> None:
    141         STALE_RATIO = 2
    142         MIN_REBUILD_ENTRIES = 64
>>  143         # without the rebuild, the heap grows by one stale entry per rewrite of a key with an expiry time
    144         if len(self._expiry_heap) <= STALE_RATIO * len(self._items) + MIN_REBUILD_ENTRIES:
    145             return
    146         self._expiry_heap = [
    147             (item.expires_at, item.cas, key) for key, item in self._items.items() if item.expires_at is not None
    148         ]
    149         heapq.heapify(self._expiry_heap)
    150 
    151 
    152 def _computeItemSize(key: Key, data_length: int) -> int:
    153     return len(key) + data_length + _ITEM_OVERHEAD_BYTES
```

### 38. cache.py:186

```python
    178 
    179 
    180 def _expired(item: Item, now: float) -> bool:
    181     return item.expires_at is not None and item.expires_at <= now
    182 
    183 
    184 def _parseCounter(data: bytes) -> int | None:
    185     MAX_COUNTER_DIGITS = 20
>>  186     # int() alone accepts signs, spaces and underscores, and raises on a value over 4300 digits
    187     if len(data) > MAX_COUNTER_DIGITS or not data.isdigit() or int(data) >= _UINT64_MODULUS:
    188         return None
    189     return int(data)
```

### 39. protocol.py:154

```python
    146     FIRST_PRINTABLE = 0x20
    147     DELETE = 0x7F
    148     if any(byte < FIRST_PRINTABLE or byte == DELETE for byte in token):
    149         return 'key contains a control character'
    150     return None
    151 
    152 
    153 def _parseUnsigned(token: bytes, limit: int) -> int | None:
>>  154     # int() alone accepts signs, spaces and underscores
    155     if not token.isdigit() or int(token) >= limit:
    156         return None
    157     return int(token)
    158 
    159 
    160 def _parseExptime(token: bytes) -> int | None:
    161     magnitude = token.removeprefix(b'-')
    162     if not magnitude.isdigit() or int(magnitude) >= _EXPTIME_LIMIT:
    163         return None
    164     return int(token)
```

### 40. server.py:71

```python
     63 
     64     async with asyncio.TaskGroup() as connections:
     65 
     66         def acceptConnection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
     67             open_writers.add(writer)
     68             task = connections.create_task(_serveConnection(cache, reader, writer))
     69             task.add_done_callback(lambda _: open_writers.discard(writer))
     70 
>>   71         # readuntil() raises LimitOverrunError once a line passes this length
     72         server = await asyncio.start_server(acceptConnection, _HOST, port, limit=_MAX_LINE_BYTES + len(_CRLF))
     73         _LOG.info('server.listening', extra={'host': _HOST, 'port': port, 'max_bytes': max_bytes})
     74         await stop.wait()
     75 
     76         _LOG.info('server.stopping', extra={'connections': len(open_writers)})
     77         server.close()
     78         for writer in open_writers:
     79             writer.close()
     80     await server.wait_closed()
     81 
```

### 41. server.py:154

```python
    146 
    147 
    148 async def _readBlockEnd(reader: asyncio.StreamReader) -> _BlockEnd:
    149     block_end = _BlockEnd.TERMINATED
    150     while True:
    151         try:
    152             chunk = await reader.readuntil(_CRLF)
    153         except asyncio.LimitOverrunError as error:
>>  154             # the read stops before a trailing CR, so a CRLF split across two reads still matches
    155             await reader.readexactly(error.consumed)
    156             block_end = _BlockEnd.MALFORMED
    157             continue
    158         return block_end if chunk == _CRLF else _BlockEnd.MALFORMED
    159 
    160 
    161 async def _buildReply(cache: Cache, reader: asyncio.StreamReader, command: Command) -> bytes | None:
    162     """Run one command.
    163 
    164     Returns:
```

### 42. server.py:184

```python
    176         case QuitCommand():
    177             return None
    178         case UnknownCommand():
    179             return _ERROR_REPLY
    180 
    181 
    182 async def _storeFromStream(cache: Cache, reader: asyncio.StreamReader, command: StorageCommand) -> bytes:
    183     if not cache.storable(command.key, command.length):
>>  184         # readexactly() here would buffer the whole announced length, which a client may set up to 4 GiB
    185         match await _skipDataBlock(reader, command.length):
    186             case _BlockEnd.TERMINATED:
    187                 return _TOO_LARGE_REPLY
    188             case _BlockEnd.MALFORMED:
    189                 return _formatClientError('bad data chunk')
    190 
    191     data = await reader.readexactly(command.length)
    192     match await _readBlockEnd(reader):
    193         case _BlockEnd.TERMINATED:
    194             return _formatStoreReply(cache.storeItem(command, data), command.noreply)
```

### 43. vocabulary.py:39

```python
     31     NON_NUMERIC = 'non_numeric'
     32     TOO_LARGE = 'too_large'
     33 
     34 
     35 @dataclass(frozen=True, slots=True)
     36 class Item:
     37     data: bytes
     38     flags: int
>>   39     expires_at: float | None  # Unix time, None when the item never expires
     40     cas: CasValue
     41 
     42 
     43 @dataclass(frozen=True, slots=True)
     44 class StorageCommand:
     45     mode: StoreMode
     46     key: Key
     47     flags: int
     48     exptime: int
     49     length: int
```

### 44. vocabulary.py:50

```python
     42 
     43 @dataclass(frozen=True, slots=True)
     44 class StorageCommand:
     45     mode: StoreMode
     46     key: Key
     47     flags: int
     48     exptime: int
     49     length: int
>>   50     cas: CasValue | None  # None unless mode is CAS
     51     noreply: bool
     52 
     53 
     54 @dataclass(frozen=True, slots=True)
     55 class RetrievalCommand:
     56     keys: tuple[Key, ...]
     57     with_cas: bool
     58 
     59 
     60 @dataclass(frozen=True, slots=True)
```
