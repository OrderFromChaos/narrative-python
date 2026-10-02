# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## P1 payroll (package payroll): 12 comments

`scratchpad/cycle13/p1/payroll`

### 1. config.py:37

```python
     29 
     30 def readRules(rules_path: Path) -> Rules:
     31     """Read and validate the rules file.
     32 
     33     Raises:
     34         UnusableInputError: The file is missing, unreadable or malformed, or has an unknown timezone.
     35     """
     36     KEYS = ('site_timezones', 'overtime_after_minutes', 'overtime_multiplier', 'round_to_minutes')
>>   37     DECIMAL = re.compile(r'[0-9]+(?:\.[0-9]+)?')  # \d would admit non-ASCII digits such as '٣'
     38 
     39     if not rules_path.is_file():
     40         raise rejectInput(_EVENT, rules_path, 'not a file')
     41     try:
     42         rules_text = rules_path.read_text(encoding='utf-8')
     43     except OSError as exc:
     44         raise rejectInput(_EVENT, rules_path, f'unreadable: {exc.strerror}') from exc
     45     except UnicodeDecodeError as exc:
     46         raise rejectInput(_EVENT, rules_path, 'not UTF-8') from exc
     47     try:
```

### 2. config.py:88

```python
     80         except ValueError as exc:
     81             raise rejectInput(_EVENT, rules_path, f'unknown timezone {raw_timezone!r}') from exc
     82 
     83     return MappingProxyType(site_timezones)
     84 
     85 
     86 def _parsePositiveInteger(raw_rules: dict[str, object], key: str, rules_path: Path) -> int:
     87     value = raw_rules[key]
>>   88     # without the bool test, JSON true passes as 1
     89     if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
     90         raise rejectInput(_EVENT, rules_path, f'{key} is not a positive integer')
     91     return value
```

### 3. logs.py:20

```python
     12 
     13 from payroll.vocabulary import UnusableInputError
     14 
     15 
     16 _STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
     17 _LOCATION = ('module', 'lineno', 'funcName')
     18 
     19 LOG = logging.getLogger('payroll')
>>   20 # logging.NullHandler() stops the last-resort handler from printing this package's warnings.
>>   21 # They reach stderr only when the calling program configures logging.
     22 LOG.addHandler(logging.NullHandler())
     23 
     24 
     25 def configureLogging(*, verbose: bool) -> None:
     26     global LOG
     27     handler = logging.StreamHandler()
     28     handler.setFormatter(_FieldFormatter())
     29     LOG.addHandler(handler)
     30     LOG.setLevel(logging.DEBUG if verbose else logging.INFO)
     31 
```

### 4. logs.py:40

```python
     32 
     33 def rejectInput(event: str, input_path: Path, reason: str, *, line_number: int | None = None) -> UnusableInputError:
     34     """Log an unusable input at ERROR under event, and build the UnusableInputError for the caller to raise."""
     35     extra: dict[str, object] = {'path': str(input_path), 'reason': reason}
     36     location = str(input_path)
     37     if line_number is not None:
     38         extra['line_number'] = line_number
     39         location = f'{input_path} line {line_number}'
>>   40     # without stacklevel=2, the logged location is this function, not the raise site
     41     LOG.error(event, extra=extra, stacklevel=2)
     42     return UnusableInputError(f'{location}: {reason}')
     43 
     44 
     45 class _FieldFormatter(logging.Formatter):
     46     def format(self, record: logging.LogRecord) -> str:
     47         extra = {key: value for key, value in record.__dict__.items() if key not in _STANDARD}
     48         located = {key: getattr(record, key) for key in _LOCATION}
     49         fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
     50         return f'{record.levelname} {record.getMessage()} {fields}'
```

### 5. pay.py:92

```python
     84 
     85     Returns:
     86         One EmployeeWeek per employee and week with a shift, sorted by (week_start, employee_id).
     87     """
     88     minutes_by_week: dict[_EmployeeWeekKey, int] = {}
     89     for shift in shifts_worked:
     90         timezone = rules.site_timezones[employees[shift.employee_id].site]
     91         local_date = shift.started_at.in_timezone(timezone).date()
>>   92         # start_of('week') would follow pendulum.week_starts_at(), which a calling program can change
     93         week_start = local_date.subtract(days=local_date.weekday())
     94         key = _EmployeeWeekKey(shift.employee_id, week_start)
     95         minutes_by_week[key] = minutes_by_week.get(key, 0) + _roundShiftMinutes(shift, rules.round_to_minutes)
     96 
     97     weeks: list[EmployeeWeek] = []
     98     for key, worked_minutes in minutes_by_week.items():
     99         employee = employees[key.employee_id]
    100         regular_minutes = min(worked_minutes, rules.overtime_after_minutes)
    101         overtime_minutes = worked_minutes - regular_minutes
    102         exact_cents = (
```

### 6. pay.py:123

```python
    115         )
    116 
    117     return tuple(sorted(weeks, key=lambda week: (week.week_start, week.employee_id)))
    118 
    119 
    120 def _roundShiftMinutes(shift: Shift, round_to_minutes: int) -> int:
    121     MICROSECONDS_PER_MINUTE = 60_000_000
    122 
>>  123     # pendulum subtracts instants, so a shift across a DST change counts the time worked
    124     elapsed = shift.ended_at - shift.started_at
    125     elapsed_microseconds = elapsed // pendulum.duration(microseconds=1)
    126     return _roundHalfUp(Fraction(elapsed_microseconds, round_to_minutes * MICROSECONDS_PER_MINUTE)) * round_to_minutes
    127 
    128 
    129 def _roundHalfUp(value: Fraction) -> int:
    130     return math.floor(value + Fraction(1, 2))
    131 
    132 
    133 ### vocabulary #########################################################################################
```

### 7. punches.py:83

```python
     75 
     76     raw_badge = raw_punch.get('badge')
     77     badge = EmployeeId(raw_badge) if isinstance(raw_badge, str) else None
     78     if not all(isinstance(raw_punch.get(field), str) for field in FIELDS):
     79         return _rejectLine(location, badge, 'missing or non-string field')
     80     if raw_punch['direction'] not in DIRECTIONS:
     81         return _rejectLine(location, badge, 'unknown direction')
     82     try:
>>   83         # tz=None leaves a timestamp without an offset naive. The default would read it as UTC.
     84         at = pendulum.parse(raw_punch['at'], tz=None)
     85     except ValueError:
     86         return _rejectLine(location, badge, 'unparseable at')
     87     if not isinstance(at, pendulum.DateTime) or at.tzinfo is None:
     88         return _rejectLine(location, badge, 'at has no UTC offset')
     89 
     90     return Punch(
     91         badge=EmployeeId(raw_punch['badge']),
     92         at=at,
     93         direction=Direction(raw_punch['direction']),
```

### 8. report.py:119

```python
    111     lines = [_formatTableRow(row, widths) for row in rows]
    112     lines.append(
    113         f'shifts {payroll.shift_count}, duplicates {payroll.duplicate_count}, problems {len(payroll.problems)}',
    114     )
    115     return '\n'.join(lines)
    116 
    117 
    118 def _formatTableRow(cells: tuple[str, ...], widths: list[int]) -> str:
>>  119     TEXT_COLUMNS = 3  # employee, name and week align left, the numbers right
    120 
    121     padded = []
    122     for column, (cell, width) in enumerate(zip(cells, widths, strict=True)):
    123         padded.append(cell.ljust(width) if column < TEXT_COLUMNS else cell.rjust(width))
    124     return '  '.join(padded).rstrip()
    125 
    126 
    127 def _computeTotals(payroll: Payroll) -> _Totals:
    128     return _Totals(
    129         employee_count=len({week.employee_id for week in payroll.weeks}),
```

### 9. roster.py:32

```python
     24 
     25 def readRoster(roster_path: Path, rules: Rules) -> Mapping[EmployeeId, Employee]:
     26     """Read and validate the roster, checking each site against rules.
     27 
     28     Raises:
     29         UnusableInputError: The file is missing, unreadable or malformed, or a row's site is absent from rules.
     30     """
     31     HEADER = ['employee_id', 'name', 'hourly_rate', 'site']
>>   32     RATE = re.compile(r'[0-9]+(?:\.[0-9]{1,2})?')  # \d would admit non-ASCII digits such as '٣'
     33 
     34     if not roster_path.is_file():
     35         raise rejectInput(_EVENT, roster_path, 'not a file')
     36     try:
     37         # newline='' so a newline quoted inside a field reaches csv unaltered
     38         with roster_path.open(encoding='utf-8', newline='') as roster_file:
     39             rows = list(csv.reader(roster_file))
     40     except OSError as exc:
     41         raise rejectInput(_EVENT, roster_path, f'unreadable: {exc.strerror}') from exc
     42     except UnicodeDecodeError as exc:
```

### 10. roster.py:37

```python
     29         UnusableInputError: The file is missing, unreadable or malformed, or a row's site is absent from rules.
     30     """
     31     HEADER = ['employee_id', 'name', 'hourly_rate', 'site']
     32     RATE = re.compile(r'[0-9]+(?:\.[0-9]{1,2})?')  # \d would admit non-ASCII digits such as '٣'
     33 
     34     if not roster_path.is_file():
     35         raise rejectInput(_EVENT, roster_path, 'not a file')
     36     try:
>>   37         # newline='' so a newline quoted inside a field reaches csv unaltered
     38         with roster_path.open(encoding='utf-8', newline='') as roster_file:
     39             rows = list(csv.reader(roster_file))
     40     except OSError as exc:
     41         raise rejectInput(_EVENT, roster_path, f'unreadable: {exc.strerror}') from exc
     42     except UnicodeDecodeError as exc:
     43         raise rejectInput(_EVENT, roster_path, 'not UTF-8') from exc
     44     except csv.Error as exc:
     45         raise rejectInput(_EVENT, roster_path, f'not CSV: {exc}') from exc
     46 
     47     if not rows or rows[0] != HEADER:
```

### 11. store.py:42

```python
     34         ' PRIMARY KEY (employee_id, week_start))'
     35     )
     36     UPSERT = (
     37         'INSERT INTO employee_weeks VALUES (?, ?, ?, ?, ?)'
     38         ' ON CONFLICT (employee_id, week_start) DO UPDATE SET'
     39         ' regular_minutes = excluded.regular_minutes,'
     40         ' overtime_minutes = excluded.overtime_minutes,'
     41         ' gross_cents = excluded.gross_cents'
>>   42         # without the WHERE, an unchanged row counts as changed in total_changes
     43         ' WHERE regular_minutes != excluded.regular_minutes'
     44         ' OR overtime_minutes != excluded.overtime_minutes'
     45         ' OR gross_cents != excluded.gross_cents'
     46     )
     47 
     48     rows = [
     49         _EmployeeWeekRow(
     50             employee_id=week.employee_id,
     51             week_start=week.week_start.isoformat(),
     52             regular_minutes=week.regular_minutes,
```

### 12. store.py:68

```python
     60         connection.executemany(UPSERT, rows)
     61         changed_rows = connection.total_changes
     62     return changed_rows
     63 
     64 
     65 ### vocabulary #########################################################################################
     66 
     67 
>>   68 # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
     69 class _EmployeeWeekRow(NamedTuple):
     70     employee_id: str
     71     week_start: str
     72     regular_minutes: int
     73     overtime_minutes: int
     74     gross_cents: int
```

## P2 invoices (package invoicing): 13 comments

`scratchpad/cycle13/p2/invoicing`

### 13. billing.py:37

```python
     29     Problem,
     30     ProblemKind,
     31     Subscribe,
     32 )
     33 
     34 
     35 _PRICES_FILENAME = 'prices.json'
     36 _CUSTOMERS_FILENAME = 'customers.csv'
>>   37 # [0-9] and not \d, which admits non-ASCII digits
     38 _MONTH_PATTERN = re.compile(r'(?P<year>[0-9]{4})-(?P<month>[0-9]{2})')
     39 
     40 
     41 def billMonth(input_dir: Path, raw_month: str, prices_path: Path | None = None) -> Billing:
     42     """Read the customers, prices and events of input_dir, and invoice each customer for the month.
     43 
     44     Args:
     45         raw_month: The month as YYYY-MM.
     46         prices_path: The prices file, prices.json in input_dir when None.
     47 
```

### 14. billing.py:102

```python
     94     LOG.error('month.rejected', extra={'month': raw_month})
     95     return ConfigError(f'month is not YYYY-MM: {raw_month!r}')
     96 
     97 
     98 def _dropDuplicateEvents(all_events: Iterable[Event]) -> list[Event]:
     99     seen: set[tuple[CustomerId, DateTime, Action]] = set()
    100     unique_events: list[Event] = []
    101     for event in all_events:
>>  102         # DateTime compares and hashes as an instant, so one moment written with two offsets is one key
    103         key = (event.customer_id, event.at, event.action)
    104         if key not in seen:
    105             seen.add(key)
    106             unique_events.append(event)
    107     return unique_events
    108 
    109 
    110 def _detectProblemKind(event: Event, customers: Mapping[CustomerId, Customer], prices: Prices) -> ProblemKind | None:
    111     if event.customer_id not in customers:
    112         return ProblemKind.UNKNOWN_CUSTOMER
```

### 15. events.py:55

```python
     47 
     48     for events_path in sorted(path for path in input_dir.glob(_EVENTS_GLOB) if path.is_file()):
     49         try:
     50             raw_bytes = events_path.read_bytes()
     51         except OSError as exc:
     52             LOG.error('events.unreadable', extra={'path': str(events_path), 'reason': exc.strerror})
     53             raise ConfigError(f'{events_path}: unreadable: {exc.strerror}') from exc
     54 
>>   55         # str.splitlines() would also split on U+2028, which JSON allows inside a string
     56         raw_lines = raw_bytes.split(b'\n')
     57         if raw_lines[-1] == b'':
     58             raw_lines.pop()
     59         line_count += len(raw_lines)
     60         for line_number, raw_line in enumerate(raw_lines, start=1):
     61             parsed = _parseEventLine(raw_line.removesuffix(b'\r'), SourceLine(events_path.name, line_number))
     62             if isinstance(parsed, Problem):
     63                 malformed.append(parsed)
     64             else:
     65                 events.append(parsed)
```

### 16. events.py:91

```python
     83         return Problem(source, customer_id, ProblemKind.MALFORMED)
     84     return Event(source, customer_id, at, action)
     85 
     86 
     87 def _parseInstant(raw_at: object) -> DateTime | None:
     88     if not isinstance(raw_at, str):
     89         return None
     90     try:
>>   91         # tz=None leaves a time without an offset naive. The default would read it as UTC.
     92         at = pendulum.parse(raw_at, tz=None)
     93     except ValueError:
     94         return None
     95     if not isinstance(at, DateTime) or at.tzinfo is None:
     96         return None
     97     return at
     98 
     99 
    100 def _parseAction(raw_kind: object, raw_plan: object) -> Action | None:
    101     plan = PlanName(raw_plan) if isinstance(raw_plan, str) else None
```

### 17. logs.py:12

```python
      4 """
      5 
      6 from __future__ import annotations
      7 
      8 import logging
      9 import sys
     10 
     11 
>>   12 # the standard formatter discards every field passed in extra
     13 _STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
     14 _LOCATION = ('module', 'lineno', 'funcName')
     15 
     16 LOG = logging.getLogger('invoicing')
     17 # logging.NullHandler() stops the last-resort handler from printing this package's warnings.
     18 # They reach stderr only when the calling program configures logging.
     19 LOG.addHandler(logging.NullHandler())
     20 
     21 
     22 def configureStderrLogging(*, verbose: bool) -> None:
```

### 18. logs.py:17

```python
      9 import sys
     10 
     11 
     12 # the standard formatter discards every field passed in extra
     13 _STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
     14 _LOCATION = ('module', 'lineno', 'funcName')
     15 
     16 LOG = logging.getLogger('invoicing')
>>   17 # logging.NullHandler() stops the last-resort handler from printing this package's warnings.
>>   18 # They reach stderr only when the calling program configures logging.
     19 LOG.addHandler(logging.NullHandler())
     20 
     21 
     22 def configureStderrLogging(*, verbose: bool) -> None:
     23     global LOG
     24     handler = logging.StreamHandler(sys.stderr)
     25     handler.setFormatter(_FieldFormatter())
     26     LOG.addHandler(handler)
     27     LOG.setLevel(logging.DEBUG if verbose else logging.INFO)
     28 
```

### 19. money.py:18

```python
     10 
     11 from __future__ import annotations
     12 
     13 import math
     14 import re
     15 from fractions import Fraction
     16 
     17 
>>   18 # [0-9] and not \d, which admits non-ASCII digits such as '٣'
     19 _AMOUNT_PATTERN = re.compile(r'[0-9]+\.[0-9]{2}')
     20 _RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]+)?')
     21 _CENTS_PER_DOLLAR = 100
     22 
     23 
     24 def parseCents(raw_amount: str) -> int | None:
     25     if not _AMOUNT_PATTERN.fullmatch(raw_amount):
     26         return None
     27     dollars, cents = raw_amount.split('.')
     28     return int(dollars) * _CENTS_PER_DOLLAR + int(cents)
```

### 20. reference_files.py:60

```python
     52 
     53 def readCustomers(customers_path: Path, prices: Prices) -> Mapping[CustomerId, Customer]:
     54     """Parse the customers file, checking each timezone and each state against the tax rates.
     55 
     56     Raises:
     57         ConfigError: the file is unreadable or malformed, or a customer has an unknown timezone or state.
     58     """
     59     try:
>>   60         # newline='' so a newline quoted inside a field reaches the csv module unchanged
     61         with customers_path.open(encoding='utf-8-sig', newline='') as handle:
     62             rows = list(csv.reader(handle, strict=True))
     63     except OSError as exc:
     64         raise _rejectConfig(customers_path, 'unreadable', exc.strerror) from exc
     65     except UnicodeDecodeError as exc:
     66         raise _rejectConfig(customers_path, 'not UTF-8', exc.reason) from exc
     67     except csv.Error as exc:
     68         raise _rejectConfig(customers_path, 'not CSV', str(exc)) from exc
     69 
     70     if not rows or rows[0] != list(_CUSTOMER_HEADER):
```

### 21. replay.py:61

```python
     53             return _Transition(None, Stretch(current.plan, current.start, event.at), in_order=True)
     54 
     55 
     56 ### vocabulary #########################################################################
     57 
     58 
     59 @dataclass(frozen=True)
     60 class _Transition:
>>   61     # the open stretch after the event, None when no subscription is active
     62     current: Stretch | None
     63     closed: Stretch | None
     64     in_order: bool
```

### 22. store.py:49

```python
     41         'name TEXT NOT NULL, '
     42         'lines TEXT NOT NULL, '
     43         'subtotal_cents INTEGER NOT NULL, '
     44         'tax_cents INTEGER NOT NULL, '
     45         'total_cents INTEGER NOT NULL, '
     46         'recorded_at TEXT NOT NULL, '
     47         'PRIMARY KEY (customer_id, month))'
     48     )
>>   49     # subtotal and total follow from lines and tax, so the WHERE compares only name, lines and tax
     50     UPSERT = (
     51         'INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
     52         'ON CONFLICT (customer_id, month) DO UPDATE SET '
     53         'name = excluded.name, lines = excluded.lines, subtotal_cents = excluded.subtotal_cents, '
     54         'tax_cents = excluded.tax_cents, total_cents = excluded.total_cents, recorded_at = excluded.recorded_at '
     55         'WHERE (invoices.name, invoices.lines, invoices.tax_cents) '
     56         'IS NOT (excluded.name, excluded.lines, excluded.tax_cents)'
     57     )
     58     recorded_at = pendulum.now('UTC').replace(microsecond=0).isoformat()
     59     rows = [_buildInvoiceRow(invoice, billing.month.label, recorded_at) for invoice in billing.invoices]
```

### 23. store.py:97

```python
     89         total_cents=invoice.total_cents,
     90         recorded_at=recorded_at,
     91     )
     92 
     93 
     94 ### vocabulary #########################################################################
     95 
     96 
>>   97 # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
     98 class _InvoiceRow(NamedTuple):
     99     customer_id: str
    100     month: str
    101     name: str
    102     lines: str
    103     subtotal_cents: int
    104     tax_cents: int
    105     total_cents: int
    106     recorded_at: str
```

### 24. vocabulary.py:103

```python
     95     events: tuple[Event, ...]
     96     malformed: tuple[Problem, ...]
     97     line_count: int
     98 
     99 
    100 @dataclass(frozen=True)
    101 class Problem:
    102     source: SourceLine
>>  103     # None when the line has no customer string
    104     customer_id: CustomerId | None
    105     kind: ProblemKind
    106 
    107 
    108 @dataclass(frozen=True)
    109 class Stretch:
    110     plan: PlanName
    111     start: DateTime
    112     # None while the subscription is open at the last event
    113     end: DateTime | None
```

### 25. vocabulary.py:112

```python
    104     customer_id: CustomerId | None
    105     kind: ProblemKind
    106 
    107 
    108 @dataclass(frozen=True)
    109 class Stretch:
    110     plan: PlanName
    111     start: DateTime
>>  112     # None while the subscription is open at the last event
    113     end: DateTime | None
    114 
    115 
    116 @dataclass(frozen=True)
    117 class CustomerHistory:
    118     stretches: tuple[Stretch, ...]
    119     out_of_order: tuple[Problem, ...]
    120 
    121 
    122 @dataclass(frozen=True)
```

## P3 snapshot pruner (package snapshot_pruner): 7 comments

`scratchpad/cycle13/p3/snapshot_pruner`

### 26. __main__.py:108

```python
    100 
    101 def parseInstant(raw_now: str) -> DateTime | None:
    102     """Parse --now, and log why when it is not an instant.
    103 
    104     Returns:
    105         None unless the text is an ISO 8601 instant with a UTC offset.
    106     """
    107     try:
>>  108         # without tz=None, pendulum.parse() reads a value with no offset as UTC
    109         parsed = pendulum.parse(raw_now, tz=None)
    110     except ValueError as exc:
    111         LOG.error('now.rejected', extra={'now': raw_now, 'reason': str(exc)})
    112         return None
    113 
    114     if not isinstance(parsed, DateTime) or parsed.tzinfo is None:
    115         LOG.error('now.rejected', extra={'now': raw_now, 'reason': 'needs a date, a time and a UTC offset'})
    116         return None
    117     return parsed
    118 
```

### 27. history.py:84

```python
     76         'keep': {quota.rule.value: quota.count for quota in policy.quotas},
     77     }
     78     return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode('utf-8')).hexdigest()
     79 
     80 
     81 ### vocabulary #########################################################################################
     82 
     83 
>>   84 # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
     85 class _DecisionRow(NamedTuple):
     86     now: str
     87     snapshot_dir: str
     88     policy_sha256: str
     89     recorded_at: str
     90     file: str
     91     decision: str
     92     rules: str
     93     local: str | None
```

### 28. listing.py:28

```python
     20 
     21 
     22 def listSnapshots(snapshot_dir: Path) -> SnapshotListing:
     23     """List the directory's snapshots, and the names with a snapshot's shape and an impossible timestamp.
     24 
     25     Raises:
     26         SnapshotDirError: The path is not a directory, or the directory cannot be listed.
     27     """
>>   28     # \d would admit non-ASCII digits such as '٣'
     29     SNAPSHOT_NAME = re.compile(r'db-([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z\.tar\.zst')
     30 
     31     if not snapshot_dir.is_dir():
     32         raise _rejectSnapshotDir(snapshot_dir, 'not a directory')
     33     try:
     34         entries = sorted(snapshot_dir.iterdir())
     35     except OSError as exc:
     36         raise _rejectSnapshotDir(snapshot_dir, str(exc)) from exc
     37 
     38     snapshots: list[Snapshot] = []
```

### 29. listing.py:43

```python
     35     except OSError as exc:
     36         raise _rejectSnapshotDir(snapshot_dir, str(exc)) from exc
     37 
     38     snapshots: list[Snapshot] = []
     39     unparseable: list[SnapshotName] = []
     40     ignored = 0
     41     for entry in entries:
     42         shape = SNAPSHOT_NAME.fullmatch(entry.name)
>>   43         # is_file() alone would admit a symbolic link to a regular file
     44         if shape is None or entry.is_symlink() or not entry.is_file():
     45             LOG.debug('listing.ignored', extra={'file': entry.name})
     46             ignored += 1
     47             continue
     48 
     49         name = SnapshotName(entry.name)
     50         year, month, day, hour, minute, second = (int(group) for group in shape.groups())
     51         try:
     52             instant = pendulum.datetime(year, month, day, hour, minute, second, tz='UTC')
     53         except ValueError:
```

### 30. logs.py:12

```python
      4 
      5 import logging
      6 
      7 
      8 _STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
      9 _LOCATION = ('module', 'lineno', 'funcName')
     10 
     11 LOG = logging.getLogger('snapshot_pruner')
>>   12 # logging.NullHandler() stops the last-resort handler from printing this package's warnings.
>>   13 # They reach stderr only when the calling program configures logging.
     14 LOG.addHandler(logging.NullHandler())
     15 
     16 
     17 def configureLogging(*, verbose: bool) -> None:
     18     global LOG
     19     handler = logging.StreamHandler()
     20     handler.setFormatter(_FieldFormatter())
     21     LOG.addHandler(handler)
     22     LOG.setLevel(logging.DEBUG if verbose else logging.INFO)
     23 
```

### 31. policy.py:63

```python
     55     if not isinstance(raw_keep, dict) or set(raw_keep) != set(rule_names):
     56         raise _rejectPolicy(policy_path, 'malformed', f'keep needs exactly the keys {", ".join(rule_names)}')
     57 
     58     quotas = tuple(RuleQuota(rule, _readCount(policy_path, rule, raw_keep[rule.value])) for rule in Rule)
     59     return Policy(timezone, quotas)
     60 
     61 
     62 def _readCount(policy_path: Path, rule: Rule, raw_count: object) -> int:
>>   63     # without the bool test, JSON true passes as 1
     64     if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 0:
     65         raise _rejectPolicy(policy_path, 'malformed', f'keep.{rule.value} is not a non-negative integer')
     66     return raw_count
     67 
     68 
     69 def _rejectPolicy(policy_path: Path, reason: str, detail: str) -> PolicyError:
     70     LOG.error('policy.rejected', extra={'path': str(policy_path), 'reason': reason, 'detail': detail}, stacklevel=2)
     71     return PolicyError(f'{policy_path}: {reason}: {detail}')
```

### 32. retention.py:74

```python
     66 
     67     recent_periods = sorted(newest_by_period, reverse=True)[: quota.count]
     68     return frozenset(newest_by_period[period].name for period in recent_periods)
     69 
     70 
     71 def _periodOf(rule: Rule, local: DateTime) -> _PeriodKey:
     72     match rule:
     73         case Rule.HOURLY:
>>   74             # truncating the instant to the hour would split a repeated DST hour into two periods
     75             return _PeriodKey((local.year, local.month, local.day, local.hour))
     76         case Rule.DAILY:
     77             return _PeriodKey((local.year, local.month, local.day))
     78         case Rule.WEEKLY:
     79             iso_date = local.isocalendar()
     80             return _PeriodKey((iso_date.year, iso_date.week))
     81         case Rule.MONTHLY:
     82             return _PeriodKey((local.year, local.month))
     83 
     84 
```

## P4 license audit (package license_audit): 8 comments

`scratchpad/cycle13/p4/license_audit`

### 33. lockfile.py:57

```python
     49 def _parseLockContents(lock: str, lock_text: str) -> LockContents:
     50     """Parse one lock file's text into its pins and its malformed lines.
     51 
     52     Args:
     53         lock: The lock file's name, recorded on each pin and malformed line.
     54     """
     55     PIN = re.compile(
     56         r'(?P<name>[^\s=;#]+)\s*==\s*(?P<version>[A-Za-z0-9.!+_-]+)'
>>   57         r'\s*(?:;\s*[^\s#][^#]*)?'  # environment marker
     58         r'(?:#.*)?',  # inline comment
     59     )
     60     pins: list[PinnedRelease] = []
     61     malformed: list[MalformedLine] = []
     62     for number, line in enumerate(lock_text.splitlines(), start=1):
     63         stripped = line.strip()
     64         if not stripped or stripped.startswith('#'):
     65             continue
     66 
     67         match = PIN.fullmatch(stripped)
```

### 34. lockfile.py:58

```python
     50     """Parse one lock file's text into its pins and its malformed lines.
     51 
     52     Args:
     53         lock: The lock file's name, recorded on each pin and malformed line.
     54     """
     55     PIN = re.compile(
     56         r'(?P<name>[^\s=;#]+)\s*==\s*(?P<version>[A-Za-z0-9.!+_-]+)'
     57         r'\s*(?:;\s*[^\s#][^#]*)?'  # environment marker
>>   58         r'(?:#.*)?',  # inline comment
     59     )
     60     pins: list[PinnedRelease] = []
     61     malformed: list[MalformedLine] = []
     62     for number, line in enumerate(lock_text.splitlines(), start=1):
     63         stripped = line.strip()
     64         if not stripped or stripped.startswith('#'):
     65             continue
     66 
     67         match = PIN.fullmatch(stripped)
     68         if match is None or not identifiers.validPackageName(match['name']):
```

### 35. spdx.py:25

```python
     17 from collections.abc import Callable, Sequence
     18 
     19 from license_audit import identifiers
     20 from license_audit.logs import LOG
     21 from license_audit.vocabulary import AllOf, AnyOf, Expression, LicenseId, LicenseKey, MalformedExpressionError
     22 
     23 
     24 _TOKEN = re.compile(r'[()]|[^\s()]+')
>>   25 _OPERATORS = (('OR', AnyOf), ('AND', AllOf))  # loosest binding first
     26 
     27 
     28 def parseLicenseExpression(expression_text: str) -> Expression:
     29     """Parse the text of an SPDX license expression into a tree.
     30 
     31     Raises:
     32         MalformedExpressionError: The text is empty, unbalanced, or has an operator or license id
     33             out of place.
     34     """
     35     tokens = _TOKEN.findall(expression_text)
```

### 36. spdx.py:44

```python
     36     tree, position = _parseOperation(tokens, 0, 0)
     37     if position != len(tokens):
     38         raise _rejectExpression(expression_text, f'unexpected {tokens[position]!r}')
     39 
     40     return tree
     41 
     42 
     43 def _parseOperation(tokens: Sequence[str], position: int, depth: int) -> tuple[Expression, int]:
>>   44     # depth indexes _OPERATORS, and one past its end is a single operand
     45     if depth == len(_OPERATORS):
     46         return _parseOperand(tokens, position)
     47 
     48     operator, combine = _OPERATORS[depth]
     49     term, position = _parseOperation(tokens, position, depth + 1)
     50     terms = [term]
     51     while position < len(tokens) and tokens[position] == operator:
     52         term, position = _parseOperation(tokens, position + 1, depth + 1)
     53         terms.append(term)
     54 
```

### 37. store.py:37

```python
     29         ' input_dir TEXT NOT NULL,'
     30         ' lock TEXT NOT NULL,'
     31         ' line INTEGER NOT NULL,'
     32         ' package TEXT NOT NULL,'
     33         ' version TEXT NOT NULL,'
     34         ' license_expression TEXT,'
     35         ' verdict TEXT NOT NULL'
     36         ');'
>>   37         # NULLs are distinct under UNIQUE, so without IFNULL a rerun duplicates every unknown-license row
     38         'CREATE UNIQUE INDEX IF NOT EXISTS verdicts_identity ON verdicts ('
     39         " audit_date, input_dir, lock, line, package, version, IFNULL(license_expression, ''), verdict"
     40         ');'
     41     )
     42     audit_date = audit.today.to_date_string()
     43     resolved_input_dir = str(input_dir.resolve())
     44     rows = [
     45         _VerdictRow(
     46             audit_date=audit_date,
     47             input_dir=resolved_input_dir,
```

### 38. store.py:69

```python
     61         connection.executemany('INSERT OR IGNORE INTO verdicts VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
     62         connection.commit()
     63         return connection.total_changes - changes_before
     64 
     65 
     66 ### vocabulary #########################################################################
     67 
     68 
>>   69 # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
     70 class _VerdictRow(NamedTuple):
     71     audit_date: str
     72     input_dir: str
     73     lock: str
     74     line: int
     75     package: str
     76     version: str
     77     license_expression: str | None
     78     verdict: str
```

### 39. vocabulary.py:13

```python
      5 from collections.abc import Mapping
      6 from dataclasses import dataclass
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
>>   13 PackageName = NewType('PackageName', str)  # PEP 503 normalised
     14 LicenseKey = NewType('LicenseKey', str)  # SPDX license id, case-folded
     15 
     16 
     17 class Verdict(Enum):
     18     ALLOWED = 'allowed'
     19     DENIED = 'denied'
     20     UNREVIEWED = 'unreviewed'
     21     UNKNOWN_LICENSE = 'unknown license'
     22 
     23 
```

### 40. vocabulary.py:14

```python
      6 from dataclasses import dataclass
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
     13 PackageName = NewType('PackageName', str)  # PEP 503 normalised
>>   14 LicenseKey = NewType('LicenseKey', str)  # SPDX license id, case-folded
     15 
     16 
     17 class Verdict(Enum):
     18     ALLOWED = 'allowed'
     19     DENIED = 'denied'
     20     UNREVIEWED = 'unreviewed'
     21     UNKNOWN_LICENSE = 'unknown license'
     22 
     23 
     24 class UnusableInputError(RuntimeError):
```

## P5 config audit (package config_audit): 8 comments

`scratchpad/cycle13/p5/config_audit`

### 41. inputs.py:89

```python
     81 
     82 
     83 def _convertDates(table: Mapping[str, object]) -> dict[str, object]:
     84     return {key: _convertDateValue(value) for key, value in table.items()}
     85 
     86 
     87 def _convertDateValue(value: object) -> object:
     88     if isinstance(value, datetime.datetime | datetime.date | datetime.time):
>>   89         # tz=None, because the default tz=UTC would add an offset to a local datetime
     90         return pendulum.instance(value, tz=None)
     91     if isinstance(value, dict):
     92         return _convertDates(value)
     93     if isinstance(value, list):
     94         return [_convertDateValue(item) for item in value]
     95     return value
     96 
     97 
     98 def _readField(
     99     table: Mapping[str, object],
```

### 42. logs.py:14

```python
      6 """
      7 
      8 from __future__ import annotations
      9 
     10 import logging
     11 
     12 
     13 LOG = logging.getLogger('config_audit')
>>   14 # logging.NullHandler() stops the last-resort handler from printing this package's records.
>>   15 # They reach stderr only when the calling program configures logging.
     16 LOG.addHandler(logging.NullHandler())
     17 
     18 _STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
     19 _LOCATION = ('module', 'lineno', 'funcName')
     20 
     21 
     22 class FieldFormatter(logging.Formatter):
     23     def format(self, record: logging.LogRecord) -> str:
     24         extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD}
     25         located = {key: getattr(record, key) for key in _LOCATION}
```

### 43. merge.py:60

```python
     52                     self.type_changes.append(finding)
     53 
     54             self.origins[path] = layer
     55             if not isinstance(value, dict):
     56                 merged[key] = value
     57                 continue
     58 
     59             existing = merged.get(key)
>>   60             # merging into the parsed table would alter the layer for every later environment
     61             child = existing if isinstance(existing, dict) else {}
     62             merged[key] = child
     63             self.mergeTable(child, value, path, layer)
```

### 44. rules.py:121

```python
    113 
    114         Returns:
    115             The integer whether or not it is in range, or None when it is absent or not an integer.
    116         """
    117         value = _lookupValue(self.merged.config, path)
    118         if value is None:
    119             self.report(FindingKind.BAD_ROLLOUT, path, f'no {path[-1]}')
    120             return None
>>  121         # without the bool test, TOML true passes as the integer 1
    122         if isinstance(value, bool) or not isinstance(value, int):
    123             self.report(FindingKind.BAD_ROLLOUT, path, f'{toml_values.classifyTomlType(value).value}, not an integer')
    124             return None
    125         if not _MIN_PERCENTAGE <= value <= _MAX_PERCENTAGE:
    126             self.report(FindingKind.BAD_ROLLOUT, path, f'{value} is outside {_MIN_PERCENTAGE} to {_MAX_PERCENTAGE}')
    127         return value
    128 
    129     def report(self, kind: FindingKind, path: KeyPath, detail: str) -> None:
    130         origins = self.merged.origins
    131         present = next(KeyPath(path[:end]) for end in range(len(path), 0, -1) if path[:end] in origins)
```

### 45. rules.py:136

```python
    128 
    129     def report(self, kind: FindingKind, path: KeyPath, detail: str) -> None:
    130         origins = self.merged.origins
    131         present = next(KeyPath(path[:end]) for end in range(len(path), 0, -1) if path[:end] in origins)
    132         self.findings.append(Finding(kind, toml_values.joinKeyPath(path), origins[present], detail))
    133 
    134 
    135 def _lookupValue(config: Mapping[str, object], path: KeyPath) -> object | None:
>>  136     # TOML has no null, so None means absent
    137     value: object = config
    138     for key in path:
    139         if not isinstance(value, dict) or key not in value:
    140             return None
    141         value = value[key]
    142     return value
```

### 46. toml_values.py:16

```python
      8 from collections.abc import Iterator, Mapping
      9 
     10 import pendulum
     11 
     12 from config_audit.vocabulary import KeyPath, TomlType
     13 
     14 
     15 def classifyTomlType(value: object) -> TomlType:
>>   16     # without testing bool first, classifyTomlType() would return INTEGER for True
     17     if isinstance(value, bool):
     18         return TomlType.BOOLEAN
     19     if isinstance(value, int):
     20         return TomlType.INTEGER
     21     if isinstance(value, float):
     22         return TomlType.FLOAT
     23     if isinstance(value, str):
     24         return TomlType.STRING
     25     # without testing DateTime first, classifyTomlType() would return DATE for a DateTime
     26     if isinstance(value, pendulum.DateTime):
```

### 47. toml_values.py:25

```python
     17     if isinstance(value, bool):
     18         return TomlType.BOOLEAN
     19     if isinstance(value, int):
     20         return TomlType.INTEGER
     21     if isinstance(value, float):
     22         return TomlType.FLOAT
     23     if isinstance(value, str):
     24         return TomlType.STRING
>>   25     # without testing DateTime first, classifyTomlType() would return DATE for a DateTime
     26     if isinstance(value, pendulum.DateTime):
     27         return TomlType.DATETIME
     28     if isinstance(value, pendulum.Date):
     29         return TomlType.DATE
     30     if isinstance(value, pendulum.Time):
     31         return TomlType.TIME
     32     if isinstance(value, list):
     33         return TomlType.ARRAY
     34     return TomlType.TABLE
     35 
```

### 48. toml_values.py:50

```python
     42     for key, value in table.items():
     43         path = KeyPath((*prefix, key))
     44         yield path, value
     45         if isinstance(value, dict):
     46             yield from walkTable(value, path)
     47 
     48 
     49 def joinKeyPath(path: KeyPath) -> str:
>>   50     # keys are joined unquoted, so ('a.b',) and ('a', 'b') render alike
     51     return '.'.join(path)
```

## P6 chess (package pgnreplay): 8 comments

`scratchpad/cycle13/p6/pgnreplay`

### 49. board.py:112

```python
    104             piece = position.board[squareAt(file, rank)]
    105             if piece is None:
    106                 empty_run += 1
    107                 continue
    108             text += (str(empty_run) if empty_run else '') + _pieceLetter(piece)
    109             empty_run = 0
    110         ranks.append(text + (str(empty_run) if empty_run else ''))
    111 
>>  112     # CastlingRight members are in FEN order, KQkq
    113     castling = ''.join(right.value for right in CastlingRight if right in position.castling) or '-'
    114     en_passant = '-' if position.en_passant is None else _formatSquare(position.en_passant)
    115     return f'{"/".join(ranks)} {position.turn.value} {castling} {en_passant}'
    116 
    117 
    118 def applyMove(position: Position, move: Move) -> Position:
    119     return _dropUncapturableEnPassant(_placeMove(position, move))
    120 
    121 
    122 def legalMoves(position: Position) -> list[Move]:
```

### 50. board.py:500

```python
    492 
    493 @dataclass(frozen=True)
    494 class _Castling:
    495     right: CastlingRight
    496     color: Color
    497     king_home: Square
    498     rook_home: Square
    499     between: tuple[Square, ...]
>>  500     king_passes: Square  # the rook lands here
    501     king_landing: Square
```

### 51. logs.py:14

```python
      6 """
      7 
      8 from __future__ import annotations
      9 
     10 import logging
     11 import sys
     12 
     13 
>>   14 # the standard formatter discards extra, so _FieldFormatter prints every attribute outside this set
     15 _STANDARD_ATTRIBUTES = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
     16 _LOCATION_ATTRIBUTES = ('module', 'lineno', 'funcName')
     17 
     18 LOG = logging.getLogger('pgnreplay')
     19 
     20 
     21 def configureLogging(*, verbose: bool) -> None:
     22     global LOG
     23     handler = logging.StreamHandler(sys.stderr)
     24     handler.setFormatter(_FieldFormatter())
```

### 52. pgn.py:71

```python
     63         set_up=tags.get('SetUp'),
     64         raw_fen=tags.get('FEN'),
     65         moves=_extractMainLine(movetext),
     66     )
     67 
     68 
     69 def _extractMainLine(movetext: str) -> tuple[str, ...]:
     70     """Return the main line's SAN tokens, up to the first result token."""
>>   71     # a comment, a parenthesis, or a run of characters up to whitespace, a brace or a parenthesis
     72     TOKEN = re.compile(r'\{[^}]*\}?|[()]|[^\s{}()]+')
     73     MOVE_NUMBER = re.compile(r'\A[0-9]+\.+')
     74     NAG = re.compile(r'\$[0-9]+')
     75     RESULTS = ('1-0', '0-1', '1/2-1/2', '*')
     76 
     77     moves = []
     78     depth = 0
     79     for token in TOKEN.findall(movetext):
     80         if token == '(':
     81             depth += 1
```

### 53. pgn.py:89

```python
     81             depth += 1
     82         elif token == ')':
     83             depth = max(depth - 1, 0)
     84         elif depth or token.startswith('{') or NAG.fullmatch(token):
     85             continue
     86         elif token in RESULTS:
     87             break
     88         else:
>>   89             # a move number may run into its move, as in 1.e4
     90             san = MOVE_NUMBER.sub('', token, count=1)
     91             if san:
     92                 moves.append(san)
     93     return tuple(moves)
```

### 54. san.py:85

```python
     77 
     78     pawn_match = _PAWN_SAN.fullmatch(stripped)
     79     if pawn_match is None:
     80         return None
     81     target = _parseTarget(pawn_match)
     82     raw_file, raw_promotion = pawn_match['file'], pawn_match['promotion']
     83     return _SanMove(
     84         kind=PieceKind.PAWN,
>>   85         # a pawn push stays on its file
     86         origin_file=board.fileOf(target) if raw_file is None else board.FILE_NAMES.index(raw_file),
     87         origin_rank=None,
     88         capture=pawn_match['capture'] is not None,
     89         target=target,
     90         promotion=None if raw_promotion is None else PieceKind(raw_promotion.lower()),
     91     )
     92 
     93 
     94 def _parseTarget(san_match: re.Match[str]) -> Square:
     95     file = board.FILE_NAMES.index(san_match['target_file'])
```

### 55. vocabulary.py:88

```python
     80 Board: TypeAlias = tuple[Piece | None, ...]
     81 
     82 
     83 @dataclass(frozen=True)
     84 class Position:
     85     board: Board
     86     turn: Color
     87     castling: frozenset[CastlingRight]
>>   88     en_passant: Square | None  # None unless an en passant capture onto it is legal
     89     halfmove_clock: int
     90     fullmove_number: int
     91 
     92 
     93 @dataclass(frozen=True)
     94 class Move:
     95     piece: Piece
     96     origin: Square
     97     target: Square
     98     promotion: PieceKind | None
```

### 56. vocabulary.py:114

```python
    106     set_up: str | None
    107     raw_fen: str | None
    108     moves: tuple[str, ...]
    109 
    110 
    111 @dataclass(frozen=True)
    112 class IllegalMove:
    113     ply: int
>>  114     san: str | None  # None only for a game with no moves and an unusable FEN tag
    115     reason: str
    116 
    117 
    118 @dataclass(frozen=True)
    119 class ReplayedGame:
    120     white: str | None
    121     black: str | None
    122     plies: int
    123     fen: str
    124     ending: Ending
```

## P7 MIDI (package midi_analyser): 5 comments

`scratchpad/cycle13/p7/midi_analyser`

### 57. analysis.py:78

```python
     70 
     71     boundaries: list[tuple[Tick, int]] = []
     72     for note in notes:
     73         boundaries.append((note.start, STARTING))
     74         boundaries.append((note.end, ENDING))
     75 
     76     sounding = 0
     77     max_sounding = 0
>>   78     # ENDING sorts before STARTING at a tied tick. Sorting on the tick alone would count a note ending
>>   79     # on a tick as overlapping one starting there.
     80     for _, change in sorted(boundaries):
     81         sounding += change
     82         max_sounding = max(max_sounding, sounding)
     83 
     84     return max_sounding
```

### 58. report.py:139

```python
    131                 f'time={_formatTimeSignature(analysis.time_signature)} '
    132                 f'tempos={analysis.tempo_change_count} notes={analysis.note_count} range={pitch_range} '
    133                 f'drums={analysis.drum_hit_count} polyphony={analysis.max_polyphony} '
    134                 f'hanging={analysis.hanging_count} orphans={analysis.orphan_off_count}'
    135             )
    136 
    137 
    138 def _formatTimeSignature(time_signature: TimeSignature | None) -> str:
>>  139     # 4/4 is the SMF default
    140     if time_signature is None:
    141         return '4/4'
    142     return f'{time_signature.numerator}/{time_signature.denominator}'
    143 
    144 
    145 def _formatNoteName(pitch: Pitch) -> str:
    146     NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    147     octave, step = divmod(pitch, len(NAMES))
    148     return f'{NAMES[step]}{octave - 1}'
    149 
```

### 59. smf.py:139

```python
    131                 time_signatures.append(TimeSignature(tick, payload[0], 2 ** payload[1]))
    132             continue
    133         if lead in SYSTEM_EXCLUSIVE:
    134             cursor.readBytes(cursor.readVariableLength())
    135             continue
    136         if lead >= SYSTEM_STATUS:
    137             raise _rejectMidi(f'undefined status byte 0x{lead:02X}', offset=cursor.position - 1)
    138 
>>  139         # running status: the last channel status byte applies to a data byte in a status byte's place
    140         if lead & STATUS_BIT:
    141             running_status = lead
    142             first_data = cursor.readByte()
    143         else:
    144             first_data = lead
    145         if running_status is None:
    146             raise _rejectMidi('data byte before any channel status byte', offset=cursor.position - 1)
    147 
    148         kind, channel = divmod(running_status, 16)
    149         if kind in ONE_DATA_BYTE:
```

### 60. smf.py:186

```python
    178         taken = self.data[self.position : end]
    179         self.position = end
    180         return taken
    181 
    182     def readByte(self) -> int:
    183         return self.readBytes(1)[0]
    184 
    185     def readVariableLength(self) -> int:
>>  186         # 7 bits per byte, most significant first, top bit set on all but the last
    187         value = 0
    188         while True:
    189             byte = self.readByte()
    190             value = (value << 7) | (byte & 0x7F)
    191             if not byte & 0x80:
    192                 return value
    193 
    194 
    195 ### vocabulary #########################################################################
    196 
```

### 61. tempo.py:31

```python
     23         self.spans = [_TempoSpan(Tick(0), Fraction(0), DEFAULT_MICROSECONDS_PER_QUARTER)]
     24         for set_tempo in sorted(set_tempos, key=lambda event: event.tick):
     25             start_seconds = self.secondsAt(set_tempo.tick)
     26             self.spans.append(_TempoSpan(set_tempo.tick, start_seconds, set_tempo.microseconds_per_quarter))
     27 
     28     def secondsAt(self, tick: Tick) -> Fraction:
     29         MICROSECONDS_PER_SECOND = 1_000_000
     30 
>>   31         # the last span starting at or before the tick
     32         span = self.spans[bisect_right(self.spans, tick, key=lambda candidate: candidate.start_tick) - 1]
     33         elapsed_ticks = tick - span.start_tick
     34         return span.start_seconds + Fraction(
     35             elapsed_ticks * span.microseconds_per_quarter,
     36             self.ticks_per_quarter * MICROSECONDS_PER_SECOND,
     37         )
     38 
     39 
     40 ### vocabulary #########################################################################
     41 
```

## P8 cache server (package cache_server): 8 comments

`scratchpad/cycle13/p8/cache_server`

### 62. protocol.py:135

```python
    127     MAX_KEY_BYTES = 250
    128     CONTROL_BYTES = frozenset(range(0x20)) | {0x7F}
    129     if len(raw_key) > MAX_KEY_BYTES or not CONTROL_BYTES.isdisjoint(raw_key):
    130         raise _rejectLine('bad key')
    131     return Key(raw_key)
    132 
    133 
    134 def _parseUnsigned(raw_number: bytes, *, bits: int) -> int:
>>  135     # on str, isdigit() would admit non-ASCII digits such as '²'
    136     if not raw_number.isdigit() or int(raw_number) >= 1 << bits:
    137         raise _rejectLine('bad command line format')
    138     return int(raw_number)
    139 
    140 
    141 def _parseExptime(raw_exptime: bytes) -> int:
    142     magnitude = _parseUnsigned(raw_exptime.removeprefix(b'-'), bits=63)
    143     return -magnitude if raw_exptime.startswith(b'-') else magnitude
    144 
    145 
```

### 63. server.py:33

```python
     25     connections: set[asyncio.Task[None]] = set()
     26 
     27     def acceptConnection(reader: StreamReader, writer: StreamWriter) -> None:
     28         task = asyncio.create_task(_answerConnection(reader, writer, cache))
     29         connections.add(task)
     30         task.add_done_callback(connections.discard)
     31 
     32     try:
>>   33         # limit makes readuntil() raise LimitOverrunError on a line longer than MAX_LINE_BYTES
     34         listener = await asyncio.start_server(acceptConnection, _LISTEN_HOST, port, limit=protocol.MAX_LINE_BYTES)
     35     except OSError as exc:
     36         raise _rejectPort(port, exc) from exc
     37 
     38     stopped = asyncio.Event()
     39     loop = asyncio.get_running_loop()
     40     for signal_number in (signal.SIGINT, signal.SIGTERM):
     41         loop.add_signal_handler(signal_number, stopped.set)
     42     LOG.info('server.listening', extra={'port': port, 'max_bytes': max_bytes})
     43     await stopped.wait()
```

### 64. session.py:91

```python
     83 
     84 async def _receiveBlock(reader: StreamReader, length: int) -> bytes:
     85     data = await reader.readexactly(length)
     86     await _consumeTerminator(reader)
     87     return data
     88 
     89 
     90 async def _discardBlock(reader: StreamReader, length: int) -> None:
>>   91     # readexactly(length) would buffer a block of any announced length
     92     CHUNK_BYTES = 65536
     93     remaining = length
     94     while remaining > 0:
     95         remaining -= len(await reader.readexactly(min(remaining, CHUNK_BYTES)))
     96     await _consumeTerminator(reader)
     97 
     98 
     99 async def _consumeTerminator(reader: StreamReader) -> None:
    100     # readexactly(2) would leave the rest of a bad block to parse as commands
    101     if await reader.readuntil(protocol.CRLF) != protocol.CRLF:
```

### 65. session.py:100

```python
     92     CHUNK_BYTES = 65536
     93     remaining = length
     94     while remaining > 0:
     95         remaining -= len(await reader.readexactly(min(remaining, CHUNK_BYTES)))
     96     await _consumeTerminator(reader)
     97 
     98 
     99 async def _consumeTerminator(reader: StreamReader) -> None:
>>  100     # readexactly(2) would leave the rest of a bad block to parse as commands
    101     if await reader.readuntil(protocol.CRLF) != protocol.CRLF:
    102         raise _rejectBlock()
    103 
    104 
    105 def _rejectBlock() -> ClientError:
    106     LOG.debug('block.rejected')
    107     return ClientError('bad data chunk')
```

### 66. store.py:37

```python
     29 _ITEM_OVERHEAD_BYTES = 50
     30 
     31 _UINT64_LIMIT = 1 << 64
     32 
     33 
     34 class Store:
     35     def __init__(self, max_bytes: int) -> None:
     36         self._max_bytes = max_bytes
>>   37         self._items: OrderedDict[Key, Item] = OrderedDict()  # least recently used first
     38         self._expiries: list[_Expiry] = []  # min-heap, entries of replaced items skipped by cas
     39         self._used_bytes = 0
     40         self._last_cas = 0
     41 
     42     def storable(self, key: Key, data_length: int) -> bool:
     43         return _computeItemSize(key, data_length) <= self._max_bytes
     44 
     45     def storeItem(self, command: StorageCommand, data: bytes) -> Outcome:
     46         now = time.monotonic()
     47         self._purgeExpired(now)
```

### 67. store.py:38

```python
     30 
     31 _UINT64_LIMIT = 1 << 64
     32 
     33 
     34 class Store:
     35     def __init__(self, max_bytes: int) -> None:
     36         self._max_bytes = max_bytes
     37         self._items: OrderedDict[Key, Item] = OrderedDict()  # least recently used first
>>   38         self._expiries: list[_Expiry] = []  # min-heap, entries of replaced items skipped by cas
     39         self._used_bytes = 0
     40         self._last_cas = 0
     41 
     42     def storable(self, key: Key, data_length: int) -> bool:
     43         return _computeItemSize(key, data_length) <= self._max_bytes
     44 
     45     def storeItem(self, command: StorageCommand, data: bytes) -> Outcome:
     46         now = time.monotonic()
     47         self._purgeExpired(now)
     48         if not self.storable(command.key, len(data)):
```

### 68. store.py:55

```python
     47         self._purgeExpired(now)
     48         if not self.storable(command.key, len(data)):
     49             return Outcome.TOO_LARGE
     50         refusal = _computeRefusal(command, self._items.get(command.key))
     51         if refusal is not None:
     52             return refusal
     53 
     54         deadline = _computeDeadline(command.exptime, now)
>>   55         # _insert() would evict live items to fit an item that is already expired
     56         if deadline is not None and deadline <= now:
     57             self._discard(command.key)
     58             return Outcome.STORED
     59         return self._insert(command.key, flags=command.flags, data=data, deadline=deadline)
     60 
     61     def fetchItems(self, keys: Iterable[Key]) -> list[Item]:
     62         self._purgeExpired(time.monotonic())
     63         found: list[Item] = []
     64         for key in keys:
     65             item = self._items.get(key)
```

### 69. store.py:159

```python
    151             return Outcome.NOT_STORED if current is None else None
    152         case StorageVerb.CAS:
    153             if current is None:
    154                 return Outcome.NOT_FOUND
    155             return None if current.cas == command.cas_unique else Outcome.EXISTS
    156 
    157 
    158 def _computeDeadline(exptime: int, now: float) -> float | None:
>>  159     # memcached reads an exptime above 30 days as a Unix time
    160     MAX_RELATIVE_EXPTIME_S = 2_592_000
    161     if exptime == 0:
    162         return None
    163     if exptime <= MAX_RELATIVE_EXPTIME_S:
    164         return now + exptime
    165     return now + (exptime - time.time())
    166 
    167 
    168 def _numeric(data: bytes) -> bool:
    169     return data.isdigit() and int(data) < _UINT64_LIMIT
```

## P9 text wrapping (package termwrap): 11 comments

`scratchpad/cycle13/p9/termwrap`

### 70. measure.py:66

```python
     58         if character == '\n':
     59             tokens.append(LineFeed(position))
     60         elif character == _SOFT_HYPHEN:
     61             tokens.append(SoftHyphen())
     62         elif character == ' ':
     63             _appendSpace(tokens)
     64         elif unicodedata.category(character) == 'Cc':
     65             raise _rejectCharacter(position, character, 'control character')
>>   66         # tested before East Asian Width, so a combining mark of width W such as U+3099 takes 0 columns
     67         elif unicodedata.combining(character) != 0 or character in _ZERO_WIDTH:
     68             _appendZeroWidth(tokens, character)
     69         else:
     70             wide = unicodedata.east_asian_width(character) in {'W', 'F'}
     71             tokens.append(Cluster(character, 2 if wide else 1))
     72         position += 1
     73 
     74     return tokens
     75 
     76 
```

### 71. measure.py:84

```python
     76 
     77 def _rejectCharacter(position: int, character: str, reason: str) -> ValueError:
     78     code_point = f'U+{ord(character):04X}'
     79     _LOG.debug('text.rejected', extra={'reason': reason, 'code_point': code_point, 'position': position})
     80     return ValueError(f'{reason}: {code_point} at index {position}')
     81 
     82 
     83 def _appendSpace(tokens: list[Token]) -> None:
>>   84     # an SGR sequence between two spaces goes into the run, so every space is dropped at a break there
     85     trailing = len(tokens)
     86     while trailing > 0 and isinstance(tokens[trailing - 1], Style):
     87         trailing -= 1
     88     run = tokens[trailing - 1] if trailing > 0 else None
     89     if not isinstance(run, SpaceRun):
     90         tokens.append(SpaceRun(' ', 1, ()))
     91         return
     92 
     93     styles = tuple(token for token in tokens[trailing:] if isinstance(token, Style))
     94     sequences = ''.join(style.sequence for style in styles)
```

### 72. vocabulary.py:11

```python
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from typing import TypeAlias
      7 
      8 
      9 @dataclass(frozen=True)
     10 class Cluster:
>>   11     text: str  # a character, then the zero-width characters after it
     12     width: int
     13 
     14 
     15 @dataclass(frozen=True)
     16 class Style:
     17     sequence: str  # an SGR escape sequence such as '\x1b[1m'
     18     reset: bool
     19 
     20 
     21 @dataclass(frozen=True)
```

### 73. vocabulary.py:17

```python
      9 @dataclass(frozen=True)
     10 class Cluster:
     11     text: str  # a character, then the zero-width characters after it
     12     width: int
     13 
     14 
     15 @dataclass(frozen=True)
     16 class Style:
>>   17     sequence: str  # an SGR escape sequence such as '\x1b[1m'
     18     reset: bool
     19 
     20 
     21 @dataclass(frozen=True)
     22 class SpaceRun:
     23     text: str  # U+0020 spaces, with any SGR sequences between them
     24     width: int
     25     styles: tuple[Style, ...]
     26 
     27 
```

### 74. vocabulary.py:23

```python
     15 @dataclass(frozen=True)
     16 class Style:
     17     sequence: str  # an SGR escape sequence such as '\x1b[1m'
     18     reset: bool
     19 
     20 
     21 @dataclass(frozen=True)
     22 class SpaceRun:
>>   23     text: str  # U+0020 spaces, with any SGR sequences between them
     24     width: int
     25     styles: tuple[Style, ...]
     26 
     27 
     28 @dataclass(frozen=True)
     29 class SoftHyphen:
     30     pass
     31 
     32 
     33 @dataclass(frozen=True)
```

### 75. wrapping.py:83

```python
     75 
     76     Returns:
     77         The last break that fits, else a break before the first cluster that does not fit, else the
     78         rest of the paragraph without its trailing spaces.
     79     """
     80     columns = 0
     81     seen_cluster = False
     82     latest: _LineCut | None = None
>>   83     trailing: _LineCut | None = None  # the break at a space run with no cluster after it
     84     for position in range(start, len(paragraph)):
     85         token = paragraph[position]
     86         match token:
     87             case Cluster():
     88                 if columns + token.width > width:
     89                     if latest is not None:
     90                         return latest
     91                     return _LineCut(tuple(paragraph[start:position]), position, hyphen=False)
     92                 columns += token.width
     93                 seen_cluster = True
```

### 76. wrapping.py:100

```python
     92                 columns += token.width
     93                 seen_cluster = True
     94                 trailing = None
     95             case SpaceRun():
     96                 trailing = _LineCut((*paragraph[start:position], *token.styles), position + 1, hyphen=False)
     97                 latest = trailing
     98                 columns += token.width
     99             case SoftHyphen():
>>  100                 # the '-' shown at the break takes a column
    101                 if seen_cluster and columns + 1 <= width:
    102                     latest = _LineCut(tuple(paragraph[start:position]), position + 1, hyphen=True)
    103             case Style():
    104                 pass
    105 
    106     if trailing is None:
    107         return _LineCut(tuple(paragraph[start:]), len(paragraph), hyphen=False)
    108     return _LineCut((*trailing.content, *paragraph[trailing.resume :]), len(paragraph), hyphen=False)
    109 
    110 
```

### 77. wrapping.py:116

```python
    108     return _LineCut((*trailing.content, *paragraph[trailing.resume :]), len(paragraph), hyphen=False)
    109 
    110 
    111 ### vocabulary #########################################################################
    112 
    113 
    114 @dataclass(frozen=True)
    115 class _LineCut:
>>  116     content: tuple[InlineToken, ...]  # the line's tokens, with the spaces at the break removed
    117     resume: int  # paragraph position where the next line starts
    118     hyphen: bool
    119 
    120 
    121 class _Typesetter:
    122     """Render lines, starting each one with the SGR sequences since the last reset."""
    123 
    124     def __init__(self) -> None:
    125         self.lines: list[str] = []
    126         self.active: list[Style] = []
```

### 78. wrapping.py:117

```python
    109 
    110 
    111 ### vocabulary #########################################################################
    112 
    113 
    114 @dataclass(frozen=True)
    115 class _LineCut:
    116     content: tuple[InlineToken, ...]  # the line's tokens, with the spaces at the break removed
>>  117     resume: int  # paragraph position where the next line starts
    118     hyphen: bool
    119 
    120 
    121 class _Typesetter:
    122     """Render lines, starting each one with the SGR sequences since the last reset."""
    123 
    124     def __init__(self) -> None:
    125         self.lines: list[str] = []
    126         self.active: list[Style] = []
    127         self.unclosed = False  # the last line ends inside a style
```

### 79. wrapping.py:127

```python
    119 
    120 
    121 class _Typesetter:
    122     """Render lines, starting each one with the SGR sequences since the last reset."""
    123 
    124     def __init__(self) -> None:
    125         self.lines: list[str] = []
    126         self.active: list[Style] = []
>>  127         self.unclosed = False  # the last line ends inside a style
    128 
    129     def setLine(self, content: Sequence[InlineToken], *, hyphen: bool) -> None:
    130         if self.unclosed:
    131             self.lines[-1] += _RESET
    132         if not content:
    133             self.lines.append('')
    134             self.unclosed = False
    135             return
    136 
    137         parts = [style.sequence for style in self.active]
```

### 80. wrapping.py:145

```python
    137         parts = [style.sequence for style in self.active]
    138         parts.extend(self._renderToken(token) for token in content)
    139         if hyphen:
    140             parts.append('-')
    141         self.lines.append(''.join(parts))
    142         self.unclosed = bool(self.active)
    143 
    144     def skipLine(self, content: Iterable[InlineToken]) -> None:
>>  145         # the styles apply to the lines after, and the text is discarded
    146         for token in content:
    147             self._renderToken(token)
    148 
    149     def _renderToken(self, token: InlineToken) -> str:
    150         match token:
    151             case Cluster():
    152                 return token.text
    153             case SpaceRun():
    154                 self._applyStyles(token.styles)
    155                 return token.text
```

## P10 change request (comments added to midi_report): 4 comments

`scratchpad/cycle13/p10/fixture/midi_report`

### 81. analysis.py:87

```python
     79     events: list[_EventT] = []
     80     for track in tracks:
     81         events.extend(event for event in track.events if isinstance(event, event_type))
     82 
     83     return events
     84 
     85 
     86 def _findFirstEvent(tracks: Iterable[Track], event_type: type[_EventT]) -> _EventT | None:
>>   87     # of events on one tick, min() returns the first in track order
     88     return min(_collectEvents(tracks, event_type), key=lambda each: each.tick, default=None)
     89 
     90 
     91 def _findLongestNote(notes: Iterable[Note], tempo_map: TempoMap) -> TimedNote | None:
     92     """Find the note that lasts the most seconds.
     93 
     94     Ties go to the earliest start, then the lowest pitch, then the lowest channel.
     95     """
     96     timed_notes: list[TimedNote] = []
     97     for note in notes:
```

### 82. report.py:176

```python
    168     # a Standard MIDI File without a time signature is in 4/4
    169     if time_signature is None:
    170         return '4/4'
    171 
    172     return f'{time_signature.numerator}/{time_signature.denominator}'
    173 
    174 
    175 def _nameKeySignature(key_signature: KeySignature) -> str:
>>  176     # tonics in circle-of-fifths order, one place per sharp or flat
    177     TONICS = ('Cb', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#')
    178     C_MAJOR = TONICS.index('C')
    179     A_MINOR = TONICS.index('A')
    180     match key_signature.mode:
    181         case KeyMode.MAJOR:
    182             return f'{TONICS[C_MAJOR + key_signature.sharps]} major'
    183         case KeyMode.MINOR:
    184             return f'{TONICS[A_MINOR + key_signature.sharps]} minor'
    185 
    186 
```

### 83. tempo.py:52

```python
     44     return Fraction(tick_microseconds, tempo_map.ticks_per_quarter * MICROSECONDS_PER_SECOND)
     45 
     46 
     47 def measureBpmRange(tempo_map: TempoMap, end_tick: Tick) -> BpmRange | None:
     48     MICROSECONDS_PER_MINUTE = 60_000_000
     49     bpms = [
     50         Fraction(MICROSECONDS_PER_MINUTE, segment.microseconds_per_quarter)
     51         for segment in tempo_map.segments
>>   52         # without the > 0 test, a set-tempo of 0 raises ZeroDivisionError
     53         if segment.start_tick < end_tick and segment.microseconds_per_quarter > 0
     54     ]
     55     if not bpms:
     56         return None
     57 
     58     return BpmRange(lowest=min(bpms), highest=max(bpms))
```

### 84. vocabulary.py:65

```python
     57 class KeyMode(Enum):
     58     MAJOR = 0
     59     MINOR = 1
     60 
     61 
     62 @dataclass(frozen=True)
     63 class KeySignature:
     64     tick: Tick
>>   65     sharps: int  # negative for flats
     66     mode: KeyMode
     67 
     68 
     69 TrackEvent = NoteStart | NoteEnd | TempoChange | TimeSignature | KeySignature
     70 
     71 
     72 @dataclass(frozen=True)
     73 class Track:
     74     events: tuple[TrackEvent, ...]
     75     end_tick: Tick  # the end-of-track event, or the last event when the chunk ends without one
```
