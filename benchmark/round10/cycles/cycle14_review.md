# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## P1 payroll (package punchpay): 9 comments

`scratchpad/cycle14/p1/punchpay`

### 1. money.py:17

```python
      9 """
     10 
     11 from __future__ import annotations
     12 
     13 import re
     14 from decimal import Decimal
     15 
     16 
>>   17 # matches:
>>   18 # `18`
>>   19 # `18.5`
>>   20 # `18.50`
>>   21 # rejects:
>>   22 # `18.505`
>>   23 # `.50`
>>   24 # `-18.50`
     25 _AMOUNT_PATTERN = re.compile(r'[0-9]+(?:\.[0-9]{1,2})?')
     26 
     27 
     28 def parseCents(raw_amount: str) -> int | None:
     29     """Return the cents in a decimal amount of at most two places, or None when raw_amount is not one."""
     30     if _AMOUNT_PATTERN.fullmatch(raw_amount) is None:
     31         return None
     32     return int(Decimal(raw_amount) * 100)
     33 
     34 
```

### 2. pay.py:95

```python
     87     punches_by_badge: dict[EmployeeId, list[Punch]] = defaultdict(list)
     88     for punch in known_punches:
     89         punches_by_badge[punch.badge].append(punch)
     90 
     91     shifts: list[_Shift] = []
     92     unpaired: list[Problem] = []
     93     for badge_punches in punches_by_badge.values():
     94         open_in: Punch | None = None
>>   95         # sorted() is stable. Punches at one instant stay in read order
     96         for punch in sorted(badge_punches, key=lambda punch: punch.at):
     97             step = _stepPairing(open_in, punch)
     98             open_in = step.open_in
     99             if step.shift is not None:
    100                 shifts.append(step.shift)
    101             if step.unpaired is not None:
    102                 unpaired.append(step.unpaired)
    103         if open_in is not None:
    104             unpaired.append(_buildProblem(open_in, ProblemKind.UNPAIRED_IN))
    105     return _Pairing(tuple(shifts), tuple(unpaired))
```

### 3. payroll_rules.py:79

```python
     71     for site, timezone_name in raw_site_timezones.items():
     72         if not (isinstance(timezone_name, str) and timezone_name in known_timezones):
     73             raise _rejectRules(rules_path, f'site_timezones: {site!r} has unknown IANA timezone {timezone_name!r}')
     74         site_timezones[SiteName(site)] = pendulum.timezone(timezone_name)
     75     return site_timezones
     76 
     77 
     78 def _parsePositiveMinutes(rules_path: Path, key: str, raw_minutes: object) -> int:
>>   79     # bool subclasses Python int. Reject it too
     80     if not (isinstance(raw_minutes, int) and not isinstance(raw_minutes, bool) and raw_minutes > 0):
     81         raise _rejectRules(rules_path, f'{key}: {raw_minutes!r} (expected a positive integer such as 15)')
     82     return raw_minutes
     83 
     84 
     85 def _parseMultiplier(rules_path: Path, raw_multiplier: object) -> Fraction:
     86     # matches:
     87     # `1.5`
     88     # `2`
     89     # rejects:
```

### 4. payroll_rules.py:86

```python
     78 def _parsePositiveMinutes(rules_path: Path, key: str, raw_minutes: object) -> int:
     79     # bool subclasses Python int. Reject it too
     80     if not (isinstance(raw_minutes, int) and not isinstance(raw_minutes, bool) and raw_minutes > 0):
     81         raise _rejectRules(rules_path, f'{key}: {raw_minutes!r} (expected a positive integer such as 15)')
     82     return raw_minutes
     83 
     84 
     85 def _parseMultiplier(rules_path: Path, raw_multiplier: object) -> Fraction:
>>   86     # matches:
>>   87     # `1.5`
>>   88     # `2`
>>   89     # rejects:
>>   90     # `1.5e0`
>>   91     # `3/2`
     92     MULTIPLIER_PATTERN = re.compile(r'[0-9]+(?:\.[0-9]+)?')
     93     if not (isinstance(raw_multiplier, str) and MULTIPLIER_PATTERN.fullmatch(raw_multiplier)):
     94         raise _rejectRules(
     95             rules_path,
     96             f'overtime_multiplier: {raw_multiplier!r} (expected a decimal string such as "1.5")',
     97         )
     98     return Fraction(raw_multiplier)
     99 
    100 
    101 def _rejectRules(rules_path: Path, reason: str) -> UnusableInputError:
```

### 5. punches.py:90

```python
     82     ):
     83         return Problem(file_name, line, badge, ProblemKind.MALFORMED)
     84     return Punch(file_name, line, badge, at, directions[raw_direction])
     85 
     86 
     87 def _parseInstant(raw_at: str) -> DateTime | None:
     88     """Return the instant in UTC, or None when raw_at is not ISO 8601 with a UTC offset."""
     89     try:
>>   90         # with tz=None, text without a UTC offset parses to a naive DateTime. The default tz would parse it as UTC
     91         parsed = pendulum.parse(raw_at, exact=True, tz=None)
     92     except ValueError:
     93         return None
     94     if not (isinstance(parsed, DateTime) and parsed.tzinfo is not None):
     95         return None
     96     try:
     97         # pendulum.parse() accepts an offset of 24 hours or more. Converting such a DateTime raises ValueError
     98         return parsed.in_timezone('UTC')
     99     except ValueError:
    100         return None
```

### 6. punches.py:97

```python
     89     try:
     90         # with tz=None, text without a UTC offset parses to a naive DateTime. The default tz would parse it as UTC
     91         parsed = pendulum.parse(raw_at, exact=True, tz=None)
     92     except ValueError:
     93         return None
     94     if not (isinstance(parsed, DateTime) and parsed.tzinfo is not None):
     95         return None
     96     try:
>>   97         # pendulum.parse() accepts an offset of 24 hours or more. Converting such a DateTime raises ValueError
     98         return parsed.in_timezone('UTC')
     99     except ValueError:
    100         return None
```

### 7. roster.py:36

```python
     28         UnusableInputError: the file is unreadable, has the wrong header, or has a row with the wrong
     29             field count, an empty or repeated employee_id, an empty name, a malformed hourly_rate, or a
     30             site absent from site_timezones.
     31     """
     32     HEADER = ['employee_id', 'name', 'hourly_rate', 'site']
     33     if not roster_path.is_file():
     34         raise _rejectRoster(str(roster_path), 'file not found')
     35     try:
>>   36         # Excel writes a byte order mark at the start of a CSV file. utf-8-sig drops it
     37         roster_text = roster_path.read_text(encoding='utf-8-sig')
     38     except (OSError, UnicodeDecodeError) as exc:
     39         raise _rejectRoster(str(roster_path), f'unreadable: {exc}') from exc
     40 
     41     reader = csv.reader(io.StringIO(roster_text))
     42     if next(reader, None) != HEADER:
     43         raise _rejectRoster(f'{roster_path}:1', f'expected the header {",".join(HEADER)}')
     44 
     45     employees: dict[EmployeeId, Employee] = {}
     46     for row in reader:
```

### 8. store.py:60

```python
     52             week.regular_minutes,
     53             week.overtime_minutes,
     54             week.gross_pay_cents,
     55         )
     56         for week in weeks
     57     ]
     58     with closing(sqlite3.connect(database_path)) as connection:
     59         connection.execute(CREATE_TABLE)
>>   60         # SQLite skips an upsert whose DO UPDATE WHERE is false. A skipped row is not in total_changes
     61         changes_before = connection.total_changes
     62         connection.executemany(UPSERT, rows)
     63         connection.commit()
     64         return connection.total_changes - changes_before
     65 
     66 
     67 ### vocabulary #########################################################################
     68 
     69 
     70 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
```

### 9. store.py:70

```python
     62         connection.executemany(UPSERT, rows)
     63         connection.commit()
     64         return connection.total_changes - changes_before
     65 
     66 
     67 ### vocabulary #########################################################################
     68 
     69 
>>   70 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     71 class _EmployeeWeekRow(NamedTuple):
     72     employee_id: str
     73     week_start: str
     74     regular_minutes: int
     75     overtime_minutes: int
     76     gross_pay_cents: int
```

## P2 invoices (package invoicing): 15 comments

`scratchpad/cycle14/p2/invoicing`

### 10. billing.py:40

```python
     32             unusable.
     33     """
     34     config = run_config.readRunConfig(input_dir, raw_month, prices_path)
     35     batch = events.readEvents(input_dir, config)
     36     unique_events = _dropDuplicates(batch.events)
     37 
     38     invoices: list[Invoice] = []
     39     problems = list(batch.problems)
>>   40     # sorted() is stable. A tie on instant is broken by read order
     41     by_customer = sorted(unique_events, key=lambda event: (event.customer_id, event.at))
     42     for customer_id, customer_events in itertools.groupby(by_customer, key=lambda event: event.customer_id):
     43         customer_replay = replay.replaySubscription(customer_events)
     44         problems.extend(
     45             Problem(event.source, customer_id, ProblemKind.OUT_OF_ORDER) for event in customer_replay.skipped
     46         )
     47         invoice = pricing.priceInvoice(config.customers[customer_id], customer_replay.stretches, config)
     48         if invoice is not None:
     49             invoices.append(invoice)
     50 
```

### 11. billing.py:62

```python
     54         invoices=tuple(invoices),
     55         problems=tuple(sorted(problems, key=lambda problem: problem.source)),
     56         event_line_count=batch.line_count,
     57         duplicate_count=len(batch.events) - len(unique_events),
     58     )
     59 
     60 
     61 def _dropDuplicates(events_read: Iterable[Event]) -> list[Event]:
>>   62     # An exporter that times out sends its events again. The first copy in read order is kept.
>>   63     # DateTime equality compares instants, so a copy with another UTC offset is a duplicate too.
     64     seen: set[tuple[CustomerId, DateTime, Action]] = set()
     65     unique_events: list[Event] = []
     66     for event in events_read:
     67         identity = (event.customer_id, event.at, event.action)
     68         if identity not in seen:
     69             seen.add(identity)
     70             unique_events.append(event)
     71 
     72     return unique_events
```

### 12. events.py:55

```python
     47     """
     48     events: list[Event] = []
     49     problems: list[Problem] = []
     50     line_count = 0
     51     for events_path in sorted(input_dir.glob(_EVENTS_GLOB), key=lambda path: path.name):
     52         if not events_path.is_file():
     53             continue
     54 
>>   55         # Here bytes.splitlines() is used. The alternative, str.splitlines(), would also split at
>>   56         # U+2028 inside a JSON string.
     57         lines = _readEventFile(events_path).splitlines()
     58         line_count += len(lines)
     59         for number, line_bytes in enumerate(lines, start=1):
     60             outcome = _classifyLine(line_bytes, SourceLine(events_path.name, number), config)
     61             if isinstance(outcome, Event):
     62                 events.append(outcome)
     63             else:
     64                 problems.append(outcome)
     65 
     66     return EventBatch(events=tuple(events), problems=tuple(problems), line_count=line_count)
```

### 13. events.py:110

```python
    102         decoded = json.loads(line_bytes)
    103     except (json.JSONDecodeError, UnicodeDecodeError):
    104         return None
    105 
    106     return decoded if isinstance(decoded, dict) else None
    107 
    108 
    109 def _parseInstant(raw_at: str) -> DateTime | None:
>>  110     # with tz=None, parse() leaves a time with no UTC offset naive. The default, tz=UTC, would make it UTC
    111     try:
    112         at = pendulum.parse(raw_at, tz=None)
    113     except ValueError:
    114         return None
    115 
    116     return at if isinstance(at, DateTime) and at.tzinfo is not None else None
    117 
    118 
    119 def _parseAction(raw_event: str, fields: Mapping[str, object]) -> Action | None:
    120     raw_plan = fields.get('plan')
```

### 14. glossary.py:91

```python
     83     UNKNOWN_CUSTOMER = 'unknown customer'
     84     UNKNOWN_PLAN = 'unknown plan'
     85     OUT_OF_ORDER = 'out of order'
     86 
     87 
     88 @dataclass(frozen=True)
     89 class Problem:
     90     source: SourceLine
>>   91     # None when a malformed line has no string in its customer field
     92     customer: str | None
     93     kind: ProblemKind
     94 
     95 
     96 @dataclass(frozen=True)
     97 class EventBatch:
     98     events: tuple[Event, ...]
     99     problems: tuple[Problem, ...]
    100     line_count: int
    101 
```

### 15. glossary.py:107

```python
     99     problems: tuple[Problem, ...]
    100     line_count: int
    101 
    102 
    103 @dataclass(frozen=True)
    104 class Stretch:
    105     plan: PlanName
    106     start: DateTime
>>  107     # None when the plan is still active after the customer's last event
    108     end: DateTime | None
    109 
    110 
    111 @dataclass(frozen=True)
    112 class Replay:
    113     stretches: tuple[Stretch, ...]
    114     skipped: tuple[Event, ...]
    115 
    116 
    117 @dataclass(frozen=True)
```

### 16. ledger.py:43

```python
     35     )
     36     DELETE = 'DELETE FROM invoices WHERE customer_id = ? AND month = ?'
     37 
     38     month = billing.month.label
     39     rows = [_buildInvoiceRow(invoice, month) for invoice in billing.invoices]
     40     invoiced = {invoice.customer_id for invoice in billing.invoices}
     41     unbilled = [(customer_id, month) for customer_id in billing.customer_ids if customer_id not in invoiced]
     42 
>>   43     # closing() closes the connection. The inner `with connection` commits, or rolls back on an exception
     44     with closing(sqlite3.connect(database_path)) as connection, connection:
     45         connection.execute(CREATE_TABLE)
     46         connection.executemany(UPSERT, rows)
     47         connection.executemany(DELETE, unbilled)
     48 
     49 
     50 def _buildInvoiceRow(invoice: Invoice, month: str) -> _InvoiceRow:
     51     lines = [
     52         {
     53             'plan': line.plan,
```

### 17. ledger.py:73

```python
     65         total_cents=invoice.total_cents,
     66         lines_json=json.dumps(lines, ensure_ascii=False),
     67     )
     68 
     69 
     70 ### vocabulary #########################################################################
     71 
     72 
>>   73 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     74 class _InvoiceRow(NamedTuple):
     75     customer_id: str
     76     month: str
     77     subtotal_cents: int
     78     tax_cents: int
     79     total_cents: int
     80     lines_json: str
```

### 18. pricing.py:28

```python
     20 def priceInvoice(customer: Customer, stretches: Iterable[Stretch], config: RunConfig) -> Invoice | None:
     21     """Price the part of each stretch inside the month, then add the customer's tax.
     22 
     23     Returns:
     24         None when no stretch overlaps the month.
     25     """
     26     month_start = pendulum.datetime(config.month.year, config.month.month, 1, tz=customer.timezone)
     27     month_end = month_start.add(months=1)
>>   28     # A month with a daylight saving change is an hour off its days times 24 hours.
>>   29     # Prorate by the elapsed time between the two instants.
     30     month_length = _elapsedMicroseconds(month_start, month_end)
     31 
     32     lines: list[InvoiceLine] = []
     33     for stretch in stretches:
     34         start = max(stretch.start, month_start)
     35         end = month_end if stretch.end is None else min(stretch.end, month_end)
     36         if end <= start:
     37             continue
     38 
     39         price_cents = config.plan_prices[stretch.plan]
```

### 19. pricing.py:53

```python
     45         return None
     46 
     47     subtotal_cents = sum(line.amount_cents for line in lines)
     48     tax_cents = int((subtotal_cents * customer.tax_rate).to_integral_value(rounding=ROUND_HALF_UP))
     49     return Invoice(customer.customer_id, customer.name, tuple(lines), Cents(subtotal_cents), Cents(tax_cents))
     50 
     51 
     52 def _elapsedMicroseconds(start: DateTime, end: DateTime) -> int:
>>   53     # exact integer, where total_seconds() returns a float
     54     return (end.int_timestamp - start.int_timestamp) * 1_000_000 + end.microsecond - start.microsecond
     55 
     56 
     57 def _divideRoundingHalfUp(numerator: int, denominator: int) -> int:
     58     return (2 * numerator + denominator) // (2 * denominator)
```

### 20. run_config.py:54

```python
     46         raise _rejectConfig(str(input_dir), 'not a directory')
     47 
     48     prices = _readPrices(input_dir / _PRICES_NAME if prices_path is None else prices_path)
     49     customers = _readCustomers(input_dir / _CUSTOMERS_NAME, prices.tax_rates)
     50     return RunConfig(month=month, customers=customers, plan_prices=prices.plan_prices)
     51 
     52 
     53 def _parseMonth(raw_month: str) -> BillingMonth:
>>   54     # matches:
>>   55     # `2028-03`
>>   56     # rejects:
>>   57     # `2028-3`
     58     month_match = re.fullmatch(r'([0-9]{4})-([0-9]{2})', raw_month)
     59     if not (month_match and 1 <= int(month_match[2]) <= 12):
     60         raise _rejectConfig('month', f'{raw_month!r} is malformed (expected YYYY-MM, such as "2028-03")')
     61 
     62     return BillingMonth(year=int(month_match[1]), month=int(month_match[2]))
     63 
     64 
     65 def _readPrices(prices_path: Path) -> _PriceList:
     66     """Read the plan prices and the tax rates of each state.
     67 
```

### 21. run_config.py:72

```python
     64 
     65 def _readPrices(prices_path: Path) -> _PriceList:
     66     """Read the plan prices and the tax rates of each state.
     67 
     68     Raises:
     69         UnusableInputError: the file is unreadable, is not JSON, lacks either object, or has a
     70             malformed price or rate.
     71     """
>>   72     # matches:
>>   73     # `29.00`
>>   74     # rejects:
>>   75     # `29.0`
     76     PRICE_PATTERN = re.compile(r'[0-9]+\.[0-9]{2}')
     77     # matches:
     78     # `0.08875`
     79     # `0`
     80     # rejects:
     81     # `.08`
     82     RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]+)?')
     83 
     84     document = _readJsonFile(prices_path)
     85     raw_plans = document.get('plans') if isinstance(document, dict) else None
```

### 22. run_config.py:77

```python
     69         UnusableInputError: the file is unreadable, is not JSON, lacks either object, or has a
     70             malformed price or rate.
     71     """
     72     # matches:
     73     # `29.00`
     74     # rejects:
     75     # `29.0`
     76     PRICE_PATTERN = re.compile(r'[0-9]+\.[0-9]{2}')
>>   77     # matches:
>>   78     # `0.08875`
>>   79     # `0`
>>   80     # rejects:
>>   81     # `.08`
     82     RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]+)?')
     83 
     84     document = _readJsonFile(prices_path)
     85     raw_plans = document.get('plans') if isinstance(document, dict) else None
     86     raw_rates = document.get('tax_rates') if isinstance(document, dict) else None
     87     if not (isinstance(raw_plans, dict) and isinstance(raw_rates, dict)):
     88         raise _rejectConfig(str(prices_path), 'malformed (expected an object with "plans" and "tax_rates" objects)')
     89 
     90     plan_prices: dict[PlanName, Cents] = {}
     91     for plan, raw_price in raw_plans.items():
```

### 23. run_config.py:160

```python
    152 
    153     return customers
    154 
    155 
    156 def _readCsvRows(csv_path: Path) -> list[list[str]]:
    157     if not csv_path.is_file():
    158         raise _rejectConfig(str(csv_path), 'no such file')
    159 
>>  160     # Here read_bytes() is used. The alternative, read_text(), would turn \r\n and \r into \n, even
>>  161     # inside a quoted CSV field.
    162     try:
    163         csv_bytes = csv_path.read_bytes()
    164     except OSError as exc:
    165         raise _rejectConfig(str(csv_path), f'unreadable ({exc.strerror})') from exc
    166 
    167     # spreadsheet exports often begin with a byte order mark. utf-8-sig drops one if present
    168     try:
    169         csv_text = csv_bytes.decode('utf-8-sig')
    170     except UnicodeDecodeError as exc:
    171         raise _rejectConfig(str(csv_path), 'not UTF-8 text') from exc
```

### 24. run_config.py:167

```python
    159 
    160     # Here read_bytes() is used. The alternative, read_text(), would turn \r\n and \r into \n, even
    161     # inside a quoted CSV field.
    162     try:
    163         csv_bytes = csv_path.read_bytes()
    164     except OSError as exc:
    165         raise _rejectConfig(str(csv_path), f'unreadable ({exc.strerror})') from exc
    166 
>>  167     # spreadsheet exports often begin with a byte order mark. utf-8-sig drops one if present
    168     try:
    169         csv_text = csv_bytes.decode('utf-8-sig')
    170     except UnicodeDecodeError as exc:
    171         raise _rejectConfig(str(csv_path), 'not UTF-8 text') from exc
    172 
    173     try:
    174         return list(csv.reader(io.StringIO(csv_text, newline='')))
    175     except csv.Error as exc:
    176         raise _rejectConfig(str(csv_path), f'not CSV ({exc})') from exc
    177 
```

## P3 snapshot pruner (package snapshot_pruner): 8 comments

`scratchpad/cycle14/p3/snapshot_pruner`

### 25. history.py:98

```python
     90         yield _DecisionRow(run_id, deleted.file, 'delete', deleted.local.isoformat(), None)
     91     for problem in plan.problems:
     92         yield _DecisionRow(run_id, problem.file, problem.kind.value, None, None)
     93 
     94 
     95 ### vocabulary #########################################################################
     96 
     97 
>>   98 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     99 class _DecisionRow(NamedTuple):
    100     run_id: int
    101     file: str
    102     decision: str
    103     local: str | None
    104     rules: str | None  # space-separated
```

### 26. history.py:104

```python
     96 
     97 
     98 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     99 class _DecisionRow(NamedTuple):
    100     run_id: int
    101     file: str
    102     decision: str
    103     local: str | None
>>  104     rules: str | None  # space-separated
```

### 27. policy.py:65

```python
     57 
     58 def _parseKeepCounts(policy_json_path: Path, raw_keep: object) -> KeepCounts:
     59     expected_keys = {period.value for period in Period}
     60     if not (isinstance(raw_keep, dict) and set(raw_keep) == expected_keys):
     61         detail = f'"keep" must be an object with exactly the keys {sorted(expected_keys)}'
     62         raise _rejectPolicy(policy_json_path, detail)
     63 
     64     for key, raw_count in raw_keep.items():
>>   65         # bool subclasses Python int. Reject it too
     66         if not (isinstance(raw_count, int) and not isinstance(raw_count, bool) and raw_count >= 0):
     67             raise _rejectPolicy(policy_json_path, f'"keep.{key}" is {raw_count!r} (expected an integer >= 0)')
     68 
     69     return KeepCounts(
     70         hourly=raw_keep['hourly'],
     71         daily=raw_keep['daily'],
     72         weekly=raw_keep['weekly'],
     73         monthly=raw_keep['monthly'],
     74     )
     75 
```

### 28. retention.py:77

```python
     69         case Period.WEEKLY:
     70             return keep.weekly
     71         case Period.MONTHLY:
     72             return keep.monthly
     73 
     74 
     75 ### vocabulary #########################################################################
     76 
>>   77 # fields run from the largest unit to the smallest, so the keys of one period sort chronologically
     78 _PeriodKey = tuple[int, ...]
```

### 29. snapshot_directory.py:24

```python
     16 from pathlib import Path
     17 
     18 import pendulum
     19 from pendulum import DateTime
     20 
     21 from snapshot_pruner.vocabulary import DirectoryListing, Problem, ProblemKind, Snapshot, SnapshotDirectoryError
     22 
     23 
>>   24 # matches:
>>   25 # `db-20281105T073000Z.tar.zst`
>>   26 # `db-20281131T000000Z.tar.zst`
>>   27 # rejects:
>>   28 # `db-20281105T0730Z.tar.zst`
>>   29 # `db-latest.tar.zst`
     30 _SNAPSHOT_NAME = re.compile(r'db-(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z\.tar\.zst', re.ASCII)
     31 
     32 _LOG = logging.getLogger(__name__)
     33 
     34 
     35 def listSnapshotDirectory(snapshot_dir: Path, now: DateTime) -> DirectoryListing:
     36     """Sort every entry of `snapshot_dir` into snapshots, problems and ignored names.
     37 
     38     Raises:
     39         SnapshotDirectoryError: `snapshot_dir` is not a directory, or cannot be listed.
```

### 30. vocabulary.py:40

```python
     32 class Policy:
     33     timezone: Timezone
     34     keep: KeepCounts
     35 
     36 
     37 @dataclass(frozen=True)
     38 class Snapshot:
     39     file: str
>>   40     at: DateTime  # UTC, from the file name
     41 
     42 
     43 @dataclass(frozen=True)
     44 class Problem:
     45     file: str
     46     kind: ProblemKind
     47 
     48 
     49 @dataclass(frozen=True)
     50 class DirectoryListing:
```

### 31. vocabulary.py:83

```python
     75 @dataclass(frozen=True)
     76 class Plan:
     77     """The decision for every entry of one snapshot directory.
     78 
     79     `keep` and `delete` sort newest first. `problems` and `ignored` sort by file name. `ignored` lists
     80     the entries that are not snapshots: other names, subdirectories and symbolic links.
     81     """
     82 
>>   83     now: DateTime  # UTC
     84     snapshot_dir: str  # as the caller passed it
     85     policy: Policy
     86     applied: bool
     87     keep: tuple[KeptSnapshot, ...]
     88     delete: tuple[DeletedSnapshot, ...]
     89     problems: tuple[Problem, ...]
     90     ignored: tuple[str, ...]
     91 
     92 
     93 @dataclass(frozen=True)
```

### 32. vocabulary.py:84

```python
     76 class Plan:
     77     """The decision for every entry of one snapshot directory.
     78 
     79     `keep` and `delete` sort newest first. `problems` and `ignored` sort by file name. `ignored` lists
     80     the entries that are not snapshots: other names, subdirectories and symbolic links.
     81     """
     82 
     83     now: DateTime  # UTC
>>   84     snapshot_dir: str  # as the caller passed it
     85     policy: Policy
     86     applied: bool
     87     keep: tuple[KeptSnapshot, ...]
     88     delete: tuple[DeletedSnapshot, ...]
     89     problems: tuple[Problem, ...]
     90     ignored: tuple[str, ...]
     91 
     92 
     93 @dataclass(frozen=True)
     94 class DeletionFailure:
```

## P4 license audit (package license_audit): 13 comments

`scratchpad/cycle14/p4/license_audit`

### 33. calendar_date.py:12

```python
      4 
      5 import re
      6 
      7 import pendulum
      8 
      9 
     10 def parseCalendarDate(raw_date: str) -> pendulum.Date | None:
     11     """Return None when raw_date is not a real date in the form YYYY-MM-DD."""
>>   12     # matches:
>>   13     # `2028-06-30`
>>   14     # rejects:
>>   15     # `2028-6-30`
>>   16     # `20280630`
     17     ISO_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
     18     # date.fromisoformat() accepts `20280630` too. Check the form first
     19     if not ISO_DATE.fullmatch(raw_date):
     20         return None
     21 
     22     try:
     23         return pendulum.Date.fromisoformat(raw_date)
     24     except ValueError:
     25         # a date that does not exist, such as 2028-02-30
     26         return None
```

### 34. calendar_date.py:18

```python
     10 def parseCalendarDate(raw_date: str) -> pendulum.Date | None:
     11     """Return None when raw_date is not a real date in the form YYYY-MM-DD."""
     12     # matches:
     13     # `2028-06-30`
     14     # rejects:
     15     # `2028-6-30`
     16     # `20280630`
     17     ISO_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
>>   18     # date.fromisoformat() accepts `20280630` too. Check the form first
     19     if not ISO_DATE.fullmatch(raw_date):
     20         return None
     21 
     22     try:
     23         return pendulum.Date.fromisoformat(raw_date)
     24     except ValueError:
     25         # a date that does not exist, such as 2028-02-30
     26         return None
```

### 35. calendar_date.py:25

```python
     17     ISO_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
     18     # date.fromisoformat() accepts `20280630` too. Check the form first
     19     if not ISO_DATE.fullmatch(raw_date):
     20         return None
     21 
     22     try:
     23         return pendulum.Date.fromisoformat(raw_date)
     24     except ValueError:
>>   25         # a date that does not exist, such as 2028-02-30
     26         return None
```

### 36. input_file.py:43

```python
     35     json_text = readInputText(json_path)
     36     try:
     37         return json.loads(json_text)
     38     except json.JSONDecodeError as exc:
     39         raise rejectInputFile(json_path, f'not JSON: {exc}') from exc
     40 
     41 
     42 def rejectInputFile(input_path: Path, problem: str) -> UnusableInputError:
>>   43     # stacklevel=2 sets the location in the record to the caller, the raise site
     44     _LOG.error('input.rejected', extra={'path': str(input_path), 'problem': problem}, stacklevel=2)
     45     return UnusableInputError(f'{input_path}: {problem}')
```

### 37. license_expression.py:19

```python
     11 
     12 import re
     13 from collections import deque
     14 from collections.abc import Callable
     15 
     16 from license_audit.vocabulary import AllOf, AnyOf, LicenseExpression, LicenseKey, LicenseRef, MalformedExpressionError
     17 
     18 
>>   19 # matches:
>>   20 # `Apache-2.0`
>>   21 # `GPL-2.0+`
>>   22 # `LicenseRef-acme:internal`
>>   23 # rejects:
>>   24 # `MIT,`
     25 _LICENSE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9.+:-]*')
     26 _TOKEN = re.compile(r'[()]|[^\s()]+')
     27 _OPERATORS_LOOSEST_FIRST = (('OR', AnyOf), ('AND', AllOf))
     28 
     29 
     30 def parseLicenseExpression(expression_text: str) -> LicenseExpression:
     31     """Parse expression_text into a tree of AnyOf, AllOf and LicenseRef.
     32 
     33     Raises:
     34         MalformedExpressionError: expression_text is not a license expression.
```

### 38. license_expression.py:62

```python
     54             return usable(expression.key)
     55         case AllOf():
     56             return all(satisfiableWith(operand, usable) for operand in expression.operands)
     57         case AnyOf():
     58             return any(satisfiableWith(operand, usable) for operand in expression.operands)
     59 
     60 
     61 def _parseOperatorLevel(tokens: deque[str], level: int) -> LicenseExpression:
>>   62     # level indexes _OPERATORS_LOOSEST_FIRST. Past its end, the next token starts one operand
     63     if level == len(_OPERATORS_LOOSEST_FIRST):
     64         return _parseOperand(tokens)
     65 
     66     operator, combine = _OPERATORS_LOOSEST_FIRST[level]
     67     operands = [_parseOperatorLevel(tokens, level + 1)]
     68     while tokens and tokens[0] == operator:
     69         tokens.popleft()
     70         operands.append(_parseOperatorLevel(tokens, level + 1))
     71     return operands[0] if len(operands) == 1 else combine(tuple(operands))
     72 
```

### 39. lock_file.py:23

```python
     15 import re
     16 from pathlib import Path
     17 
     18 from license_audit import input_file
     19 from license_audit.package_name import normalizePackageName
     20 from license_audit.vocabulary import LockFileContents, MalformedLine, Pin, Version
     21 
     22 
>>   23 # name, `==`, version, then an optional marker and an optional comment
>>   24 # matches:
>>   25 # `Requests==2.31.0`
>>   26 # `psycopg2==2.9.9 ; sys_platform != "win32"  # binary wheel on CI`
>>   27 # rejects:
>>   28 # `celery>=5`
>>   29 # `redis==7.4.0#no space before the comment`
     30 _PIN_LINE = re.compile(
     31     r'(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*==\s*(?P<version>[^\s;#]+)'
     32     r'\s*(?:;\s*[^\s#][^#]*)?(?:\s#.*)?',
     33 )
     34 
     35 
     36 def readLockFile(lock_path: Path) -> LockFileContents:
     37     """Read the pins and malformed lines of lock_path, in line order.
     38 
     39     Raises:
```

### 40. verdict_store.py:77

```python
     69     except sqlite3.Error as exc:
     70         _LOG.error('database.unusable', extra={'database': str(database_path), 'problem': str(exc)})
     71         raise VerdictStoreError(f'{database_path}: {exc}') from exc
     72 
     73 
     74 ### vocabulary #########################################################################
     75 
     76 
>>   77 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     78 class _VerdictRow(NamedTuple):
     79     input_dir: str
     80     audit_date: str
     81     lock: str
     82     line: int
     83     package: str
     84     version: str
     85     license: str | None
     86     verdict: str
```

### 41. vocabulary.py:13

```python
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from pathlib import Path
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
>>   13 PackageName = NewType('PackageName', str)  # after PEP 503 normalisation
     14 Version = NewType('Version', str)
     15 LicenseKey = NewType('LicenseKey', str)  # a license id, casefolded for comparison
     16 
     17 
     18 @dataclass(frozen=True)
     19 class LicenseRef:
     20     key: LicenseKey
     21 
     22 
     23 @dataclass(frozen=True)
```

### 42. vocabulary.py:15

```python
      7 from pathlib import Path
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
     13 PackageName = NewType('PackageName', str)  # after PEP 503 normalisation
     14 Version = NewType('Version', str)
>>   15 LicenseKey = NewType('LicenseKey', str)  # a license id, casefolded for comparison
     16 
     17 
     18 @dataclass(frozen=True)
     19 class LicenseRef:
     20     key: LicenseKey
     21 
     22 
     23 @dataclass(frozen=True)
     24 class AllOf:
     25     """Operands joined by AND."""
```

### 43. vocabulary.py:42

```python
     34     operands: tuple[LicenseExpression, ...]
     35 
     36 
     37 LicenseExpression: TypeAlias = LicenseRef | AllOf | AnyOf
     38 
     39 
     40 @dataclass(frozen=True)
     41 class DeclaredLicense:
>>   42     text: str  # as written in licenses.json
     43     expression: LicenseExpression
     44 
     45 
     46 @dataclass(frozen=True)
     47 class Release:
     48     package: PackageName
     49     version: Version
     50 
     51 
     52 @dataclass(frozen=True)
```

### 44. vocabulary.py:56

```python
     48     package: PackageName
     49     version: Version
     50 
     51 
     52 @dataclass(frozen=True)
     53 class Pin:
     54     """One `name==version` line of a lock file."""
     55 
>>   56     lock: str  # file name of the lock file
     57     line: int
     58     package: PackageName
     59     version: Version
     60 
     61 
     62 @dataclass(frozen=True)
     63 class MalformedLine:
     64     lock: str
     65     line: int
     66     text: str
```

### 45. vocabulary.py:104

```python
     96     DENIED = 'denied'
     97     UNREVIEWED = 'unreviewed'
     98     UNKNOWN_LICENSE = 'unknown license'
     99 
    100 
    101 @dataclass(frozen=True)
    102 class AuditEntry:
    103     pin: Pin
>>  104     license_text: str | None  # None when licenses.json has no expression for the release
    105     verdict: Verdict
    106 
    107 
    108 @dataclass(frozen=True)
    109 class VerdictTotals:
    110     entries: int
    111     allowed: int
    112     denied: int
    113     unreviewed: int
    114     unknown: int
```

## P5 config audit (package layer_audit): 13 comments

`scratchpad/cycle14/p5/layer_audit`

### 46. loading.py:116

```python
    108     return {key: _convertValue(raw_value, toml_path) for key, raw_value in raw_table.items()}
    109 
    110 
    111 def _convertValue(raw_value: object, toml_path: Path) -> TomlValue:
    112     if isinstance(raw_value, dict):
    113         return {key: _convertValue(item, toml_path) for key, item in raw_value.items()}
    114     if isinstance(raw_value, list):
    115         return [_convertValue(item, toml_path) for item in raw_value]
>>  116     # TOML local datetimes and times have no UTC offset. tz=None leaves them without one
    117     if isinstance(raw_value, (datetime, date, time)):
    118         return pendulum.instance(raw_value, tz=None)
    119     if isinstance(raw_value, (str, int, float)):
    120         return raw_value
    121     raise _rejectInput(toml_path, f'tomllib returned an unsupported {type(raw_value).__name__} value')
    122 
    123 
    124 def _parseVersion(raw_version: object, toml_path: Path, key: str) -> Version:
    125     # matches:
    126     # `1.10.0`
```

### 47. loading.py:125

```python
    117     if isinstance(raw_value, (datetime, date, time)):
    118         return pendulum.instance(raw_value, tz=None)
    119     if isinstance(raw_value, (str, int, float)):
    120         return raw_value
    121     raise _rejectInput(toml_path, f'tomllib returned an unsupported {type(raw_value).__name__} value')
    122 
    123 
    124 def _parseVersion(raw_version: object, toml_path: Path, key: str) -> Version:
>>  125     # matches:
>>  126     # `1.10.0`
>>  127     # rejects:
>>  128     # `1.10`
>>  129     # `v1.10.0`
    130     VERSION = re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)')
    131 
    132     version_match = VERSION.fullmatch(raw_version) if isinstance(raw_version, str) else None
    133     if version_match is None:
    134         raise _rejectInput(toml_path, f'{key} {raw_version!r} is not a version (expected MAJOR.MINOR.PATCH, "1.10.0")')
    135     major, minor, patch = (int(number) for number in version_match.groups())
    136     return Version(major, minor, patch)
    137 
    138 
    139 def _parseEnvironments(raw_environments: object, layers_path: Path) -> tuple[EnvironmentPlan, ...]:
```

### 48. loading.py:140

```python
    132     version_match = VERSION.fullmatch(raw_version) if isinstance(raw_version, str) else None
    133     if version_match is None:
    134         raise _rejectInput(toml_path, f'{key} {raw_version!r} is not a version (expected MAJOR.MINOR.PATCH, "1.10.0")')
    135     major, minor, patch = (int(number) for number in version_match.groups())
    136     return Version(major, minor, patch)
    137 
    138 
    139 def _parseEnvironments(raw_environments: object, layers_path: Path) -> tuple[EnvironmentPlan, ...]:
>>  140     # matches:
>>  141     # `base`
>>  142     # `eu-west_2`
>>  143     # rejects:
>>  144     # `../base`
    145     LAYER_NAME = re.compile(r'[A-Za-z0-9_-]+')
    146 
    147     if not isinstance(raw_environments, dict):
    148         raise _rejectInput(
    149             layers_path,
    150             'environments must be a table (expected [environments] prod = ["base", "prod"])',
    151         )
    152     environments: list[EnvironmentPlan] = []
    153     for name, raw_layers in raw_environments.items():
    154         valid_layers = isinstance(raw_layers, list) and all(
```

### 49. merging.py:63

```python
     55                 continue
     56 
     57             if earlier is not None:
     58                 earlier_type = TomlType.classifyValue(earlier)
     59                 value_type = TomlType.classifyValue(value)
     60                 if earlier_type != value_type:
     61                     detail = f'{earlier_type.value} in {self.origins[path]}, {value_type.value} in {layer}'
     62                     self.type_changes.append(Finding(FindingKind.TYPE_CHANGE, path, layer, detail))
>>   63             # A later layer merges into this value in place, and every environment reads the same layer
>>   64             # table. Copy the value.
     65             merged[key] = copy.deepcopy(value)
     66             self.recordOrigins(path, value, layer=layer)
     67 
     68     def recordOrigins(self, path: KeyPath, value: TomlValue, *, layer: LayerName) -> None:
     69         self.origins[path] = layer
     70         if isinstance(value, dict):
     71             for key, item in value.items():
     72                 self.recordOrigins(path.child(key), item, layer=layer)
```

### 50. report.py:38

```python
     30 def formatSummary(audit: Audit) -> list[str]:
     31     rows: list[tuple[str, ...]] = []
     32     for environment in audit.environments:
     33         for finding in environment.findings:
     34             severity = finding.kind.severity.value
     35             rows.append(
     36                 (environment.name, severity, finding.kind.value, str(finding.path), finding.layer, finding.detail),
     37             )
>>   38     # every column but the last, the detail, is padded to its widest cell
     39     widths = [max((len(row[column]) for row in rows), default=0) for column in range(5)]
     40     lines = [
     41         '  '.join([*(cell.ljust(width) for cell, width in zip(row[:-1], widths, strict=True)), row[-1]]) for row in rows
     42     ]
     43 
     44     errors = countFindings(audit, Severity.ERROR)
     45     warnings = countFindings(audit, Severity.WARNING)
     46     lines.append(f'{len(audit.environments)} environments, {errors} errors, {warnings} warnings')
     47     return lines
     48 
```

### 51. rules.py:117

```python
    109 
    110         if len(shares) == len(arms) and sum(shares) != PERCENT_MAX:
    111             detail = f'arm shares sum to {sum(shares)}, expected {PERCENT_MAX}'
    112             findings.append(_reportBadRollout(merged, arms_path, detail))
    113     return findings
    114 
    115 
    116 def _describePercentProblem(value: TomlValue) -> str | None:
>>  117     # bool subclasses Python int. Reject it too
    118     if isinstance(value, bool) or not isinstance(value, int):
    119         value_type = TomlType.classifyValue(value)
    120         return f'is a {value_type.value}, expected an integer from {PERCENT_MIN} to {PERCENT_MAX}'
    121     if not PERCENT_MIN <= value <= PERCENT_MAX:
    122         return f'{value} is outside {PERCENT_MIN} to {PERCENT_MAX}'
    123     return None
    124 
    125 
    126 def _reportBadRollout(merged: MergedEnvironment, path: KeyPath, detail: str) -> Finding:
    127     return Finding(FindingKind.BAD_ROLLOUT, path, merged.origins[path], detail)
```

### 52. vocabulary.py:18

```python
     10 from typing import NewType, TypeAlias
     11 
     12 from pendulum import Date, DateTime, Time
     13 
     14 
     15 LayerName = NewType('LayerName', str)
     16 EnvironmentName = NewType('EnvironmentName', str)
     17 
>>   18 # tomllib's value types, with pendulum types in place of datetime, date and time
     19 TomlValue: TypeAlias = 'str | int | float | bool | DateTime | Date | Time | list[TomlValue] | dict[str, TomlValue]'
     20 TomlTable: TypeAlias = 'dict[str, TomlValue]'
     21 
     22 
     23 class TomlType(Enum):
     24     STRING = 'string'
     25     INTEGER = 'integer'
     26     FLOAT = 'float'
     27     BOOLEAN = 'boolean'
     28     DATETIME = 'datetime'
```

### 53. vocabulary.py:36

```python
     28     DATETIME = 'datetime'
     29     DATE = 'date'
     30     TIME = 'time'
     31     ARRAY = 'array'
     32     TABLE = 'table'
     33 
     34     @classmethod
     35     def classifyValue(cls, value: TomlValue) -> TomlType:
>>   36         # bool subclasses Python int. Test it first
     37         if isinstance(value, bool):
     38             return cls.BOOLEAN
     39         if isinstance(value, int):
     40             return cls.INTEGER
     41         if isinstance(value, float):
     42             return cls.FLOAT
     43         if isinstance(value, str):
     44             return cls.STRING
     45         # DateTime subclasses Date. Test it first
     46         if isinstance(value, DateTime):
```

### 54. vocabulary.py:45

```python
     37         if isinstance(value, bool):
     38             return cls.BOOLEAN
     39         if isinstance(value, int):
     40             return cls.INTEGER
     41         if isinstance(value, float):
     42             return cls.FLOAT
     43         if isinstance(value, str):
     44             return cls.STRING
>>   45         # DateTime subclasses Date. Test it first
     46         if isinstance(value, DateTime):
     47             return cls.DATETIME
     48         if isinstance(value, Date):
     49             return cls.DATE
     50         if isinstance(value, Time):
     51             return cls.TIME
     52         if isinstance(value, list):
     53             return cls.ARRAY
     54         return cls.TABLE
     55 
```

### 55. vocabulary.py:69

```python
     61     def child(self, key: str) -> KeyPath:
     62         return KeyPath((*self.segments, key))
     63 
     64     @property
     65     def last(self) -> str:
     66         return self.segments[-1]
     67 
     68     def __str__(self) -> str:
>>   69         # matches:
>>   70         # `search_v2`
>>   71         # `db-host`
>>   72         # rejects:
>>   73         # `x.y`
     74         BARE_KEY = re.compile(r'[A-Za-z0-9_-]+')
     75         # a key outside the bare-key characters is written as a TOML basic string, as in `a."x.y"`
     76         return '.'.join(key if BARE_KEY.fullmatch(key) else json.dumps(key) for key in self.segments)
     77 
     78 
     79 @dataclass(frozen=True, order=True)
     80 class Version:
     81     major: int
     82     minor: int
     83     patch: int
```

### 56. vocabulary.py:75

```python
     67 
     68     def __str__(self) -> str:
     69         # matches:
     70         # `search_v2`
     71         # `db-host`
     72         # rejects:
     73         # `x.y`
     74         BARE_KEY = re.compile(r'[A-Za-z0-9_-]+')
>>   75         # a key outside the bare-key characters is written as a TOML basic string, as in `a."x.y"`
     76         return '.'.join(key if BARE_KEY.fullmatch(key) else json.dumps(key) for key in self.segments)
     77 
     78 
     79 @dataclass(frozen=True, order=True)
     80 class Version:
     81     major: int
     82     minor: int
     83     patch: int
     84 
     85     def __str__(self) -> str:
```

### 57. vocabulary.py:141

```python
    133             case FindingKind.BAD_ROLLOUT:
    134                 return Severity.ERROR
    135 
    136 
    137 @dataclass(frozen=True)
    138 class Finding:
    139     kind: FindingKind
    140     path: KeyPath
>>  141     # the last layer to set a key at or below path
    142     layer: LayerName
    143     detail: str
    144 
    145 
    146 @dataclass(frozen=True)
    147 class MergedEnvironment:
    148     config: TomlTable
    149     # every key path of config, mapped to the last layer to set a key at or below it
    150     origins: Mapping[KeyPath, LayerName]
    151     type_changes: tuple[Finding, ...]
```

### 58. vocabulary.py:149

```python
    141     # the last layer to set a key at or below path
    142     layer: LayerName
    143     detail: str
    144 
    145 
    146 @dataclass(frozen=True)
    147 class MergedEnvironment:
    148     config: TomlTable
>>  149     # every key path of config, mapped to the last layer to set a key at or below it
    150     origins: Mapping[KeyPath, LayerName]
    151     type_changes: tuple[Finding, ...]
    152 
    153 
    154 @dataclass(frozen=True)
    155 class EnvironmentAudit:
    156     name: EnvironmentName
    157     layers: tuple[LayerName, ...]
    158     config: TomlTable
    159     findings: tuple[Finding, ...]
```

## P6 chess (package pgn_replay): 12 comments

`scratchpad/cycle14/p6/pgn_replay`

### 59. __main__.py:71

```python
     63     if not pgn_paths:
     64         LOG.error('input.no_pgn_files', extra={'input_dir': raw_input_dir, 'expected': f'a directory with {PGN_GLOB}'})
     65         return EXIT_UNUSABLE_INPUT
     66 
     67     located_games: list[LocatedGame] = []
     68     unreadable = 0
     69     for pgn_path in pgn_paths:
     70         try:
>>   71             # PGN files from older software are often Latin-1. errors='replace' turns each such byte into U+FFFD
     72             pgn_text = pgn_path.read_text(encoding='utf-8', errors='replace')
     73         except OSError as exc:
     74             LOG.error('input.unreadable', extra={'pgn_file': pgn_path.name, 'error': exc.strerror})
     75             unreadable += 1
     76             continue
     77         replayed_games = enumerate(replayPgnText(pgn_text), start=1)
     78         file_games = [LocatedGame(pgn_path.name, number, replayed) for number, replayed in replayed_games]
     79         located_games.extend(file_games)
     80         file_totals = countTotals(file_games)
     81         if file_totals.illegal or file_totals.mismatches:
```

### 60. fen.py:91

```python
     83 
     84 
     85 def _parseBoard(raw_board: str) -> Board:
     86     raw_ranks = raw_board.split('/')
     87     if len(raw_ranks) != 8:
     88         raise _rejectFen(f'board {raw_board!r} has {len(raw_ranks)} ranks (expected 8, separated by /)')
     89 
     90     squares: list[Piece | None] = []
>>   91     # rank 8 comes first in FEN, and a1 first on the board
     92     for raw_rank in reversed(raw_ranks):
     93         row: list[Piece | None] = []
     94         for character in raw_rank:
     95             piece = _parseFenPiece(character)
     96             if character in '12345678':
     97                 row.extend([None] * int(character))
     98             elif piece is not None:
     99                 row.append(piece)
    100             else:
    101                 raise _rejectFen(f'board character {character!r} (expected a piece letter such as N or n, or 1 to 8)')
```

### 61. fen.py:165

```python
    157         raise _rejectFen('the side not to move is in check')
    158 
    159 
    160 def _doubleStepEvident(position: Position, en_passant: Square) -> bool:
    161     board = position.board
    162     stepper = opponentOf(position.side_to_move)
    163     ranks = lookupPawnRanks(stepper)
    164     rank_offset = 8 * ranks.forward
>>  165     # test the rank first. On another rank, en_passant + rank_offset can leave the board, and a negative index wraps
    166     if en_passant // 8 != ranks.start_rank + ranks.forward:
    167         return False
    168     pawn_landed = board[en_passant + rank_offset] == Piece(stepper, PieceKind.PAWN)
    169     return pawn_landed and board[en_passant] is None and board[en_passant - rank_offset] is None
    170 
    171 
    172 def _parseFenPiece(character: str) -> Piece | None:
    173     kind = parsePieceLetter(character.upper())
    174     if kind is None:
    175         return None
```

### 62. pgn.py:23

```python
     15 import re
     16 from collections.abc import Mapping, Sequence
     17 
     18 from pgn_replay.vocabulary import PgnGame
     19 
     20 
     21 def parsePgnText(pgn_text: str) -> tuple[PgnGame, ...]:
     22     """Split a PGN text into games, in text order."""
>>   23     # `[White "Ada"]` is a tag, `3...` a number, `$1` a glyph and `Qxf7#` a word.
>>   24     # An unclosed comment runs to the end of the text.
     25     TOKEN_PATTERN = re.compile(
     26         r'(?P<tag>\[\s*(?P<tag_name>\w+)\s+"(?P<tag_value>(?:[^"\\]|\\.)*)"\s*\])'
     27         r'|(?P<comment>\{[^}]*\}?)'
     28         r'|(?P<open>\()'
     29         r'|(?P<close>\))'
     30         r'|(?P<glyph>\$\d+)'
     31         r'|(?P<result>1-0|0-1|1/2-1/2|\*)'
     32         r'|(?P<number>\d+\.+)'
     33         r'|(?P<word>[^\s{}()$]+|\S)',
     34     )
```

### 63. rules.py:54

```python
     46 
     47 
     48 def inCheck(board: Board, color: Color) -> bool:
     49     king = Square(board.index(Piece(color, PieceKind.KING)))
     50     return squareAttacked(board, king, opponentOf(color))
     51 
     52 
     53 def squareAttacked(board: Board, square: Square, attacker: Color) -> bool:
>>   54     # a pawn attacks diagonally forward, so the attacking pawn stands one rank behind the square
     55     behind = -lookupPawnRanks(attacker).forward
     56     for file_step in (-1, 1):
     57         source = _offsetSquare(square, (file_step, behind))
     58         if source is not None and board[source] == Piece(attacker, PieceKind.PAWN):
     59             return True
     60 
     61     # movement is symmetric. A piece attacks the square when its steps, taken from the square, reach it
     62     for kind in PieceKind:
     63         movement = _lookupMovement(kind)
     64         if movement is None:
```

### 64. rules.py:61

```python
     53 def squareAttacked(board: Board, square: Square, attacker: Color) -> bool:
     54     # a pawn attacks diagonally forward, so the attacking pawn stands one rank behind the square
     55     behind = -lookupPawnRanks(attacker).forward
     56     for file_step in (-1, 1):
     57         source = _offsetSquare(square, (file_step, behind))
     58         if source is not None and board[source] == Piece(attacker, PieceKind.PAWN):
     59             return True
     60 
>>   61     # movement is symmetric. A piece attacks the square when its steps, taken from the square, reach it
     62     for kind in PieceKind:
     63         movement = _lookupMovement(kind)
     64         if movement is None:
     65             continue
     66         for step in movement.steps:
     67             reached = list(_walk(board, square, step, slides=movement.slides))
     68             if reached and board[reached[-1]] == Piece(attacker, kind):
     69                 return True
     70 
     71     return False
```

### 65. rules.py:140

```python
    132     return move.en_passant or position.board[move.target] is not None
    133 
    134 
    135 def applyMove(state: GameState, move: Move) -> GameState:
    136     """Play a legal move, and update the castling rights, the en passant square and both counters."""
    137     position = state.position
    138     double_step = move.piece.kind is PieceKind.PAWN and abs(move.target - move.origin) == 16
    139     passed_square = Square((move.origin + move.target) // 2) if double_step else None
>>  140     # a castling right ends once its king or rook leaves home, or a piece captures on the rook's home square
    141     touched = {move.origin, move.target}
    142     lost_rights = set()
    143     for right in CastlingRight:
    144         geometry = lookupCastlingGeometry(right)
    145         if touched & {geometry.king_from, geometry.rook_from}:
    146             lost_rights.add(right)
    147 
    148     next_position = Position(
    149         board=_movePieces(position.board, move),
    150         side_to_move=opponentOf(position.side_to_move),
```

### 66. rules.py:222

```python
    214     return expanded
    215 
    216 
    217 def _movePieces(board: Board, move: Move) -> Board:
    218     squares = list(board)
    219     squares[move.origin] = None
    220     squares[move.target] = move.piece if move.promotion is None else Piece(move.piece.color, move.promotion)
    221     if move.en_passant:
>>  222         # the captured pawn stands beside the capturing pawn, on the target's file
    223         squares[move.origin - move.origin % 8 + move.target % 8] = None
    224     if move.castling is not None:
    225         geometry = lookupCastlingGeometry(move.castling)
    226         squares[geometry.rook_from] = None
    227         squares[geometry.rook_to] = Piece(geometry.color, PieceKind.ROOK)
    228     return tuple(squares)
    229 
    230 
    231 def _walk(board: Board, origin: Square, step: _Step, *, slides: bool) -> Iterator[Square]:
    232     """Yield the squares reached by repeating step from origin, or only the first square when not sliding.
```

### 67. rules.py:289

```python
    281         case PieceKind.QUEEN:
    282             return _Movement(STRAIGHT_STEPS + DIAGONAL_STEPS, slides=True)
    283         case PieceKind.KING:
    284             return _Movement(STRAIGHT_STEPS + DIAGONAL_STEPS, slides=False)
    285 
    286 
    287 ### vocabulary #########################################################################
    288 
>>  289 # (file step, rank step)
    290 _Step = tuple[int, int]
    291 
    292 
    293 @dataclass(frozen=True)
    294 class _Movement:
    295     """`slides` is true for a bishop, a rook and a queen. These go any number of steps in one direction."""
    296 
    297     steps: tuple[_Step, ...]
    298     slides: bool
```

### 68. san.py:40

```python
     32     """Resolve a SAN token to the one legal move of the side to move that matches it.
     33 
     34     A piece pinned to its king is not a candidate, so `Nc3` needs no file or rank while the other
     35     knight that reaches c3 is pinned.
     36 
     37     Raises:
     38         IllegalMoveError: the token is not SAN, or matches no legal move, or matches more than one.
     39     """
>>   40     # matches:
>>   41     # `e4`
>>   42     # `Nbd7`
>>   43     # `exd8=Q+`
>>   44     # `O-O-O!?`
>>   45     # rejects:
>>   46     # `Kx9`
     47     SAN_PATTERN = re.compile(
     48         r'(?:(?P<castling>O-O(?:-O)?)'
     49         r'|(?P<piece>[A-Z])?(?P<file>[a-h])?(?P<rank>[1-8])?(?P<capture>x)?(?P<target>[a-h][1-8])'
     50         r'(?:=(?P<promotion>[A-Z]))?)'
     51         r'[+#!?]*',
     52     )
     53     UNPARSEABLE = 'not SAN (expected a form such as e4, Nbd7, exd6, a8=N or O-O)'
     54     match = SAN_PATTERN.fullmatch(san)
     55     if match is None:
     56         raise _rejectSan(san, UNPARSEABLE)
```

### 69. vocabulary.py:10

```python
      2 
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum, auto
      7 from typing import NewType
      8 
      9 
>>   10 # a1 is 0, b1 is 1, a2 is 8 and h8 is 63
     11 Square = NewType('Square', int)
     12 
     13 
     14 class Color(Enum):
     15     WHITE = auto()
     16     BLACK = auto()
     17 
     18 
     19 class PieceKind(Enum):
     20     PAWN = auto()
```

### 70. vocabulary.py:44

```python
     36 
     37 
     38 @dataclass(frozen=True)
     39 class Piece:
     40     color: Color
     41     kind: PieceKind
     42 
     43 
>>   44 # 64 squares in Square order. None is an empty square
     45 Board = tuple[Piece | None, ...]
     46 
     47 
     48 @dataclass(frozen=True)
     49 class Position:
     50     """Two positions are the same for threefold repetition when these four fields are equal.
     51 
     52     `en_passant` is set only when a capture onto it is legal.
     53     """
     54 
```

## P7 MIDI (package midi_report): 10 comments

`scratchpad/cycle14/p7/midi_report`

### 71. analysis.py:33

```python
     25     NoteMessageKind,
     26     Pitch,
     27     Tick,
     28     Track,
     29 )
     30 
     31 
     32 _DRUM_CHANNEL = Channel(9)
>>   33 # the defaults that the Standard MIDI File specification sets for a file without these events
     34 _DEFAULT_MICROSECONDS_PER_QUARTER = 500_000
     35 _DEFAULT_METER = Meter(4, 4)
     36 
     37 
     38 def analyseMidiFile(data: bytes) -> FileAnalysis:
     39     """Parse and analyse the bytes of one Standard MIDI File.
     40 
     41     Raises:
     42         UnreadableMidiError: the bytes are not a Standard MIDI File that midi_report can read.
     43     """
```

### 72. analysis.py:70

```python
     62         max_polyphony=_computeMaxPolyphony(notes),
     63         hanging_count=sum(note.hanging for note in notes),
     64         orphan_off_count=sum(paired.orphan_off_count for paired in paired_tracks),
     65     )
     66 
     67 
     68 def _buildTempoMap(midi_file: MidiFile) -> _TempoMap:
     69     tempo_changes = itertools.chain.from_iterable(track.tempo_changes for track in midi_file.tracks)
>>   70     # sorted() is stable. Of two changes on one tick, the later in track order applies
     71     change_ticks = [Tick(0)]
     72     tempos = [_DEFAULT_MICROSECONDS_PER_QUARTER]
     73     for change in sorted(tempo_changes, key=lambda change: change.tick):
     74         if change.tick == change_ticks[-1]:
     75             tempos[-1] = change.microseconds_per_quarter
     76         else:
     77             change_ticks.append(change.tick)
     78             tempos.append(change.microseconds_per_quarter)
     79 
     80     elapsed_microseconds = [Fraction(0)]
```

### 73. analysis.py:124

```python
    116         case NoteMessageKind.ON:
    117             return message.velocity > 0
    118         case NoteMessageKind.OFF:
    119             return False
    120 
    121 
    122 def _findMeter(tracks: Iterable[Track]) -> Meter:
    123     time_signatures = itertools.chain.from_iterable(track.time_signatures for track in tracks)
>>  124     # min() returns the first of equal ticks. Of two time signatures on one tick, the earlier track's applies
    125     first = min(time_signatures, key=lambda signature: signature.tick, default=None)
    126     if first is None:
    127         return _DEFAULT_METER
    128 
    129     return Meter(first.numerator, 2**first.denominator_exponent)
    130 
    131 
    132 def _findLongestNote(notes: Iterable[_Note], tempo_map: _TempoMap) -> LongestNote | None:
    133     # Fraction durations. Two notes of equal length can get float durations that differ in the last bit
    134     longest = min(
```

### 74. analysis.py:133

```python
    125     first = min(time_signatures, key=lambda signature: signature.tick, default=None)
    126     if first is None:
    127         return _DEFAULT_METER
    128 
    129     return Meter(first.numerator, 2**first.denominator_exponent)
    130 
    131 
    132 def _findLongestNote(notes: Iterable[_Note], tempo_map: _TempoMap) -> LongestNote | None:
>>  133     # Fraction durations. Two notes of equal length can get float durations that differ in the last bit
    134     longest = min(
    135         notes,
    136         key=lambda note: (-tempo_map.microsecondsBetween(note.start, note.end), note.start, note.pitch, note.channel),
    137         default=None,
    138     )
    139     if longest is None:
    140         return None
    141 
    142     return LongestNote(
    143         pitch=longest.pitch,
```

### 75. analysis.py:151

```python
    143         pitch=longest.pitch,
    144         channel=longest.channel,
    145         start_seconds=tempo_map.secondsBetween(Tick(0), longest.start),
    146         seconds=tempo_map.secondsBetween(longest.start, longest.end),
    147     )
    148 
    149 
    150 def _computeMaxPolyphony(notes: Sequence[_Note]) -> int:
>>  151     # The interval of a note is [start, end). At a shared tick, an end (-1) sorts before a start (+1).
>>  152     # A note of zero ticks overlaps nothing.
    153     timed_notes = [note for note in notes if note.end > note.start]
    154     edges = sorted([(note.start, 1) for note in timed_notes] + [(note.end, -1) for note in timed_notes])
    155     sounding = 0
    156     max_polyphony = 0
    157     for _, change in edges:
    158         sounding += change
    159         max_polyphony = max(max_polyphony, sounding)
    160 
    161     return max_polyphony
    162 
```

### 76. analysis.py:192

```python
    184     notes: tuple[_Note, ...]
    185     drum_hit_count: int
    186     orphan_off_count: int
    187 
    188 
    189 @dataclass(frozen=True)
    190 class _TempoMap:
    191     ticks_per_quarter: int
>>  192     # each tempo applies from its change tick up to the next one
    193     change_ticks: tuple[Tick, ...]
    194     microseconds_per_quarter: tuple[int, ...]
    195     elapsed_microseconds: tuple[Fraction, ...]
    196 
    197     def microsecondsBetween(self, start: Tick, end: Tick) -> Fraction:
    198         return self.microsecondsAt(end) - self.microsecondsAt(start)
    199 
    200     def microsecondsAt(self, tick: Tick) -> Fraction:
    201         span = bisect_right(self.change_ticks, tick) - 1
    202         span_ticks = tick - self.change_ticks[span]
```

### 77. report.py:146

```python
    138             )
    139 
    140 
    141 def _formatOptionalNoteName(pitch: Pitch | None) -> str | None:
    142     return None if pitch is None else _formatNoteName(pitch)
    143 
    144 
    145 def _formatNoteName(pitch: Pitch) -> str:
>>  146     # pitch 60 is C4
    147     NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    148     return f'{NAMES[pitch % 12]}{pitch // 12 - 1}'
    149 
    150 
    151 ### vocabulary #########################################################################
    152 
    153 
    154 @dataclass(frozen=True)
    155 class _Totals:
    156     files: int
```

### 78. smf.py:199

```python
    191     def readDataByte(self) -> int:
    192         value = self.readByte()
    193         if value & 0x80:
    194             raise self.rejectEvent(f'has the data byte 0x{value:02x} (expected 0x00 to 0x7F)')
    195 
    196         return value
    197 
    198     def readVariableLength(self) -> int:
>>  199         # 7 bits per byte, most significant first. The top bit is set on every byte but the last
    200         value = 0
    201         while True:
    202             byte = self.readByte()
    203             value = (value << 7) | (byte & 0x7F)
    204             if not byte & 0x80:
    205                 return value
    206 
    207     def decodeTempo(self, meta_data: bytes) -> int:
    208         if len(meta_data) != 3:
    209             raise self.rejectEvent(f'is a set-tempo event of {len(meta_data)} bytes (expected 3)')
```

### 79. vocabulary.py:46

```python
     38     tick: Tick
     39     microseconds_per_quarter: int
     40 
     41 
     42 @dataclass(frozen=True)
     43 class TimeSignature:
     44     tick: Tick
     45     numerator: int
>>   46     # the denominator is 2 ** denominator_exponent
     47     denominator_exponent: int
     48 
     49 
     50 @dataclass(frozen=True)
     51 class Track:
     52     note_messages: tuple[NoteMessage, ...]
     53     tempo_changes: tuple[TempoChange, ...]
     54     time_signatures: tuple[TimeSignature, ...]
     55     end_tick: Tick
     56 
```

### 80. vocabulary.py:61

```python
     53     tempo_changes: tuple[TempoChange, ...]
     54     time_signatures: tuple[TimeSignature, ...]
     55     end_tick: Tick
     56 
     57 
     58 @dataclass(frozen=True)
     59 class MidiFile:
     60     file_format: int
>>   61     # the count in the MThd chunk. This count can differ from len(tracks)
     62     track_count: int
     63     ticks_per_quarter: int
     64     tracks: tuple[Track, ...]
     65 
     66 
     67 @dataclass(frozen=True)
     68 class Meter:
     69     numerator: int
     70     denominator: int
     71 
```

## P8 cache server (package cache_server): 8 comments

`scratchpad/cycle14/p8/cache_server`

### 81. protocol.py:168

```python
    160 
    161     printable = all(byte > SPACE and byte != DELETE for byte in raw_key)
    162     if not (len(raw_key) <= MAX_KEY_BYTES and printable):
    163         raise _rejectCommandLine(f'bad key (expected 1 to {MAX_KEY_BYTES} bytes with no control character or space)')
    164     return Key(raw_key)
    165 
    166 
    167 def _parseUnsigned(raw_number: bytes, field: str, maximum: int) -> int:
>>  168     # a token is at most MAX_LINE_BYTES long. int() accepts up to 4,300 digits
    169     if not (raw_number.isdigit() and int(raw_number) <= maximum):
    170         raise _rejectCommandLine(f'bad {field} (expected an integer from 0 to {maximum})')
    171     return int(raw_number)
    172 
    173 
    174 def _parseExptime(raw_exptime: bytes) -> int:
    175     LIMIT = 2**63
    176 
    177     digits = raw_exptime.removeprefix(b'-')
    178     if not (digits.isdigit() and int(digits) < LIMIT):
```

### 82. server.py:50

```python
     42         ListenError: the port can't be bound.
     43     """
     44     stop = asyncio.Event()
     45     loop = asyncio.get_running_loop()
     46     for signal_number in (signal.SIGINT, signal.SIGTERM):
     47         loop.add_signal_handler(signal_number, stop.set)
     48 
     49     cache_server = _CacheServer(Store(max_bytes))
>>   50     # readuntil() counts a partly received line end against the limit. _readLine() checks the exact length
     51     line_limit = protocol.MAX_LINE_BYTES + len(protocol.LINE_END)
     52     try:
     53         listener = await asyncio.start_server(cache_server.acceptClient, _HOST, port, limit=line_limit)
     54     except OSError as exc:
     55         _LOG.error('server.listen_failed', extra={'host': _HOST, 'port': port, 'reason': exc.strerror})
     56         raise ListenError(f'{_HOST}:{port}') from exc
     57     _LOG.info('server.listening', extra={'host': _HOST, 'port': port, 'max_bytes': max_bytes})
     58 
     59     await stop.wait()
     60     listener.close()
```

### 83. server.py:184

```python
    176     Returns:
    177         The data, or b'' when keep is False. None when other bytes come before the next line end.
    178         The reader is then past that line end.
    179 
    180     Raises:
    181         asyncio.IncompleteReadError: the client closed the connection.
    182         LineTooLongError: the bytes after the block run over protocol.MAX_LINE_BYTES with no line end.
    183     """
>>  184     # a block too large to store is dropped chunk by chunk. A client can't make the server buffer it
    185     CHUNK_BYTES = 64 * 1024
    186 
    187     chunks = []
    188     remaining = byte_count
    189     while remaining > 0:
    190         chunk = await reader.readexactly(min(remaining, CHUNK_BYTES))
    191         if keep:
    192             chunks.append(chunk)
    193         remaining -= len(chunk)
    194 
```

### 84. store.py:29

```python
     21     ObjectTooLargeError,
     22     Outcome,
     23     StorageCommand,
     24     StorageVerb,
     25 )
     26 
     27 
     28 _ITEM_OVERHEAD_BYTES = 50
>>   29 # memcached protocol: an exptime up to 30 days is relative. A larger one is a Unix time
     30 _MAX_RELATIVE_EXPTIME_S = 30 * 24 * 60 * 60
     31 
     32 _LOG = logging.getLogger(__name__)
     33 
     34 
     35 class Store:
     36     def __init__(self, max_bytes: int) -> None:
     37         self.max_bytes = max_bytes
     38         # least recently used first
     39         self.items: OrderedDict[Key, Item] = OrderedDict()
```

### 85. store.py:38

```python
     30 _MAX_RELATIVE_EXPTIME_S = 30 * 24 * 60 * 60
     31 
     32 _LOG = logging.getLogger(__name__)
     33 
     34 
     35 class Store:
     36     def __init__(self, max_bytes: int) -> None:
     37         self.max_bytes = max_bytes
>>   38         # least recently used first
     39         self.items: OrderedDict[Key, Item] = OrderedDict()
     40         self.used_bytes = 0
     41         self.last_cas = 0
     42 
     43     def storable(self, key: Key, byte_count: int) -> bool:
     44         return _measureItem(key, byte_count) <= self.max_bytes
     45 
     46     def storeItem(self, command: StorageCommand, data: bytes) -> Outcome:
     47         """Apply a set, add, replace or cas.
     48 
```

### 86. store.py:141

```python
    133 
    134     def _removeExpiredItems(self) -> None:
    135         expired_keys = [key for key, item in self.items.items() if _expired(item)]
    136         for key in expired_keys:
    137             self._removeItem(key)
    138 
    139 
    140 def _describeKey(key: Key) -> str:
>>  141     # keys are arbitrary bytes. Non-UTF-8 bytes appear as \x escapes
    142     return key.decode('utf-8', 'backslashreplace')
    143 
    144 
    145 def _findStorageRefusal(command: StorageCommand, current: Item | None) -> Outcome | None:
    146     match command.verb:
    147         case StorageVerb.SET:
    148             return None
    149         case StorageVerb.ADD:
    150             return Outcome.NOT_STORED if current is not None else None
    151         case StorageVerb.REPLACE:
```

### 87. store.py:180

```python
    172     match verb:
    173         case ArithmeticVerb.INCR:
    174             return (value + amount) % (UINT64_MAX + 1)
    175         case ArithmeticVerb.DECR:
    176             return max(value - amount, 0)
    177 
    178 
    179 def _numeric(data: bytes) -> bool:
>>  180     # int() rejects a string over 4,300 digits. Check the length first
    181     MAX_DIGITS = len(str(UINT64_MAX))
    182     return len(data) <= MAX_DIGITS and data.isdigit() and int(data) <= UINT64_MAX
    183 
    184 
    185 def _expired(item: Item) -> bool:
    186     return item.deadline is not None and item.deadline <= time.monotonic()
    187 
    188 
    189 def _measureItem(key: Key, byte_count: int) -> int:
    190     return len(key) + byte_count + _ITEM_OVERHEAD_BYTES
```

### 88. vocabulary.py:79

```python
     71 
     72 Command: TypeAlias = StorageCommand | RetrievalCommand | DeleteCommand | ArithmeticCommand | QuitCommand
     73 
     74 
     75 @dataclass(frozen=True)
     76 class Item:
     77     flags: int
     78     data: bytes
>>   79     # a time.monotonic() value. An item with None doesn't expire
     80     deadline: float | None
     81     cas: CasValue
     82 
     83 
     84 class MalformedCommandError(RuntimeError):
     85     pass
     86 
     87 
     88 class UnknownCommandError(RuntimeError):
     89     pass
```

## P9 text wrapping (package termwrap): 16 comments

`scratchpad/cycle14/p9/termwrap`

### 89. measure.py:44

```python
     36 
     37     A zero-width character at the start of the text, or after an SGR sequence or a soft hyphen, is a
     38     cluster of 0 columns.
     39 
     40     Raises:
     41         ValueError: The text has a character with no column width, such as a control character or a
     42             newline, or an escape sequence other than SGR.
     43     """
>>   44     # matches:
>>   45     # `\x1b[1m`
>>   46     # `\x1b[38;5;208m`
>>   47     # `\x1b[m`
>>   48     # rejects:
>>   49     # `\x1b[2K`
     50     STYLE_SEQUENCE = re.compile(r'\x1b\[[0-9;]*m')
     51     tokens: list[Token] = []
     52     index = 0
     53     while index < len(text):
     54         character = text[index]
     55         if character == _ESCAPE:
     56             sequence = STYLE_SEQUENCE.match(text, index)
     57             if sequence is None:
     58                 raise ValueError(
     59                     f'unsupported escape sequence {text[index : index + 8]!r} '
```

### 90. measure.py:83

```python
     75         index += 1
     76 
     77     return tokens
     78 
     79 
     80 def _zeroWidth(character: str) -> bool:
     81     return (
     82         unicodedata.combining(character) != 0
>>   83         or character in {'​', '‍'}  # zero width space, zero width joiner
     84         or '︀' <= character <= '️'  # variation selectors
     85     )
     86 
     87 
     88 def _countCharacterColumns(character: str) -> int:
     89     # control, format, surrogate, private use, unassigned, line separator, paragraph separator
     90     UNMEASURABLE_CATEGORIES = frozenset({'Cc', 'Cf', 'Cs', 'Co', 'Cn', 'Zl', 'Zp'})
     91     if _zeroWidth(character):
     92         return 0
     93     if unicodedata.category(character) in UNMEASURABLE_CATEGORIES:
```

### 91. measure.py:84

```python
     76 
     77     return tokens
     78 
     79 
     80 def _zeroWidth(character: str) -> bool:
     81     return (
     82         unicodedata.combining(character) != 0
     83         or character in {'​', '‍'}  # zero width space, zero width joiner
>>   84         or '︀' <= character <= '️'  # variation selectors
     85     )
     86 
     87 
     88 def _countCharacterColumns(character: str) -> int:
     89     # control, format, surrogate, private use, unassigned, line separator, paragraph separator
     90     UNMEASURABLE_CATEGORIES = frozenset({'Cc', 'Cf', 'Cs', 'Co', 'Cn', 'Zl', 'Zp'})
     91     if _zeroWidth(character):
     92         return 0
     93     if unicodedata.category(character) in UNMEASURABLE_CATEGORIES:
     94         raise ValueError(
```

### 92. measure.py:89

```python
     81     return (
     82         unicodedata.combining(character) != 0
     83         or character in {'​', '‍'}  # zero width space, zero width joiner
     84         or '︀' <= character <= '️'  # variation selectors
     85     )
     86 
     87 
     88 def _countCharacterColumns(character: str) -> int:
>>   89     # control, format, surrogate, private use, unassigned, line separator, paragraph separator
     90     UNMEASURABLE_CATEGORIES = frozenset({'Cc', 'Cf', 'Cs', 'Co', 'Cn', 'Zl', 'Zp'})
     91     if _zeroWidth(character):
     92         return 0
     93     if unicodedata.category(character) in UNMEASURABLE_CATEGORIES:
     94         raise ValueError(
     95             f'character U+{ord(character):04X} has no column width '
     96             '(expected printable characters, SGR sequences and soft hyphens, and newlines only in wrap())',
     97         )
     98 
     99     return 2 if unicodedata.east_asian_width(character) in {'W', 'F'} else 1
```

### 93. vocabulary.py:10

```python
      2 
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum, auto
      7 
      8 
      9 class TokenKind(Enum):
>>   10     CLUSTER = auto()  # a character and the zero-width characters after it
     11     SPACE = auto()  # one U+0020, with no zero-width character after it
     12     STYLE = auto()  # an SGR escape sequence
     13     SOFT_HYPHEN = auto()
     14 
     15 
     16 @dataclass(frozen=True)
     17 class Token:
     18     kind: TokenKind
     19     text: str
     20     columns: int
```

### 94. vocabulary.py:11

```python
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum, auto
      7 
      8 
      9 class TokenKind(Enum):
     10     CLUSTER = auto()  # a character and the zero-width characters after it
>>   11     SPACE = auto()  # one U+0020, with no zero-width character after it
     12     STYLE = auto()  # an SGR escape sequence
     13     SOFT_HYPHEN = auto()
     14 
     15 
     16 @dataclass(frozen=True)
     17 class Token:
     18     kind: TokenKind
     19     text: str
     20     columns: int
```

### 95. vocabulary.py:12

```python
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum, auto
      7 
      8 
      9 class TokenKind(Enum):
     10     CLUSTER = auto()  # a character and the zero-width characters after it
     11     SPACE = auto()  # one U+0020, with no zero-width character after it
>>   12     STYLE = auto()  # an SGR escape sequence
     13     SOFT_HYPHEN = auto()
     14 
     15 
     16 @dataclass(frozen=True)
     17 class Token:
     18     kind: TokenKind
     19     text: str
     20     columns: int
```

### 96. wrapping.py:25

```python
     17 from collections.abc import Sequence
     18 from dataclasses import dataclass
     19 from itertools import takewhile
     20 
     21 from termwrap import measure
     22 from termwrap.vocabulary import Token, TokenKind
     23 
     24 
>>   25 _MINIMUM_WIDTH = 2  # the widest cluster takes 2 columns
     26 _RESET = '\x1b[0m'
     27 
     28 
     29 def wrap(text: str, width: int) -> list[str]:
     30     """Break the text into lines of at most `width` columns.
     31 
     32     Raises:
     33         ValueError: `width` is below 2, or the text has a character with no column width, such as a
     34             control character other than newline, or an escape sequence other than SGR.
     35     """
```

### 97. wrapping.py:50

```python
     42     return _renderLines(lines)
     43 
     44 
     45 def _breakParagraph(tokens: Sequence[Token], width: int) -> list[_Line]:
     46     lines: list[_Line] = []
     47     pending: list[Token] = []
     48     for token in tokens:
     49         pending.append(token)
>>   50         # a run of spaces may pass the right edge. The run is dropped at the break
     51         while token.kind is TokenKind.CLUSTER and sum(item.columns for item in pending) > width:
     52             cut = _findBreak(pending, width)
     53             kept = pending[: cut.end]
     54             # an SGR sequence among dropped spaces still changes the style of the next line
     55             dropped_styles = [item for item in pending[cut.end : cut.resume] if item.kind is TokenKind.STYLE]
     56             if cut.hyphenated or sum(item.columns for item in kept) > 0:
     57                 lines.append(_Line(tuple(kept), hyphenated=cut.hyphenated))
     58                 pending = dropped_styles + pending[cut.resume :]
     59             else:
     60                 # spaces at the start of a line overflowed. Drop them and emit no empty line
```

### 98. wrapping.py:54

```python
     46     lines: list[_Line] = []
     47     pending: list[Token] = []
     48     for token in tokens:
     49         pending.append(token)
     50         # a run of spaces may pass the right edge. The run is dropped at the break
     51         while token.kind is TokenKind.CLUSTER and sum(item.columns for item in pending) > width:
     52             cut = _findBreak(pending, width)
     53             kept = pending[: cut.end]
>>   54             # an SGR sequence among dropped spaces still changes the style of the next line
     55             dropped_styles = [item for item in pending[cut.end : cut.resume] if item.kind is TokenKind.STYLE]
     56             if cut.hyphenated or sum(item.columns for item in kept) > 0:
     57                 lines.append(_Line(tuple(kept), hyphenated=cut.hyphenated))
     58                 pending = dropped_styles + pending[cut.resume :]
     59             else:
     60                 # spaces at the start of a line overflowed. Drop them and emit no empty line
     61                 pending = kept + dropped_styles + pending[cut.resume :]
     62 
     63     lines.append(_finishParagraph(pending, width))
     64     return lines
```

### 99. wrapping.py:60

```python
     52             cut = _findBreak(pending, width)
     53             kept = pending[: cut.end]
     54             # an SGR sequence among dropped spaces still changes the style of the next line
     55             dropped_styles = [item for item in pending[cut.end : cut.resume] if item.kind is TokenKind.STYLE]
     56             if cut.hyphenated or sum(item.columns for item in kept) > 0:
     57                 lines.append(_Line(tuple(kept), hyphenated=cut.hyphenated))
     58                 pending = dropped_styles + pending[cut.resume :]
     59             else:
>>   60                 # spaces at the start of a line overflowed. Drop them and emit no empty line
     61                 pending = kept + dropped_styles + pending[cut.resume :]
     62 
     63     lines.append(_finishParagraph(pending, width))
     64     return lines
     65 
     66 
     67 def _findBreak(pending: Sequence[Token], width: int) -> _Break:
     68     """Find the latest break before the last token, which is the cluster that overflowed.
     69 
     70     A soft hyphen is a break only with a free column for the `-` and a column before it on the line.
```

### 100. wrapping.py:100

```python
     92         end -= 1
     93     return _Break(end, end, hyphenated=False)
     94 
     95 
     96 def _finishParagraph(pending: Sequence[Token], width: int) -> _Line:
     97     if sum(token.columns for token in pending) <= width:
     98         return _Line(tuple(pending), hyphenated=False)
     99 
>>  100     # A cluster that overflows breaks the line when appended. A line that overflows here ends in spaces.
>>  101     # Drop them and any soft hyphen after the last cluster, and keep the SGR sequences.
    102     last_cluster = max((index for index, token in enumerate(pending) if token.kind is TokenKind.CLUSTER), default=-1)
    103     kept = [token for index, token in enumerate(pending) if index <= last_cluster or token.kind is TokenKind.STYLE]
    104     return _Line(tuple(kept), hyphenated=False)
    105 
    106 
    107 def _renderLines(lines: Sequence[_Line]) -> list[str]:
    108     """Join each line's tokens, and close and reopen the SGR style at every break.
    109 
    110     SGR sequences at the start of a line fold into the opening style. A line with no visible text
    111     renders as an empty string.
```

### 101. wrapping.py:127

```python
    119         body = ''.join(_renderToken(token) for token in line.tokens[leading:]) + ('-' if line.hyphenated else '')
    120         closing = _RESET if style and number < len(lines) else ''
    121         rendered.append(''.join(opening) + body + closing if body else '')
    122 
    123     return rendered
    124 
    125 
    126 def _updateStyle(style: tuple[str, ...], tokens: Sequence[Token]) -> tuple[str, ...]:
>>  127     # the spec defines a reset as `\x1b[0m` or `\x1b[m` only
    128     RESETS = frozenset({'\x1b[0m', '\x1b[m'})
    129     for token in tokens:
    130         if token.kind is TokenKind.STYLE:
    131             style = () if token.text in RESETS else (*style, token.text)
    132     return style
    133 
    134 
    135 def _renderToken(token: Token) -> str:
    136     match token.kind:
    137         case TokenKind.CLUSTER | TokenKind.SPACE | TokenKind.STYLE:
```

### 102. wrapping.py:140

```python
    132     return style
    133 
    134 
    135 def _renderToken(token: Token) -> str:
    136     match token.kind:
    137         case TokenKind.CLUSTER | TokenKind.SPACE | TokenKind.STYLE:
    138             return token.text
    139         case TokenKind.SOFT_HYPHEN:
>>  140             # a soft hyphen inside a line is not shown. One at a break is _Line.hyphenated
    141             return ''
    142 
    143 
    144 ### vocabulary #########################################################################
    145 
    146 
    147 @dataclass(frozen=True)
    148 class _Line:
    149     tokens: tuple[Token, ...]
    150     hyphenated: bool
```

### 103. wrapping.py:155

```python
    147 @dataclass(frozen=True)
    148 class _Line:
    149     tokens: tuple[Token, ...]
    150     hyphenated: bool
    151 
    152 
    153 @dataclass(frozen=True)
    154 class _Break:
>>  155     end: int  # the line is pending[:end]
    156     resume: int  # the next line starts at pending[resume:]
    157     hyphenated: bool
```

### 104. wrapping.py:156

```python
    148 class _Line:
    149     tokens: tuple[Token, ...]
    150     hyphenated: bool
    151 
    152 
    153 @dataclass(frozen=True)
    154 class _Break:
    155     end: int  # the line is pending[:end]
>>  156     resume: int  # the next line starts at pending[resume:]
    157     hyphenated: bool
```

## P10 change request (comments added to midi_report): 4 comments

`scratchpad/cycle14/p10/fixture/midi_report`

### 105. analysis.py:93

```python
     85     events: list[_EventT] = []
     86     for track in tracks:
     87         events.extend(event for event in track.events if isinstance(event, event_type))
     88 
     89     return events
     90 
     91 
     92 def _findFirstEvent(tracks: Iterable[Track], event_type: type[_EventT]) -> _EventT | None:
>>   93     # of events on one tick, min() returns the first in track order
     94     return min(_collectEvents(tracks, event_type), key=lambda event: event.tick, default=None)
     95 
     96 
     97 def _selectChannel(track: Track, channel: Channel) -> Track:
     98     """Drop the note starts and ends of every other channel."""
     99     events = tuple(
    100         event for event in track.events if not isinstance(event, NoteStart | NoteEnd) or event.channel == channel
    101     )
    102     return Track(events, track.end_tick)
    103 
```

### 106. report.py:171

```python
    163     # a Standard MIDI File without a time signature is in 4/4
    164     if time_signature is None:
    165         return '4/4'
    166 
    167     return f'{time_signature.numerator}/{time_signature.denominator}'
    168 
    169 
    170 def _nameKey(key_signature: KeySignature) -> str:
>>  171     # from 7 flats to 7 sharps
    172     MAJOR_TONICS = ('Cb', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#')
    173     MINOR_TONICS = ('Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#')
    174     MOST_FLATS = 7
    175     tonic_index = key_signature.sharps + MOST_FLATS
    176     match key_signature.mode:
    177         case Mode.MAJOR:
    178             return f'{MAJOR_TONICS[tonic_index]} major'
    179         case Mode.MINOR:
    180             return f'{MINOR_TONICS[tonic_index]} minor'
    181 
```

### 107. smf.py:151

```python
    143     return Track(tuple(events), tick)
    144 
    145 
    146 def _decodeMetaEvent(tick: Tick, meta_type: int, meta_data: bytes) -> list[TrackEvent]:
    147     SET_TEMPO = 0x51
    148     TIME_SIGNATURE = 0x58
    149     KEY_SIGNATURE = 0x59
    150     MOST_ACCIDENTALS = 7
>>  151     MODES = (Mode.MAJOR, Mode.MINOR)  # indexed by the mi byte
>>  152     # 0 microseconds per quarter note has no beats per minute. Skip the event
    153     if meta_type == SET_TEMPO and len(meta_data) == 3 and any(meta_data):
    154         return [TempoChange(tick, int.from_bytes(meta_data, 'big'))]
    155     if meta_type == TIME_SIGNATURE and len(meta_data) >= 2:
    156         return [TimeSignature(tick, numerator=meta_data[0], denominator=2 ** meta_data[1])]
    157     if meta_type == KEY_SIGNATURE and len(meta_data) == 2:
    158         sharps = int.from_bytes(meta_data[:1], 'big', signed=True)
    159         if abs(sharps) <= MOST_ACCIDENTALS and meta_data[1] < len(MODES):
    160             return [KeySignature(tick, sharps, MODES[meta_data[1]])]
    161     if meta_type in (SET_TEMPO, TIME_SIGNATURE, KEY_SIGNATURE):
    162         LOG.debug('smf.malformed_meta_event', extra={'meta_type': meta_type, 'length': len(meta_data)})
```

### 108. vocabulary.py:65

```python
     57 class Mode(Enum):
     58     MAJOR = 'major'
     59     MINOR = 'minor'
     60 
     61 
     62 @dataclass(frozen=True)
     63 class KeySignature:
     64     tick: Tick
>>   65     sharps: int  # negative for flats
     66     mode: Mode
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
