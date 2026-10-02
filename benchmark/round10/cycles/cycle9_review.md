# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package license_audit): 9 comments

`scratchpad/cycle9/p4_X_1/license_audit`

### 1. dates.py:9

```python
      1 """Parse the calendar dates of the audit, from `--today` and from the `until` of a policy exception."""
      2 
      3 from __future__ import annotations
      4 
      5 import pendulum
      6 
      7 
      8 def parseCalendarDate(raw_date: str) -> pendulum.Date:
>>    9     # raises ValueError for a string that is not YYYY-MM-DD or names no real day
     10     return pendulum.from_format(raw_date, 'YYYY-MM-DD').date()
```

### 2. expression.py:23

```python
     15 from collections import deque
     16 from collections.abc import Callable
     17 
     18 from license_audit.logs import LOG
     19 from license_audit.names import foldLicenseId
     20 from license_audit.vocabulary import AllOf, AnyOf, ExpressionNode, ExpressionSyntaxError, LicenseKey, LicenseLeaf
     21 
     22 
>>   23 _TOKEN = re.compile(r'\(|\)|[^\s()]+')  # a parenthesis, or a run of anything else up to whitespace
     24 _OPERATORS = frozenset({'AND', 'OR', '(', ')'})
     25 
     26 
     27 def parseLicenseExpression(expression_text: str) -> ExpressionNode:
     28     """Build the tree of one license expression.
     29 
     30     Raises:
     31         ExpressionSyntaxError: The text is empty, has unbalanced parentheses, or has an operator
     32             or id out of place.
     33     """
```

### 3. lockfile.py:27

```python
     19 
     20 
     21 def readLockFile(lock_path: Path) -> LockFile:
     22     """Parse every line of one lock file.
     23 
     24     Raises:
     25         UnusableInputError: The file is unreadable or not UTF-8.
     26     """
>>   27     # name, '==', version, then an optional '; marker' and an optional '# comment'
     28     PIN = re.compile(
     29         r'(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*==\s*(?P<version>[^\s;#]+)'
     30         r'\s*(?:;\s*[^\s#][^#]*)?(?:#.*)?',
     31     )
     32     lock = LockName(lock_path.name)
     33     try:
     34         lock_text = lock_path.read_text(encoding='utf-8')
     35     except OSError as exc:
     36         raise _rejectLockFile(lock_path, f'unreadable: {exc.strerror}') from exc
     37     except UnicodeDecodeError as exc:
```

### 4. vocabulary.py:13

```python
      5 from collections.abc import Mapping
      6 from dataclasses import dataclass
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
>>   13 PackageName = NewType('PackageName', str)  # PEP 503 normalised: lower case, separators folded to '-'
     14 LicenseKey = NewType('LicenseKey', str)  # case-folded SPDX license id, for comparison only
     15 LockName = NewType('LockName', str)  # file name of a lock file inside the input directory
     16 
     17 
     18 class Verdict(Enum):
     19     ALLOWED = 'allowed'
     20     DENIED = 'denied'
     21     UNREVIEWED = 'unreviewed'
     22     UNKNOWN_LICENSE = 'unknown license'
     23 
```

### 5. vocabulary.py:14

```python
      6 from dataclasses import dataclass
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
     13 PackageName = NewType('PackageName', str)  # PEP 503 normalised: lower case, separators folded to '-'
>>   14 LicenseKey = NewType('LicenseKey', str)  # case-folded SPDX license id, for comparison only
     15 LockName = NewType('LockName', str)  # file name of a lock file inside the input directory
     16 
     17 
     18 class Verdict(Enum):
     19     ALLOWED = 'allowed'
     20     DENIED = 'denied'
     21     UNREVIEWED = 'unreviewed'
     22     UNKNOWN_LICENSE = 'unknown license'
     23 
     24 
```

### 6. vocabulary.py:15

```python
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 import pendulum
     11 
     12 
     13 PackageName = NewType('PackageName', str)  # PEP 503 normalised: lower case, separators folded to '-'
     14 LicenseKey = NewType('LicenseKey', str)  # case-folded SPDX license id, for comparison only
>>   15 LockName = NewType('LockName', str)  # file name of a lock file inside the input directory
     16 
     17 
     18 class Verdict(Enum):
     19     ALLOWED = 'allowed'
     20     DENIED = 'denied'
     21     UNREVIEWED = 'unreviewed'
     22     UNKNOWN_LICENSE = 'unknown license'
     23 
     24 
     25 @dataclass(frozen=True)
```

### 7. vocabulary.py:66

```python
     58     operands: tuple[ExpressionNode, ...]
     59 
     60 
     61 ExpressionNode: TypeAlias = LicenseLeaf | AllOf | AnyOf
     62 
     63 
     64 @dataclass(frozen=True)
     65 class LicenseExpression:
>>   66     text: str  # as written in licenses.json
     67     root: ExpressionNode
     68 
     69 
     70 @dataclass(frozen=True)
     71 class Release:
     72     package: PackageName
     73     version: str
     74 
     75 
     76 LicenseCatalog: TypeAlias = Mapping[Release, LicenseExpression]
```

### 8. vocabulary.py:82

```python
     74 
     75 
     76 LicenseCatalog: TypeAlias = Mapping[Release, LicenseExpression]
     77 
     78 
     79 @dataclass(frozen=True)
     80 class PolicyException:
     81     package: PackageName
>>   82     license_id: str  # as written in policy.json
     83     until: pendulum.Date
     84     reason: str | None
     85 
     86 
     87 @dataclass(frozen=True)
     88 class Policy:
     89     allowed: frozenset[LicenseKey]
     90     denied: frozenset[LicenseKey]
     91     exceptions: tuple[PolicyException, ...]
     92 
```

### 9. vocabulary.py:97

```python
     89     allowed: frozenset[LicenseKey]
     90     denied: frozenset[LicenseKey]
     91     exceptions: tuple[PolicyException, ...]
     92 
     93 
     94 @dataclass(frozen=True)
     95 class AuditedEntry:
     96     entry: LockEntry
>>   97     license_text: str | None  # None when licenses.json lists no expression for the release
     98     verdict: Verdict
     99 
    100 
    101 @dataclass(frozen=True)
    102 class Audit:
    103     today: pendulum.Date
    104     entries: tuple[AuditedEntry, ...]
    105     expired_exceptions: tuple[PolicyException, ...]
    106     malformed: tuple[MalformedLine, ...]
    107 
```

## Run 2 (package license_audit): 15 comments

`scratchpad/cycle9/p4_X_2/license_audit`

### 10. __main__.py:133

```python
    125     return today
    126 
    127 
    128 ### vocabulary #########################################################################
    129 
    130 
    131 @dataclass(frozen=True)
    132 class CommandLine:
>>  133     raw_input_dir: str  # echoed into audit.json as typed
    134     today: Date
    135     policy_path: Path | None
    136     output_path: Path
    137     database_path: Path
    138     verbose: bool
    139 
    140 
    141 if __name__ == '__main__':
    142     sys.exit(main())
```

### 11. input_gate.py:39

```python
     31     except json.JSONDecodeError as exc:
     32         raise rejectInput(json_path, f'invalid JSON at line {exc.lineno}') from exc
     33     if not isinstance(document, dict):
     34         raise rejectInput(json_path, 'top level is not an object')
     35     return document
     36 
     37 
     38 def rejectInput(input_path: Path, reason: str) -> AuditInputError:
>>   39     # stacklevel=2 attributes the record to the raise site in the caller
     40     LOG.error('input.rejected', extra={'path': input_path, 'reason': reason}, stacklevel=2)
     41     return AuditInputError(f'{input_path}: {reason}')
```

### 12. license_expression.py:54

```python
     46 def parseLicenseId(raw_license_id: str) -> LicenseId | None:
     47     LICENSE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9.+:-]*')
     48     if raw_license_id in {operator.value for operator in Operator} or not LICENSE_ID.fullmatch(raw_license_id):
     49         return None
     50     return LicenseId(raw_license_id.lower())
     51 
     52 
     53 def _parseOperands(tokens: Sequence[str], start: int, operator: Operator) -> _Parsed | None:
>>   54     # one precedence level: operands joined by operator
     55     first = _parseOperand(tokens, start, operator)
     56     if first is None:
     57         return None
     58     operands = [first.expression]
     59     end = first.end
     60     while end < len(tokens) and tokens[end] == operator.value:
     61         following = _parseOperand(tokens, end + 1, operator)
     62         if following is None:
     63             return None
     64         operands.append(following.expression)
```

### 13. license_expression.py:73

```python
     65         end = following.end
     66 
     67     if len(operands) == 1:
     68         return first
     69     return _Parsed(Compound(operator, tuple(operands)), end)
     70 
     71 
     72 def _parseOperand(tokens: Sequence[str], start: int, operator: Operator) -> _Parsed | None:
>>   73     # an OR operand is an AND chain, so AND binds tighter
     74     match operator:
     75         case Operator.OR:
     76             return _parseOperands(tokens, start, Operator.AND)
     77         case Operator.AND:
     78             return _parseAtom(tokens, start)
     79 
     80 
     81 def _parseAtom(tokens: Sequence[str], start: int) -> _Parsed | None:
     82     if start >= len(tokens):
     83         return None
```

### 14. license_expression.py:102

```python
     94 
     95 
     96 ### vocabulary #########################################################################
     97 
     98 
     99 @dataclass(frozen=True)
    100 class _Parsed:
    101     expression: LicenseExpression
>>  102     end: int  # index of the first token after the expression
```

### 15. lockfile.py:30

```python
     22 def readLockFile(lock_path: Path) -> LockReadout:
     23     """Read the pins and the malformed lines of one lock file, both in line order.
     24 
     25     Raises:
     26         AuditInputError: the file is unreadable or not UTF-8.
     27     """
     28     PIN = re.compile(
     29         r'(?P<name>[^\s=;#]+)==(?P<version>[A-Za-z0-9.!+_-]+)'
>>   30         r'(?:\s*;\s*[^#\s][^#]*?)?'  # environment marker
     31         r'(?:\s+#.*)?',  # inline comment
     32     )
     33     lock = LockName(lock_path.name)
     34     lock_text = readInputText(lock_path)
     35 
     36     pins = []
     37     malformed = []
     38     # splitlines() would also split at form feeds and other separators, which shifts line numbers
     39     for line_number, raw_line in enumerate(lock_text.split('\n'), start=1):
     40         line = raw_line.strip()
```

### 16. lockfile.py:31

```python
     23     """Read the pins and the malformed lines of one lock file, both in line order.
     24 
     25     Raises:
     26         AuditInputError: the file is unreadable or not UTF-8.
     27     """
     28     PIN = re.compile(
     29         r'(?P<name>[^\s=;#]+)==(?P<version>[A-Za-z0-9.!+_-]+)'
     30         r'(?:\s*;\s*[^#\s][^#]*?)?'  # environment marker
>>   31         r'(?:\s+#.*)?',  # inline comment
     32     )
     33     lock = LockName(lock_path.name)
     34     lock_text = readInputText(lock_path)
     35 
     36     pins = []
     37     malformed = []
     38     # splitlines() would also split at form feeds and other separators, which shifts line numbers
     39     for line_number, raw_line in enumerate(lock_text.split('\n'), start=1):
     40         line = raw_line.strip()
     41         if not line or line.startswith('#'):
```

### 17. lockfile.py:38

```python
     30         r'(?:\s*;\s*[^#\s][^#]*?)?'  # environment marker
     31         r'(?:\s+#.*)?',  # inline comment
     32     )
     33     lock = LockName(lock_path.name)
     34     lock_text = readInputText(lock_path)
     35 
     36     pins = []
     37     malformed = []
>>   38     # splitlines() would also split at form feeds and other separators, which shifts line numbers
     39     for line_number, raw_line in enumerate(lock_text.split('\n'), start=1):
     40         line = raw_line.strip()
     41         if not line or line.startswith('#'):
     42             continue
     43 
     44         pin = PIN.fullmatch(line)
     45         package = parsePackageName(pin['name']) if pin else None
     46         if pin is None or package is None:
     47             LOG.debug('lock.line_malformed', extra={'lock': lock, 'line': line_number})
     48             malformed.append(MalformedLine(lock, line_number, line))
```

### 18. package_name.py:19

```python
     11 from __future__ import annotations
     12 
     13 import re
     14 
     15 from license_audit.vocabulary import PackageName
     16 
     17 
     18 def parsePackageName(raw_name: str) -> PackageName | None:
>>   19     VALID_NAME = re.compile(r'[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?')  # PEP 508
     20     SEPARATOR_RUN = re.compile(r'[-_.]+')
     21     if not VALID_NAME.fullmatch(raw_name):
     22         return None
     23     return PackageName(SEPARATOR_RUN.sub('-', raw_name).lower())
```

### 19. policy.py:56

```python
     48     policy: Policy,
     49     package: PackageName,
     50     expression: LicenseExpression,
     51     today: Date,
     52 ) -> Verdict:
     53     """Judge one license expression of package against the policy as it stands today."""
     54     if satisfiable(expression, lambda license_id: _usable(policy, package, license_id, today)):
     55         return Verdict.ALLOWED
>>   56     # denied when every way to satisfy the expression needs a denied id
     57     if not satisfiable(expression, lambda license_id: license_id not in policy.denied):
     58         return Verdict.DENIED
     59     return Verdict.UNREVIEWED
     60 
     61 
     62 def selectExpiredExceptions(policy: Policy, today: Date) -> tuple[PolicyException, ...]:
     63     expired = {exception for exception in policy.exceptions if exception.until < today}
     64     return tuple(sorted(expired, key=lambda exception: (exception.package, exception.license_id, exception.until)))
     65 
     66 
```

### 20. store.py:34

```python
     26 
     27     Raises:
     28         sqlite3.Error: the database cannot be opened or written.
     29     """
     30     SCHEMA = (
     31         'CREATE TABLE IF NOT EXISTS verdict ('
     32         ' audit_date TEXT NOT NULL, input_dir TEXT NOT NULL, lock TEXT NOT NULL, line INTEGER NOT NULL,'
     33         ' package TEXT NOT NULL, version TEXT NOT NULL, license TEXT, verdict TEXT NOT NULL);'
>>   34         # COALESCE: a unique index treats every NULL as distinct, so unknown-license rows would repeat
     35         'CREATE UNIQUE INDEX IF NOT EXISTS verdict_once ON verdict'
     36         " (audit_date, input_dir, lock, line, package, version, COALESCE(license, ''), verdict);"
     37     )
     38     INSERT = (
     39         'INSERT OR IGNORE INTO verdict (audit_date, input_dir, lock, line, package, version, license, verdict)'
     40         ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
     41     )
     42     resolved_input_dir = str(input_dir.resolve())
     43     rows = [
     44         (
```

### 21. vocabulary.py:13

```python
      5 from collections.abc import Mapping
      6 from dataclasses import dataclass
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 from pendulum import Date
     11 
     12 
>>   13 PackageName = NewType('PackageName', str)  # PEP 503 normalised
     14 Version = NewType('Version', str)
     15 LockName = NewType('LockName', str)  # file name of a lock file, without its directory
     16 LicenseId = NewType('LicenseId', str)  # lower case
     17 
     18 
     19 class Verdict(Enum):
     20     ALLOWED = 'allowed'
     21     DENIED = 'denied'
     22     UNREVIEWED = 'unreviewed'
     23     UNKNOWN_LICENSE = 'unknown license'
```

### 22. vocabulary.py:15

```python
      7 from enum import Enum
      8 from typing import NewType, TypeAlias
      9 
     10 from pendulum import Date
     11 
     12 
     13 PackageName = NewType('PackageName', str)  # PEP 503 normalised
     14 Version = NewType('Version', str)
>>   15 LockName = NewType('LockName', str)  # file name of a lock file, without its directory
     16 LicenseId = NewType('LicenseId', str)  # lower case
     17 
     18 
     19 class Verdict(Enum):
     20     ALLOWED = 'allowed'
     21     DENIED = 'denied'
     22     UNREVIEWED = 'unreviewed'
     23     UNKNOWN_LICENSE = 'unknown license'
     24 
     25 
```

### 23. vocabulary.py:16

```python
      8 from typing import NewType, TypeAlias
      9 
     10 from pendulum import Date
     11 
     12 
     13 PackageName = NewType('PackageName', str)  # PEP 503 normalised
     14 Version = NewType('Version', str)
     15 LockName = NewType('LockName', str)  # file name of a lock file, without its directory
>>   16 LicenseId = NewType('LicenseId', str)  # lower case
     17 
     18 
     19 class Verdict(Enum):
     20     ALLOWED = 'allowed'
     21     DENIED = 'denied'
     22     UNREVIEWED = 'unreviewed'
     23     UNKNOWN_LICENSE = 'unknown license'
     24 
     25 
     26 class Operator(Enum):
```

### 24. vocabulary.py:99

```python
     91     allowed: frozenset[LicenseId]
     92     denied: frozenset[LicenseId]
     93     exceptions: tuple[PolicyException, ...]
     94 
     95 
     96 @dataclass(frozen=True)
     97 class AuditEntry:
     98     pin: Pin
>>   99     published_license: PublishedLicense | None  # None when licenses.json lists no license for the release
    100     verdict: Verdict
    101 
    102 
    103 @dataclass(frozen=True)
    104 class VerdictTotals:
    105     entries: int
    106     allowed: int
    107     denied: int
    108     unreviewed: int
    109     unknown: int
```
