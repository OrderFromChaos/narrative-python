# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package invoicing): 13 comments

`scratchpad/cycle7/p2_S_1/invoicing`

### 1. events.py:130

```python
    122     if isinstance(raw_plan, str) and not raw_plan:
    123         return None
    124 
    125     plan = PlanName(raw_plan) if isinstance(raw_plan, str) else None
    126     return Event(customer_id, at, kind, plan)
    127 
    128 
    129 def _parseInstant(raw_at: str) -> DateTime | None:
>>  130     # None unless raw_at is an ISO 8601 date and time with a UTC offset
    131     try:
    132         at = pendulum.parse(raw_at, tz=None)
    133     except ValueError:
    134         return None
    135     if not isinstance(at, DateTime) or at.tzinfo is None:
    136         return None
    137 
    138     return at
    139 
    140 
```

### 2. money.py:19

```python
     11 from __future__ import annotations
     12 
     13 import math
     14 import re
     15 from fractions import Fraction
     16 
     17 
     18 def parseCents(raw_dollars: str) -> int | None:
>>   19     # None when the text is not a dollar amount with exactly two decimal places
     20     if re.fullmatch(r'[0-9]+\.[0-9]{2}', raw_dollars) is None:
     21         return None
     22 
     23     whole, fraction = raw_dollars.split('.')
     24     return int(whole) * 100 + int(fraction)
     25 
     26 
     27 def formatCents(cents: int) -> str:
     28     return f'{cents // 100}.{cents % 100:02d}'
     29 
```

### 3. reference.py:81

```python
     73     """
     74     try:
     75         customers_text = customers_path.read_bytes().decode('utf-8-sig')
     76     except OSError as exc:
     77         raise _rejectReference(customers_path, f'unreadable: {exc.strerror}') from exc
     78     except UnicodeDecodeError as exc:
     79         raise _rejectReference(customers_path, f'not UTF-8: {exc.reason}') from exc
     80 
>>   81     # newline='' leaves a newline quoted inside a field intact
     82     reader = csv.reader(io.StringIO(customers_text, newline=''), strict=True)
     83     try:
     84         rows = list(reader)
     85     except csv.Error as exc:
     86         raise _rejectReference(customers_path, f'not CSV: {exc}') from exc
     87 
     88     if not rows or rows[0] != _CUSTOMERS_HEADER:
     89         raise _rejectReference(customers_path, f'header is not {",".join(_CUSTOMERS_HEADER)}')
     90 
     91     customers: dict[CustomerId, Customer] = {}
```

### 4. timeline.py:56

```python
     48                 LOG.debug('timeline.out_of_order', extra={'file': sourced.source.file, 'line': sourced.source.line})
     49                 problems.append(Problem(sourced.source, customer_id, ProblemKind.OUT_OF_ORDER))
     50                 continue
     51             if active is not None and event.plan == active.plan:
     52                 continue
     53 
     54             if active is not None:
     55                 customer_stretches.append(PlanStretch(active.plan, active.since, event.at))
>>   56             # a cancel's plan is None, so a cancel leaves no active plan
     57             active = None if event.plan is None else _ActivePlan(event.plan, event.at)
     58 
     59         if active is not None:
     60             customer_stretches.append(PlanStretch(active.plan, active.since, None))
     61         stretches[customer_id] = tuple(customer_stretches)
     62 
     63     return Replay(stretches, tuple(problems))
     64 
     65 
     66 def _inOrder(kind: EventKind, *, subscribed: bool) -> bool:
```

### 5. vocabulary.py:64

```python
     56     customer_id: CustomerId
     57     name: str
     58     zone: Timezone
     59     state: StateCode
     60 
     61 
     62 @dataclass(frozen=True)
     63 class SourceLine:
>>   64     file: str  # basename, as the report names it
     65     line: int
     66 
     67 
     68 @dataclass(frozen=True)
     69 class Event:
     70     """One subscription event. Two resent copies of an event compare equal."""
     71 
     72     customer_id: CustomerId
     73     at: DateTime
     74     kind: EventKind
```

### 6. vocabulary.py:75

```python
     67 
     68 @dataclass(frozen=True)
     69 class Event:
     70     """One subscription event. Two resent copies of an event compare equal."""
     71 
     72     customer_id: CustomerId
     73     at: DateTime
     74     kind: EventKind
>>   75     plan: PlanName | None  # None exactly when kind is CANCEL
     76 
     77 
     78 @dataclass(frozen=True)
     79 class SourcedEvent:
     80     event: Event
     81     source: SourceLine
     82 
     83 
     84 @dataclass(frozen=True)
     85 class Problem:
```

### 7. vocabulary.py:87

```python
     79 class SourcedEvent:
     80     event: Event
     81     source: SourceLine
     82 
     83 
     84 @dataclass(frozen=True)
     85 class Problem:
     86     source: SourceLine
>>   87     customer_id: CustomerId | None  # None when a malformed line names no customer as a string
     88     kind: ProblemKind
     89 
     90 
     91 @dataclass(frozen=True)
     92 class EventLog:
     93     events: tuple[SourcedEvent, ...]  # read order, problems and duplicates removed
     94     problems: tuple[Problem, ...]
     95     line_count: int
     96     duplicate_count: int
     97 
```

### 8. vocabulary.py:93

```python
     85 class Problem:
     86     source: SourceLine
     87     customer_id: CustomerId | None  # None when a malformed line names no customer as a string
     88     kind: ProblemKind
     89 
     90 
     91 @dataclass(frozen=True)
     92 class EventLog:
>>   93     events: tuple[SourcedEvent, ...]  # read order, problems and duplicates removed
     94     problems: tuple[Problem, ...]
     95     line_count: int
     96     duplicate_count: int
     97 
     98 
     99 @dataclass(frozen=True)
    100 class PlanStretch:
    101     plan: PlanName
    102     start: DateTime
    103     end: DateTime | None  # None while the plan is still active after the last event
```

### 9. vocabulary.py:103

```python
     95     line_count: int
     96     duplicate_count: int
     97 
     98 
     99 @dataclass(frozen=True)
    100 class PlanStretch:
    101     plan: PlanName
    102     start: DateTime
>>  103     end: DateTime | None  # None while the plan is still active after the last event
    104 
    105 
    106 @dataclass(frozen=True)
    107 class Replay:
    108     stretches: Mapping[CustomerId, tuple[PlanStretch, ...]]
    109     problems: tuple[Problem, ...]
    110 
    111 
    112 @dataclass(frozen=True)
    113 class InvoiceLine:
```

### 10. vocabulary.py:115

```python
    107 class Replay:
    108     stretches: Mapping[CustomerId, tuple[PlanStretch, ...]]
    109     problems: tuple[Problem, ...]
    110 
    111 
    112 @dataclass(frozen=True)
    113 class InvoiceLine:
    114     plan: PlanName
>>  115     start: DateTime  # in the customer's zone
    116     end: DateTime
    117     amount_cents: int
    118 
    119 
    120 @dataclass(frozen=True)
    121 class Invoice:
    122     customer: Customer
    123     lines: tuple[InvoiceLine, ...]
    124     subtotal_cents: int
    125     tax_cents: int
```

### 11. vocabulary.py:132

```python
    124     subtotal_cents: int
    125     tax_cents: int
    126     total_cents: int
    127 
    128 
    129 @dataclass(frozen=True)
    130 class BillingResult:
    131     month: BillingMonth
>>  132     invoices: tuple[Invoice, ...]  # sorted by customer_id
    133     problems: tuple[Problem, ...]  # sorted by (file, line)
    134     customers: tuple[Customer, ...]  # every customer of customers.csv, invoiced or not
    135     event_count: int
    136     duplicate_count: int
    137     billed_cents: int
```

### 12. vocabulary.py:133

```python
    125     tax_cents: int
    126     total_cents: int
    127 
    128 
    129 @dataclass(frozen=True)
    130 class BillingResult:
    131     month: BillingMonth
    132     invoices: tuple[Invoice, ...]  # sorted by customer_id
>>  133     problems: tuple[Problem, ...]  # sorted by (file, line)
    134     customers: tuple[Customer, ...]  # every customer of customers.csv, invoiced or not
    135     event_count: int
    136     duplicate_count: int
    137     billed_cents: int
```

### 13. vocabulary.py:134

```python
    126     total_cents: int
    127 
    128 
    129 @dataclass(frozen=True)
    130 class BillingResult:
    131     month: BillingMonth
    132     invoices: tuple[Invoice, ...]  # sorted by customer_id
    133     problems: tuple[Problem, ...]  # sorted by (file, line)
>>  134     customers: tuple[Customer, ...]  # every customer of customers.csv, invoiced or not
    135     event_count: int
    136     duplicate_count: int
    137     billed_cents: int
```

## Run 1 (tests): 1 comments

`scratchpad/cycle7/p2_S_1/tests`

### 14. test_invoicing.py:74

```python
     66     exact = Fraction(numerator, denominator)
     67     rounded = money.roundHalfUp(exact)
     68 
     69     assert -Fraction(1, 2) < rounded - exact <= Fraction(1, 2)
     70 
     71 
     72 @given(st.sampled_from(ZONES), st.integers(min_value=2000, max_value=2040), st.integers(min_value=1, max_value=12))
     73 def testWholeMonthBillsFullPrice(zone_name: str, year: int, month: int) -> None:
>>   74     # subscribed long before the month, in any zone, so DST changes the month's length but not its price
     75     with tempfile.TemporaryDirectory() as scratch_dir:
     76         input_dir = Path(scratch_dir)
     77         prices = {'plans': {'pro': '29.00'}, 'tax_rates': {'CA': '0'}}
     78         subscribe = {'customer': 'C1', 'at': '1999-01-01T00:00:00+00:00', 'event': 'subscribe', 'plan': 'pro'}
     79         (input_dir / 'prices.json').write_text(json.dumps(prices), encoding='utf-8')
     80         (input_dir / 'customers.csv').write_text(
     81             f'customer_id,name,timezone,state\nC1,A,{zone_name},CA\n',
     82             encoding='utf-8',
     83         )
     84         (input_dir / 'a.events.jsonl').write_text(json.dumps(subscribe) + '\n', encoding='utf-8')
```

## Run 2 (package invoicing): 4 comments

`scratchpad/cycle7/p2_S_2/invoicing`

### 15. events.py:54

```python
     46     """
     47     events: dict[Event, None] = {}
     48     problems: list[Problem] = []
     49     lines_read = 0
     50     duplicates = 0
     51 
     52     for events_path in sorted(path for path in input_dir.glob(_EVENTS_GLOB) if path.is_file()):
     53         try:
>>   54             # read_text() would fail the whole file on one line that is not UTF-8
     55             events_bytes = events_path.read_bytes()
     56         except OSError as exc:
     57             raise logs.rejectInput('events.rejected', events_path, exc.strerror or 'unreadable') from exc
     58 
     59         for line_number, raw_line in enumerate(events_bytes.splitlines(), start=1):
     60             lines_read += 1
     61             source = SourceLine(events_path.name, line_number)
     62             classified = _classifyLine(raw_line, source, customers, price_list)
     63             if isinstance(classified, Problem):
     64                 problems.append(classified)
```

### 16. events.py:136

```python
    128 def _parseInstant(raw_at: object) -> DateTime | None:
    129     """Return None unless the value is an ISO 8601 date and time with a UTC offset."""
    130     if not isinstance(raw_at, str):
    131         return None
    132     try:
    133         at = pendulum.parse(raw_at, tz=None, exact=True)
    134     except ParserError:
    135         return None
>>  136     # without tz=None, a time with no offset parses as UTC
    137     if not isinstance(at, DateTime) or at.tzinfo is None:
    138         return None
    139     return at
```

### 17. money.py:20

```python
     12 
     13 import math
     14 import re
     15 from fractions import Fraction
     16 
     17 from invoicing.vocabulary import Cents
     18 
     19 
>>   20 _DOLLARS_PATTERN = re.compile(r'([0-9]+)\.([0-9]{2})')  # \d would admit non-ASCII digits
     21 
     22 
     23 def parseCents(raw_dollars: str) -> Cents | None:
     24     """Return None when the text is not a dollar amount with exactly two decimal places."""
     25     matched = _DOLLARS_PATTERN.fullmatch(raw_dollars)
     26     if matched is None:
     27         return None
     28     return Cents(int(matched[1]) * 100 + int(matched[2]))
     29 
     30 
```

### 18. vocabulary.py:60

```python
     52 
     53 
     54 @dataclass(frozen=True, order=True)
     55 class SourceLine:
     56     file: str
     57     line: int
     58 
     59 
>>   60 # source is left out of comparison and hashing, so a resent event compares equal to the first copy
     61 @dataclass(frozen=True)
     62 class Subscribe:
     63     customer_id: CustomerId
     64     at: DateTime
     65     plan: PlanName
     66     source: SourceLine = field(compare=False)
     67 
     68 
     69 @dataclass(frozen=True)
     70 class Change:
```
