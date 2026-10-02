# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package billing_reconciler): 6 comments

`scratchpad/cycle5/v6_S_1/billing_reconciler`

### 1. __main__.py:49

```python
     41 
     42 DEFAULT_REPORT_PATH = Path('report.json')
     43 DEFAULT_DATABASE_PATH = Path('reconcile.db')
     44 
     45 
     46 def main() -> int:
     47     """Reconcile the input directory, write the report and the database, and print the summary."""
     48     parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
>>   49     # type=Path would drop a trailing slash or a leading ./, and the report states input_dir as given
     50     parser.add_argument('input_dir')
     51     parser.add_argument('--rules', type=Path, help=f'default: INPUT_DIR/{rules_file.RULES_FILE_NAME}')
     52     parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH)
     53     parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH)
     54     parser.add_argument('--verbose', action='store_true', help='log every rejected record')
     55     args = parser.parse_args()
     56 
     57     logs.configureLogging(verbose=args.verbose)
     58     input_dir = Path(args.input_dir)
     59     rules_path = input_dir / rules_file.RULES_FILE_NAME if args.rules is None else args.rules
```

### 2. __main__.py:61

```python
     53     parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH)
     54     parser.add_argument('--verbose', action='store_true', help='log every rejected record')
     55     args = parser.parse_args()
     56 
     57     logs.configureLogging(verbose=args.verbose)
     58     input_dir = Path(args.input_dir)
     59     rules_path = input_dir / rules_file.RULES_FILE_NAME if args.rules is None else args.rules
     60 
>>   61     # read-only: NEVER write inside the input directory
     62     for output_path in (args.report, args.database):
     63         if output_path.resolve().is_relative_to(input_dir.resolve()):
     64             LOG.error('run.output_inside_input_dir', extra={'output_path': str(output_path)})
     65             return ExitCode.UNUSABLE.value
     66 
     67     try:
     68         reconciliation = reconcile.reconcileDirectory(input_dir, rules_path)
     69     except (InputDirectoryError, RulesError):
     70         return ExitCode.UNUSABLE.value
     71 
```

### 3. billing_csv.py:50

```python
     42 def _parseBillingRow(fields: list[str], line_number: int, file_name: str) -> BillingLine | RejectedRow:
     43     location = f'line {line_number}'
     44     if len(fields) != len(_HEADER):
     45         return RejectedRow(location, f'{len(fields)} fields, expected {len(_HEADER)}')
     46 
     47     resource_id, sku, cents_text, region = fields
     48     if not resource_id or not sku or not region:
     49         return RejectedRow(location, 'resource_id, sku or region is empty')
>>   50     # isdigit() alone admits non-ASCII digits such as '²'
     51     if not (cents_text.isascii() and cents_text.isdigit()):
     52         return RejectedRow(location, f'monthly_cents {cents_text!r} is not a run of digits')
     53 
     54     return BillingLine(
     55         resource_id=ResourceId(resource_id),
     56         sku=Sku(sku),
     57         monthly_cents=int(cents_text),
     58         region=RegionName(region),
     59         source=file_name,
     60         location=location,
```

### 4. join.py:45

```python
     37         (resource for resource_id, resource in scanned.items() if resource_id not in billed),
     38         key=lambda resource: resource.resource_id,
     39     )
     40     matched_pairs = [
     41         (billed[resource_id], scanned[resource_id]) for resource_id in sorted(billed.keys() & scanned.keys())
     42     ]
     43 
     44     aliases = rules.region_aliases
>>   45     # aliases resolve one hop per side, never transitively
     46     mismatched_pairs = [
     47         (line, resource)
     48         for line, resource in matched_pairs
     49         if aliases.get(line.region, line.region) != aliases.get(resource.region, resource.region)
     50     ]
     51 
     52     findings = (
     53         *(_findBilledNotFound(line, rules.grace_cents) for line in unmatched_lines),
     54         *(_findFoundNotBilled(resource) for resource in unbilled_resources),
     55         *(_findRegionMismatch(line, resource) for line, resource in mismatched_pairs),
```

### 5. rules_file.py:63

```python
     55 
     56     ignored_skus = document['ignored_skus']
     57     if not isinstance(ignored_skus, list) or not all(isinstance(sku, str) for sku in ignored_skus):
     58         raise _rejectRules(rules_path, 'ignored_skus is not a list of strings')
     59     region_aliases = document['region_aliases']
     60     if not isinstance(region_aliases, dict) or not all(isinstance(target, str) for target in region_aliases.values()):
     61         raise _rejectRules(rules_path, 'region_aliases is not an object of string to string')
     62     grace_cents = document['grace_cents']
>>   63     # without the bool test, JSON true passes as 1
     64     if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
     65         raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')
     66 
     67     return ReconcileRules(
     68         ignored_skus=frozenset(Sku(sku) for sku in ignored_skus),
     69         region_aliases={RegionName(name): RegionName(region_aliases[name]) for name in sorted(region_aliases)},
     70         grace_cents=grace_cents,
     71     )
     72 
     73 
```

### 6. store.py:51

```python
     43             finding.sku,
     44             finding.monthly_cents,
     45             finding.team,
     46             finding.billed_region,
     47             finding.scanned_region,
     48             finding.above_grace,
     49             json.dumps(finding.sources),
     50         )
>>   51         # SQLite treats each NULL as distinct under PRIMARY KEY, so a key over the nullable columns
>>   52         # would admit a duplicate row
     53         rows.append((json.dumps(values), *values, first_seen))
     54 
     55     try:
     56         with closing(sqlite3.connect(database_path)) as connection, connection:
     57             connection.execute(SCHEMA)
     58             changes_before = connection.total_changes
     59             connection.executemany(INSERT, rows)
     60             added = connection.total_changes - changes_before
     61     except sqlite3.Error as exc:
     62         LOG.error('store.unwritable', extra={'database_path': str(database_path), 'reason': str(exc)})
```

## Run 2 (package reconciler): 7 comments

`scratchpad/cycle5/v6_S_2/reconciler`

### 7. __main__.py:61

```python
     53         help=f'rules file (default: {reconciliation.RULES_FILE_NAME} in input_dir)',
     54     )
     55     parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='JSON report to write')
     56     parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='SQLite database of findings')
     57     parser.add_argument('--verbose', action='store_true', help='log every rejected record')
     58     args = parser.parse_args()
     59     logs.configureLogging(verbose=args.verbose)
     60 
>>   61     # read-only: NEVER write inside the input directory
     62     input_dir = Path(args.input_dir)
     63     for output_path in (args.report, args.database):
     64         if output_path.resolve().is_relative_to(input_dir.resolve()):
     65             parser.error(f'{output_path} lies inside the input directory {args.input_dir}')
     66 
     67     try:
     68         reconciled = reconciliation.reconcileDirectory(input_dir, rules_path=args.rules)
     69     except (RulesError, InputDirectoryError):
     70         return ExitCode.UNUSABLE.value
     71 
```

### 8. billing.py:43

```python
     35     """Parse the billing export at billing_path, row by row.
     36 
     37     Raises:
     38         UnreadableInventoryError: The file cannot be read or decoded, is not CSV, or does not open
     39             with the header.
     40     """
     41     source = FileName(billing_path.name)
     42     try:
>>   43         # read_text() would translate newlines, which alters a newline quoted inside a CSV field
     44         billing_text = billing_path.read_bytes().decode('utf-8')
     45     except OSError as exc:
     46         raise _rejectBillingFile(source, f'unreadable: {exc.strerror}') from exc
     47     except UnicodeDecodeError as exc:
     48         raise _rejectBillingFile(source, f'not UTF-8: {exc.reason}') from exc
     49 
     50     reader = csv.reader(io.StringIO(billing_text, newline=''))
     51     try:
     52         rows = [(reader.line_num, row) for row in reader]
     53     except csv.Error as exc:
```

### 9. billing.py:78

```python
     70     return ParsedFile(billing_lines=tuple(billing_lines), scanned_resources=(), rejections=tuple(rejections))
     71 
     72 
     73 def _parseBillingRow(row: list[str], source: FileName, location: str) -> BillingLine | RejectedRecord:
     74     if len(row) != len(_BILLING_HEADER):
     75         return RejectedRecord(location, f'{len(row)} fields, expected {len(_BILLING_HEADER)}')
     76 
     77     resource_id, sku, monthly_cents, region = row
>>   78     # isdigit() alone admits non-ASCII digits such as '²'
     79     if not (monthly_cents.isascii() and monthly_cents.isdigit()):
     80         return RejectedRecord(location, f'monthly_cents {monthly_cents!r} is not a non-negative integer')
     81     empty = [name for name, value in zip(_BILLING_HEADER, row, strict=True) if not value]
     82     if empty:
     83         return RejectedRecord(location, f'empty {", ".join(empty)}')
     84 
     85     return BillingLine(ResourceId(resource_id), Sku(sku), Cents(int(monthly_cents)), Region(region), source)
     86 
     87 
     88 def _rejectBillingFile(source: FileName, reason: str) -> UnreadableInventoryError:
```

### 10. join.py:65

```python
     57         findings=findings,
     58         matched=len(matched_ids),
     59         ignored_billing=len(inventory.billing_lines) - len(billed),
     60         ignored_scanned=len(inventory.scanned_resources) - len(scanned),
     61     )
     62 
     63 
     64 def _sameRegion(billed_region: Region, scanned_region: Region, region_aliases: Mapping[Region, Region]) -> bool:
>>   65     # one hop, not transitive: with a->b and b->c, a resolves to b and b to c, so a matches neither
     66     return region_aliases.get(billed_region, billed_region) == region_aliases.get(scanned_region, scanned_region)
     67 
     68 
     69 def _buildBilledNotFound(line: BillingLine, rules: ReconcileRules) -> Finding:
     70     return Finding(
     71         kind=FindingKind.BILLED_NOT_FOUND,
     72         resource_id=line.resource_id,
     73         sku=line.sku,
     74         monthly_cents=line.monthly_cents,
     75         team=None,
```

### 11. logs.py:15

```python
      7 
      8 from __future__ import annotations
      9 
     10 import logging
     11 import sys
     12 
     13 
     14 _LOCATION = ('module', 'lineno', 'funcName')
>>   15 # the standard formatter discards every field passed in `extra`
     16 _STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
     17 
     18 LOG = logging.getLogger('reconciler')
     19 
     20 
     21 def configureLogging(*, verbose: bool) -> None:
     22     global LOG
     23     handler = logging.StreamHandler(sys.stderr)
     24     handler.setFormatter(_FieldFormatter())
     25     LOG.addHandler(handler)
```

### 12. rules.py:60

```python
     52 
     53     ignored_skus = document['ignored_skus']
     54     if not isinstance(ignored_skus, list) or not all(isinstance(sku, str) for sku in ignored_skus):
     55         raise _rejectRules(rules_path, 'ignored_skus is not a list of strings')
     56     region_aliases = document['region_aliases']
     57     if not isinstance(region_aliases, dict) or not all(isinstance(alias, str) for alias in region_aliases.values()):
     58         raise _rejectRules(rules_path, 'region_aliases is not an object of string to string')
     59     grace_cents = document['grace_cents']
>>   60     # without the bool test, JSON true passes as 1
     61     if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
     62         raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')
     63 
     64     return ReconcileRules(
     65         ignored_skus=frozenset(Sku(sku) for sku in ignored_skus),
     66         region_aliases=MappingProxyType({Region(name): Region(alias) for name, alias in region_aliases.items()}),
     67         grace_cents=Cents(grace_cents),
     68     )
     69 
     70 
```

### 13. vocabulary.py:21

```python
     13 from typing import NewType
     14 
     15 
     16 ResourceId = NewType('ResourceId', str)
     17 Sku = NewType('Sku', str)
     18 Region = NewType('Region', str)
     19 Team = NewType('Team', str)
     20 Cents = NewType('Cents', int)
>>   21 FileName = NewType('FileName', str)  # a basename, never a path
     22 
     23 
     24 class InventoryFormat(Enum):
     25     BILLING = 'billing'
     26     SCAN = 'scan'
     27     UNKNOWN = 'unknown'
     28 
     29 
     30 class FileStatus(Enum):
     31     OK = 'ok'
```
