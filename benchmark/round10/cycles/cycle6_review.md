# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package timesheet): 9 comments

`scratchpad/cycle6/p1_S_1/timesheet`

### 1. glossary.py:55

```python
     47     employee_id: EmployeeId
     48     name: str
     49     hourly_rate: Decimal
     50     zone: ZoneInfo
     51 
     52 
     53 @dataclass(frozen=True)
     54 class SourceLine:
>>   55     file: str  # basename of the punch file
     56     line: int  # 1-based
     57 
     58 
     59 @dataclass(frozen=True)
     60 class Punch:
     61     badge: EmployeeId
     62     at: datetime
     63     direction: Direction
     64     source: SourceLine
     65 
```

### 2. glossary.py:56

```python
     48     name: str
     49     hourly_rate: Decimal
     50     zone: ZoneInfo
     51 
     52 
     53 @dataclass(frozen=True)
     54 class SourceLine:
     55     file: str  # basename of the punch file
>>   56     line: int  # 1-based
     57 
     58 
     59 @dataclass(frozen=True)
     60 class Punch:
     61     badge: EmployeeId
     62     at: datetime
     63     direction: Direction
     64     source: SourceLine
     65 
     66 
```

### 3. glossary.py:108

```python
    100     shifts: tuple[Shift, ...]
    101     unpaired: tuple[Problem, ...]
    102 
    103 
    104 @dataclass(frozen=True)
    105 class EmployeeWeek:
    106     employee_id: EmployeeId
    107     name: str
>>  108     week_start: date  # Monday, in the employee's site zone
    109     regular_minutes: int
    110     overtime_minutes: int
    111     gross_pay: Decimal  # rounded to cents
    112 
    113 
    114 @dataclass(frozen=True)
    115 class PayRun:
    116     """The result of one pay computation.
    117 
    118     `weeks` sorts by (week_start, employee_id) and `problems` by (file, line).
```

### 4. glossary.py:111

```python
    103 
    104 @dataclass(frozen=True)
    105 class EmployeeWeek:
    106     employee_id: EmployeeId
    107     name: str
    108     week_start: date  # Monday, in the employee's site zone
    109     regular_minutes: int
    110     overtime_minutes: int
>>  111     gross_pay: Decimal  # rounded to cents
    112 
    113 
    114 @dataclass(frozen=True)
    115 class PayRun:
    116     """The result of one pay computation.
    117 
    118     `weeks` sorts by (week_start, employee_id) and `problems` by (file, line).
    119     """
    120 
    121     weeks: tuple[EmployeeWeek, ...]
```

### 5. punch_files.py:50

```python
     42             if not raw_line.strip():
     43                 continue
     44 
     45             parsed = _parsePunch(raw_line, SourceLine(punch_path.name, line_number))
     46             if isinstance(parsed, Problem):
     47                 malformed.append(parsed)
     48                 continue
     49 
>>   50             # keyed on the parsed instant; the raw `at` string would count one punch sent with two offsets twice
     51             key = (parsed.badge, parsed.at, parsed.direction)
     52             if key in seen:
     53                 duplicates += 1
     54                 continue
     55             seen.add(key)
     56             punches.append(parsed)
     57 
     58     return PunchLog(tuple(punches), duplicates, tuple(malformed))
     59 
     60 
```

### 6. roster_csv.py:31

```python
     23 def readRoster(roster_path: Path, rules: Rules) -> Mapping[EmployeeId, Employee]:
     24     """Read and validate the roster, resolving each site to its zone.
     25 
     26     Raises:
     27         ConfigError: the file is unreadable or not CSV, the header differs, or a row is malformed,
     28             repeats an employee_id or names a site the rules do not.
     29     """
     30     HEADER = ['employee_id', 'name', 'hourly_rate', 'site']
>>   31     RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]{1,2})?')  # \d would admit non-ASCII digits such as '٣'
     32 
     33     try:
     34         with roster_path.open(encoding='utf-8', newline='') as roster_file:
     35             rows = list(csv.reader(roster_file, strict=True))
     36     except OSError as exc:
     37         raise logs.rejectInput(f'unreadable: {exc.strerror}', roster_path) from exc
     38     except UnicodeDecodeError as exc:
     39         raise logs.rejectInput('not UTF-8', roster_path) from exc
     40     except csv.Error as exc:
     41         raise logs.rejectInput(f'not CSV: {exc}', roster_path) from exc
```

### 7. rules_file.py:34

```python
     26 
     27 def readRules(rules_path: Path) -> Rules:
     28     """Read and validate the rules file.
     29 
     30     Raises:
     31         ConfigError: the file is unreadable or not a JSON object, a key is missing, a value has the
     32             wrong type, or a zone name is not an IANA zone.
     33     """
>>   34     MULTIPLIER_PATTERN = re.compile(r'[0-9]+(\.[0-9]+)?')  # \d would admit non-ASCII digits such as '٣'
     35 
     36     try:
     37         rules_text = rules_path.read_text(encoding='utf-8')
     38     except OSError as exc:
     39         raise logs.rejectInput(f'unreadable: {exc.strerror}', rules_path) from exc
     40     except UnicodeDecodeError as exc:
     41         raise logs.rejectInput('not UTF-8', rules_path) from exc
     42 
     43     try:
     44         document = json.loads(rules_text)
```

### 8. rules_file.py:78

```python
     70         site_timezones=MappingProxyType({site: ZoneInfo(zone_name) for site, zone_name in site_timezones.items()}),
     71         overtime_after_minutes=document['overtime_after_minutes'],
     72         overtime_multiplier=Decimal(multiplier),
     73         round_to_minutes=document['round_to_minutes'],
     74     )
     75 
     76 
     77 def _positiveInteger(value: object) -> bool:
>>   78     # without the bool test, JSON true passes as 1
     79     return isinstance(value, int) and not isinstance(value, bool) and value > 0
```

### 9. store.py:48

```python
     40         ' employee_id TEXT NOT NULL,'
     41         ' week_start TEXT NOT NULL,'
     42         ' name TEXT NOT NULL,'
     43         ' regular_minutes INTEGER NOT NULL,'
     44         ' overtime_minutes INTEGER NOT NULL,'
     45         ' gross_pay_cents INTEGER NOT NULL,'
     46         ' PRIMARY KEY (employee_id, week_start))'
     47     )
>>   48     # without the WHERE, rowcount counts an unchanged row as changed
     49     UPSERT = (
     50         'INSERT INTO employee_week VALUES (?, ?, ?, ?, ?, ?)'
     51         ' ON CONFLICT (employee_id, week_start) DO UPDATE SET'
     52         ' name = excluded.name,'
     53         ' regular_minutes = excluded.regular_minutes,'
     54         ' overtime_minutes = excluded.overtime_minutes,'
     55         ' gross_pay_cents = excluded.gross_pay_cents'
     56         ' WHERE (name, regular_minutes, overtime_minutes, gross_pay_cents)'
     57         ' != (excluded.name, excluded.regular_minutes, excluded.overtime_minutes, excluded.gross_pay_cents)'
     58     )
```

## Run 2 (package payroll): 10 comments

`scratchpad/cycle6/p1_S_2/payroll`

### 10. pay.py:54

```python
     46             EmployeeWeek(employee_id, employee.name, week_start, regular_minutes, overtime_minutes, gross_cents),
     47         )
     48 
     49     return tuple(sorted(weeks, key=lambda week: (week.week_start, week.employee_id)))
     50 
     51 
     52 def roundShiftMinutes(elapsed: timedelta, round_to_minutes: int) -> int:
     53     step = timedelta(minutes=round_to_minutes)
>>   54     # floor(elapsed / step + 1/2) in whole microseconds, so a halfway length rounds up with no float error
     55     steps = (2 * elapsed + step) // (2 * step)
     56     return steps * round_to_minutes
     57 
     58 
     59 def computeGrossCents(
     60     hourly_rate: Decimal,
     61     regular_minutes: int,
     62     overtime_minutes: int,
     63     overtime_multiplier: Decimal,
     64 ) -> int:
```

### 11. roster.py:32

```python
     24 
     25     Raises:
     26         InputError: the file is unreadable, its header is wrong, or a row is malformed.
     27     """
     28     HEADER = ['employee_id', 'name', 'hourly_rate', 'site']
     29     RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]{1,2})?')
     30 
     31     try:
>>   32         # read_text() would translate newlines, which alters a newline quoted inside a CSV field
     33         roster_text = roster_path.read_bytes().decode('utf-8-sig')
     34     except OSError as exc:
     35         raise _rejectRoster(roster_path, 0, f'unreadable: {exc.strerror}') from exc
     36     except UnicodeDecodeError as exc:
     37         raise _rejectRoster(roster_path, 0, 'not UTF-8') from exc
     38 
     39     rows = csv.reader(io.StringIO(roster_text, newline=''))
     40     if next(rows, None) != HEADER:
     41         raise _rejectRoster(roster_path, 1, f'header is not {",".join(HEADER)}')
     42 
```

### 12. rules.py:78

```python
     70         raise _rejectRules(rules_path, 'site_timezones is not a JSON object')
     71 
     72     site_zones: dict[SiteName, ZoneInfo] = {}
     73     for site, zone_name in site_timezones.items():
     74         if not isinstance(zone_name, str):
     75             raise _rejectRules(rules_path, f'site {site} names no zone')
     76         try:
     77             site_zones[SiteName(site)] = ZoneInfo(zone_name)
>>   78         # ZoneInfo() raises ValueError, not ZoneInfoNotFoundError, for a malformed key such as '../x'
     79         except (ZoneInfoNotFoundError, ValueError) as exc:
     80             raise _rejectRules(rules_path, f'site {site} names unknown zone {zone_name}') from exc
     81 
     82     return site_zones
     83 
     84 
     85 def _parsePositiveInteger(value: object, key: str, rules_path: Path) -> int:
     86     # without the bool test, JSON true passes as 1
     87     if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
     88         raise _rejectRules(rules_path, f'{key} is not a positive integer')
```

### 13. rules.py:86

```python
     78         # ZoneInfo() raises ValueError, not ZoneInfoNotFoundError, for a malformed key such as '../x'
     79         except (ZoneInfoNotFoundError, ValueError) as exc:
     80             raise _rejectRules(rules_path, f'site {site} names unknown zone {zone_name}') from exc
     81 
     82     return site_zones
     83 
     84 
     85 def _parsePositiveInteger(value: object, key: str, rules_path: Path) -> int:
>>   86     # without the bool test, JSON true passes as 1
     87     if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
     88         raise _rejectRules(rules_path, f'{key} is not a positive integer')
     89     return value
     90 
     91 
     92 def _rejectRules(rules_path: Path, reason: str) -> InputError:
     93     LOG.error('rules.rejected', extra={'path': str(rules_path), 'reason': reason})
     94     return InputError(f'{rules_path}: {reason}')
```

### 14. shifts.py:18

```python
     10 from collections.abc import Iterable
     11 from datetime import datetime
     12 
     13 from payroll.logs import LOG
     14 from payroll.vocabulary import Direction, EmployeeId, Pairing, Problem, ProblemKind, Punch, Shift
     15 
     16 
     17 def dropDuplicates(punches: Iterable[Punch]) -> tuple[Punch, ...]:
>>   18     # aware datetimes compare by instant, so the same punch written with another offset matches
     19     seen: set[tuple[EmployeeId, datetime, Direction]] = set()
     20     unique: list[Punch] = []
     21     for punch in punches:
     22         identity = (punch.badge, punch.at, punch.direction)
     23         if identity not in seen:
     24             seen.add(identity)
     25             unique.append(punch)
     26     return tuple(unique)
     27 
     28 
```

### 15. store.py:44

```python
     36     )
     37     UPSERT = (
     38         'INSERT INTO employee_week VALUES (?, ?, ?, ?, ?, ?)'
     39         ' ON CONFLICT (employee_id, week_start) DO UPDATE SET'
     40         ' name = excluded.name,'
     41         ' regular_minutes = excluded.regular_minutes,'
     42         ' overtime_minutes = excluded.overtime_minutes,'
     43         ' gross_cents = excluded.gross_cents'
>>   44         # without the WHERE, an unchanged row counts as a change
     45         ' WHERE (name, regular_minutes, overtime_minutes, gross_cents)'
     46         ' != (excluded.name, excluded.regular_minutes, excluded.overtime_minutes, excluded.gross_cents)'
     47     )
     48 
     49     rows = (
     50         (
     51             week.employee_id,
     52             week.week_start.isoformat(),
     53             week.name,
     54             week.regular_minutes,
```

### 16. vocabulary.py:56

```python
     48     employee_id: EmployeeId
     49     name: str
     50     hourly_rate: Decimal
     51     site: SiteName
     52 
     53 
     54 @dataclass(frozen=True, order=True)
     55 class Location:
>>   56     file: str  # basename of the punch file
     57     line: int  # 1-based
     58 
     59 
     60 @dataclass(frozen=True)
     61 class Punch:
     62     badge: EmployeeId
     63     at: datetime  # always carries a UTC offset
     64     direction: Direction
     65     location: Location
     66 
```

### 17. vocabulary.py:57

```python
     49     name: str
     50     hourly_rate: Decimal
     51     site: SiteName
     52 
     53 
     54 @dataclass(frozen=True, order=True)
     55 class Location:
     56     file: str  # basename of the punch file
>>   57     line: int  # 1-based
     58 
     59 
     60 @dataclass(frozen=True)
     61 class Punch:
     62     badge: EmployeeId
     63     at: datetime  # always carries a UTC offset
     64     direction: Direction
     65     location: Location
     66 
     67 
```

### 18. vocabulary.py:63

```python
     55 class Location:
     56     file: str  # basename of the punch file
     57     line: int  # 1-based
     58 
     59 
     60 @dataclass(frozen=True)
     61 class Punch:
     62     badge: EmployeeId
>>   63     at: datetime  # always carries a UTC offset
     64     direction: Direction
     65     location: Location
     66 
     67 
     68 @dataclass(frozen=True)
     69 class Problem:
     70     location: Location
     71     badge: str | None  # None when the line carried no string badge
     72     kind: ProblemKind
     73 
```

### 19. vocabulary.py:71

```python
     63     at: datetime  # always carries a UTC offset
     64     direction: Direction
     65     location: Location
     66 
     67 
     68 @dataclass(frozen=True)
     69 class Problem:
     70     location: Location
>>   71     badge: str | None  # None when the line carried no string badge
     72     kind: ProblemKind
     73 
     74 
     75 @dataclass(frozen=True)
     76 class PunchReading:
     77     punches: tuple[Punch, ...]
     78     problems: tuple[Problem, ...]
     79 
     80 
     81 @dataclass(frozen=True)
```

## Run 2 (tests): 1 comments

`scratchpad/cycle6/p1_S_2/tests`

### 20. test_payroll.py:42

```python
     34 
     35 
     36 def testRoundShiftMinutesHalfwayRoundsUp() -> None:
     37     assert roundShiftMinutes(timedelta(minutes=487, seconds=30), 15) == 495
     38     assert roundShiftMinutes(timedelta(minutes=487, seconds=29), 15) == 480
     39 
     40 
     41 def testGrossCentsHalfCentRoundsUp() -> None:
>>   42     # 2400 minutes at 18.20 is 728.00, and 15 overtime minutes at 1.5x is 6.825
     43     assert computeGrossCents(Decimal('18.20'), 2400, 15, Decimal('1.5')) == 73483
     44 
     45 
     46 def testFixturePayroll() -> None:
     47     payroll = computePayroll(FIXTURE_DIR)
     48     week_numbers = [
     49         (week.employee_id, week.week_start, week.regular_minutes, week.overtime_minutes, week.gross_cents)
     50         for week in payroll.weeks
     51     ]
     52     problems = [(problem.location.file, problem.location.line, problem.kind) for problem in payroll.problems]
```
