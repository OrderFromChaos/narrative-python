# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package snapshot_pruner): 9 comments

`scratchpad/cycle8/p3_S_1/snapshot_pruner`

### 1. __main__.py:115

```python
    107 
    108 def parseInstant(raw_now: str) -> DateTime:
    109     """Parse an ISO 8601 instant with a UTC offset, for argparse.
    110 
    111     Raises:
    112         argparse.ArgumentTypeError: the text is not an ISO 8601 date and time, or has no UTC offset.
    113     """
    114     try:
>>  115         # tz=None leaves a string with no offset naive, so the offset test below rejects it
    116         now = pendulum.parse(raw_now, tz=None)
    117     except ValueError as exc:
    118         raise argparse.ArgumentTypeError(f'not an ISO 8601 instant: {raw_now!r}') from exc
    119     if not isinstance(now, DateTime) or now.tzinfo is None:
    120         raise argparse.ArgumentTypeError(f'not an instant with a UTC offset: {raw_now!r}')
    121     return now
    122 
    123 
    124 ### vocabulary #########################################################################
    125 
```

### 2. history.py:51

```python
     43         rules = ','.join(rule.value for rule in kept.rules)
     44         rows.append((*run, kept.snapshot.path.name, kept.snapshot.local.isoformat(), 'keep', rules, None))
     45     for snapshot in plan.delete:
     46         rows.append((*run, snapshot.path.name, snapshot.local.isoformat(), 'delete', '', None))
     47     for problem_file in plan.problems:
     48         rows.append((*run, problem_file.path.name, None, 'keep', '', problem_file.problem.value))
     49 
     50     try:
>>   51         # a connection's context manager commits or rolls back and does not close; closing() closes
     52         with closing(sqlite3.connect(db_path)) as connection, connection:
     53             connection.execute(CREATE_TABLE)
     54             added = connection.executemany(INSERT_ROW, rows).rowcount
     55     except sqlite3.Error as exc:
     56         LOG.error('history.unwritable', extra={'database': str(db_path), 'error': str(exc)})
     57         raise HistoryError(f'{db_path}: {exc}') from exc
     58 
     59     return added
     60 
     61 
```

### 3. history.py:63

```python
     55     except sqlite3.Error as exc:
     56         LOG.error('history.unwritable', extra={'database': str(db_path), 'error': str(exc)})
     57         raise HistoryError(f'{db_path}: {exc}') from exc
     58 
     59     return added
     60 
     61 
     62 def _describePolicy(policy: Policy) -> str:
>>   63     # canonical JSON, so policy files that differ only in layout name one policy
     64     keep = {
     65         Rule.HOURLY.value: policy.hourly,
     66         Rule.DAILY.value: policy.daily,
     67         Rule.WEEKLY.value: policy.weekly,
     68         Rule.MONTHLY.value: policy.monthly,
     69     }
     70     return json.dumps({'timezone': policy.timezone.name, 'keep': keep}, sort_keys=True)
     71 
     72 
     73 ### vocabulary #########################################################################
```

### 4. history.py:76

```python
     68         Rule.MONTHLY.value: policy.monthly,
     69     }
     70     return json.dumps({'timezone': policy.timezone.name, 'keep': keep}, sort_keys=True)
     71 
     72 
     73 ### vocabulary #########################################################################
     74 
     75 
>>   76 # now, snapshot_dir, policy, file, local, decision, rules, problem
     77 _DecisionRow = tuple[str, str, str, str, str | None, str, str, str | None]
```

### 5. policy_file.py:49

```python
     41     raw_keep = raw_policy['keep']
     42     if not isinstance(raw_timezone, str):
     43         raise _rejectPolicy(policy_path, 'timezone must be a string')
     44     rule_names = [rule.value for rule in Rule if rule is not Rule.NEWEST]
     45     if not isinstance(raw_keep, dict) or set(raw_keep) != set(rule_names):
     46         raise _rejectPolicy(policy_path, f'keep must be an object with the keys {", ".join(rule_names)}')
     47 
     48     for name, count in raw_keep.items():
>>   49         # without the bool test, JSON true passes as 1
     50         if isinstance(count, bool) or not isinstance(count, int) or count < 0:
     51             raise _rejectPolicy(policy_path, f'keep.{name} must be a non-negative integer')
     52 
     53     try:
     54         timezone = pendulum.timezone(raw_timezone)
     55     except (ValueError, OSError) as exc:
     56         # without OSError, a tzdata directory name such as America crashes with IsADirectoryError
     57         raise _rejectPolicy(policy_path, f'unknown timezone {raw_timezone!r}') from exc
     58 
     59     return Policy(timezone, raw_keep['hourly'], raw_keep['daily'], raw_keep['weekly'], raw_keep['monthly'])
```

### 6. policy_file.py:56

```python
     48     for name, count in raw_keep.items():
     49         # without the bool test, JSON true passes as 1
     50         if isinstance(count, bool) or not isinstance(count, int) or count < 0:
     51             raise _rejectPolicy(policy_path, f'keep.{name} must be a non-negative integer')
     52 
     53     try:
     54         timezone = pendulum.timezone(raw_timezone)
     55     except (ValueError, OSError) as exc:
>>   56         # without OSError, a tzdata directory name such as America crashes with IsADirectoryError
     57         raise _rejectPolicy(policy_path, f'unknown timezone {raw_timezone!r}') from exc
     58 
     59     return Policy(timezone, raw_keep['hourly'], raw_keep['daily'], raw_keep['weekly'], raw_keep['monthly'])
     60 
     61 
     62 def _rejectPolicy(policy_path: Path, reason: str) -> PolicyError:
     63     LOG.error('policy.rejected', extra={'policy': str(policy_path), 'reason': reason})
     64     return PolicyError(f'{policy_path}: {reason}')
```

### 7. retention.py:57

```python
     49             return policy.monthly
     50         case Rule.NEWEST:
     51             return 1
     52 
     53 
     54 def _computePeriod(rule: Rule, local: DateTime) -> tuple[int, ...]:
     55     match rule:
     56         case Rule.HOURLY:
>>   57             # local.start_of('hour') would split a repeated hour in two: DateTime equality compares instants
     58             return (local.year, local.month, local.day, local.hour)
     59         case Rule.DAILY:
     60             return (local.year, local.month, local.day)
     61         case Rule.WEEKLY:
     62             iso_date = local.isocalendar()
     63             return (iso_date.year, iso_date.week)
     64         case Rule.MONTHLY:
     65             return (local.year, local.month)
     66         case Rule.NEWEST:
     67             return ()
```

### 8. snapshot_listing.py:44

```python
     36     except OSError as exc:
     37         LOG.error('snapshot_dir.unreadable', extra={'snapshot_dir': str(snapshot_dir), 'error': exc.strerror})
     38         raise SnapshotDirectoryError(f'{snapshot_dir}: {exc.strerror}') from exc
     39 
     40     snapshots: list[Snapshot] = []
     41     problems: list[ProblemFile] = []
     42     for path in entries:
     43         name_match = _SNAPSHOT_NAME.fullmatch(path.name)
>>   44         # is_file() follows a symbolic link, so it alone admits a link to a snapshot
     45         if name_match is None or path.is_symlink() or not path.is_file():
     46             LOG.debug('snapshot.ignored', extra={'file': path.name})
     47             continue
     48 
     49         at = _parseSnapshotInstant(name_match)
     50         if at is None:
     51             problems.append(ProblemFile(path, Problem.UNPARSEABLE))
     52         elif at > now:
     53             problems.append(ProblemFile(path, Problem.FUTURE))
     54         else:
```

### 9. vocabulary.py:13

```python
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from pathlib import Path
      8 
      9 from pendulum import DateTime, Timezone
     10 
     11 
     12 class Rule(Enum):
>>   13     # member order is the order plan.json lists a snapshot's rules
     14     HOURLY = 'hourly'
     15     DAILY = 'daily'
     16     WEEKLY = 'weekly'
     17     MONTHLY = 'monthly'
     18     NEWEST = 'newest'
     19 
     20 
     21 class Problem(Enum):
     22     UNPARSEABLE = 'unparseable'
     23     FUTURE = 'future'
```

## Run 2 (package snapshot_pruner): 7 comments

`scratchpad/cycle8/p3_S_2/snapshot_pruner`

### 10. __main__.py:93

```python
     85 
     86     if failed:
     87         return EXIT_DELETION_FAILED
     88     return EXIT_PROBLEMS if plan.problems else EXIT_SUCCESS
     89 
     90 
     91 def parseInstant(raw_now: str) -> DateTime:
     92     try:
>>   93         # tz=None leaves a value without an offset naive, where the default would read it as UTC
     94         now = pendulum.parse(raw_now, tz=None)
     95     except ValueError as exc:
     96         raise argparse.ArgumentTypeError(f'not an ISO 8601 instant: {raw_now}') from exc
     97 
     98     if not isinstance(now, DateTime) or now.tzinfo is None:
     99         raise argparse.ArgumentTypeError(f'needs a date, a time and a UTC offset: {raw_now}')
    100     return now
    101 
    102 
    103 if __name__ == '__main__':
```

### 11. listing.py:23

```python
     15 
     16 import pendulum
     17 from pendulum import DateTime
     18 
     19 from snapshot_pruner.logs import LOG
     20 from snapshot_pruner.vocabulary import FileName, Listing, Problem, ProblemKind, Snapshot, SnapshotDirectoryError
     21 
     22 
>>   23 # db-YYYYMMDDTHHMMSSZ.tar.zst; \d would also match non-ASCII digits such as '٣'
     24 _SNAPSHOT_NAME = re.compile(r'db-([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z\.tar\.zst')
     25 
     26 
     27 def listSnapshots(snapshot_dir: Path, now: DateTime) -> Listing:
     28     """Sort the directory's entries into snapshots and problems, in file name order.
     29 
     30     Raises:
     31         SnapshotDirectoryError: the directory is missing or cannot be listed.
     32     """
     33     if not snapshot_dir.is_dir():
```

### 12. policy.py:46

```python
     38         raw_policy = json.loads(policy_text)
     39     except json.JSONDecodeError as exc:
     40         raise _rejectPolicy(policy_path, f'not JSON: {exc.msg} at line {exc.lineno}') from exc
     41 
     42     if not isinstance(raw_policy, dict) or set(raw_policy) != {'timezone', 'keep'}:
     43         raise _rejectPolicy(policy_path, 'needs exactly the keys timezone and keep')
     44 
     45     raw_timezone = raw_policy['timezone']
>>   46     # zoneinfo raises IsADirectoryError for a region such as 'America', so test membership first
     47     if not isinstance(raw_timezone, str) or raw_timezone not in pendulum.timezones():
     48         raise _rejectPolicy(policy_path, f'unknown timezone {raw_timezone!r}')
     49 
     50     raw_keep = raw_policy['keep']
     51     if not isinstance(raw_keep, dict) or set(raw_keep) != {rule.value for rule in Rule}:
     52         raise _rejectPolicy(policy_path, 'keep needs exactly the keys hourly, daily, weekly and monthly')
     53 
     54     quotas: list[RuleQuota] = []
     55     for rule in Rule:
     56         periods = raw_keep[rule.value]
```

### 13. policy.py:57

```python
     49 
     50     raw_keep = raw_policy['keep']
     51     if not isinstance(raw_keep, dict) or set(raw_keep) != {rule.value for rule in Rule}:
     52         raise _rejectPolicy(policy_path, 'keep needs exactly the keys hourly, daily, weekly and monthly')
     53 
     54     quotas: list[RuleQuota] = []
     55     for rule in Rule:
     56         periods = raw_keep[rule.value]
>>   57         # without the bool test, JSON true passes as 1
     58         if isinstance(periods, bool) or not isinstance(periods, int) or periods < 0:
     59             raise _rejectPolicy(policy_path, f'keep.{rule.value} is not a non-negative integer')
     60         quotas.append(RuleQuota(rule, periods))
     61 
     62     return Policy(pendulum.Timezone(raw_timezone), tuple(quotas))
     63 
     64 
     65 def _rejectPolicy(policy_path: Path, reason: str) -> PolicyError:
     66     LOG.error('policy.rejected', extra={'policy': str(policy_path), 'reason': reason}, stacklevel=2)
     67     return PolicyError(f'{policy_path}: {reason}')
```

### 14. retention.py:73

```python
     65 
     66 
     67 def _selectKeptFiles(newest_first: Sequence[Snapshot], quota: RuleQuota, timezone: Timezone) -> frozenset[FileName]:
     68     newest_by_period: dict[_Period, FileName] = {}
     69     for snapshot in newest_first:
     70         period = _computePeriod(quota.rule, snapshot.instant.in_timezone(timezone))
     71         newest_by_period.setdefault(period, snapshot.file)
     72 
>>   73     # a period ranks by its newest snapshot, and newest-first input inserts periods in that order
     74     return frozenset(list(newest_by_period.values())[: quota.periods])
     75 
     76 
     77 def _computePeriod(rule: Rule, local: DateTime) -> _Period:
     78     match rule:
     79         case Rule.HOURLY:
     80             return (local.year, local.month, local.day, local.hour)
     81         case Rule.DAILY:
     82             return (local.year, local.month, local.day)
     83         case Rule.WEEKLY:
```

### 15. vocabulary.py:42

```python
     34 class Policy:
     35     timezone: Timezone
     36     quotas: tuple[RuleQuota, ...]
     37 
     38 
     39 @dataclass(frozen=True)
     40 class Snapshot:
     41     file: FileName
>>   42     instant: DateTime  # UTC
     43 
     44 
     45 @dataclass(frozen=True)
     46 class Problem:
     47     file: FileName
     48     kind: ProblemKind
     49 
     50 
     51 @dataclass(frozen=True)
     52 class Listing:
```

### 16. vocabulary.py:77

```python
     69     def reasons(self) -> tuple[str, ...]:
     70         newest = ('newest',) if self.newest else ()
     71         return (*(rule.value for rule in self.rules), *newest)
     72 
     73 
     74 @dataclass(frozen=True)
     75 class Plan:
     76     policy: Policy
>>   77     now: DateTime  # UTC
     78     raw_snapshot_dir: str
     79     keep: tuple[Decision, ...]
     80     delete: tuple[Decision, ...]
     81     problems: tuple[Problem, ...]
     82 
     83 
     84 class PolicyError(RuntimeError):
     85     pass
     86 
     87 
```

## Run 2 (tests): 1 comments

`scratchpad/cycle8/p3_S_2/tests`

### 17. test_snapshot_pruner.py:22

```python
     14 from hypothesis import given, settings
     15 from hypothesis import strategies as st
     16 
     17 from snapshot_pruner import PolicyError, computePlan, history
     18 
     19 
     20 FIXTURE_DIR = Path(__file__).resolve().parent.parent / 'fixture'
     21 FIXTURE_NOW = pendulum.datetime(2028, 11, 5, 8, tz='UTC')
>>   22 WINDOW_START_S = 1830297600  # 2028-01-01T00:00:00Z
     23 WINDOW_END_S = WINDOW_START_S + 2 * 366 * 24 * 3600
     24 TIMEZONES = ('America/New_York', 'Europe/London', 'Australia/Lord_Howe', 'Asia/Kathmandu', 'UTC')
     25 
     26 
     27 def testFixturePlan() -> None:
     28     plan = computePlan(str(FIXTURE_DIR / 'snapshots'), FIXTURE_DIR / 'policy.json', FIXTURE_NOW)
     29 
     30     assert [(decision.snapshot.file, decision.reasons) for decision in plan.keep] == [
     31         ('db-20281105T073000Z.tar.zst', ('hourly', 'daily', 'weekly', 'monthly', 'newest')),
     32         ('db-20281105T063000Z.tar.zst', ('hourly',)),
```
