# Round 10 — blind rating

Fifteen comments from three sources, shuffled. Each shows the comment and the code below it.

For each: `keep`, `trim: <your version>` or `cut`, and a reason if you have one. Don't read
`rating_key.md` before answering.

## R10-V01

```python
# bool is a subclass of int, and `true` in the rules file is a type error.
if isinstance(value, bool) or not isinstance(value, int) or value < 0:
    raise ReconcileError(f'rules file {path}: {key!r} must be an integer of zero or more')
return value
```

## R10-V02

```python
# the suffix alone decides, so a *.scan.json holding no JSON is a scan document that failed
if basename.endswith(BILLING_SUFFIX):
    return InventoryFormat.BILLING
if basename.endswith(SCAN_SUFFIX):
    return InventoryFormat.SCAN
```

## R10-V03

```python
# databases written before 2026/10/01 lack the scanned_sku column
columns = {name for (name,) in self.connection.execute(LIST_FINDING_COLUMNS)}
if 'scanned_sku' not in columns:
    self.connection.execute(ADD_SCANNED_SKU)
self.connection.commit()
```

## R10-V04

```python
# every key is mandatory, and each carries its own shape
for key in ('ignored_skus', 'region_aliases', 'grace_cents'):
    if key not in stated:
        raise _rejectRules(rules_path, f'{key} is missing')
rules = ReconcileRules(
```

## R10-V05

```python
# read-only: NEVER write inside the input directory
for output_path in (args.report, args.db):
    if output_path.resolve().is_relative_to(input_dir.resolve()):
        LOG.error('output.inside_input_dir', extra={'output_path': str(output_path), 'input_dir': args.input_dir})
        return reconcile.EXIT_UNUSABLE
```

## R10-V06

```python
# A blank line is not a record. Without this, every file that ends in a
# newline would reject a phantom row.
if not row:
    continue
record = _read_row(row, path.name, rows.line_num, outcome, accepted_resource_ids)
if record is not None:
```

## R10-V07

```python
# One row per finding, in the column order of the INSERT. The DB-API takes a sequence per row and
# raises ProgrammingError on a dataclass, so the shape stays a tuple and the alias gives it a name.
_FindingRow = tuple[str, str, str, str, int | None, str | None, str | None, str | None, int, str, str]
```

## R10-V08

```python
# An ignored team runs its own billing, so its billing lines leave the report too. A billing line
# names no team, so it takes the team of the scanned resource with the same resource_id.
ignored_team_resources = {
    record.resource_id for record in scanned_records if record.team in reconcile_rules.ignored_teams
} - scanned.keys()
billed = _indexByResourceId(
```

## R10-V09

```python
# input_dir_argument stays a str: a Path would normalise what the command line typed
report = {
    'generated_at': reconciliation.started_at.isoformat(timespec='seconds'),
    'input_dir': input_dir_argument,
    'rules': _describeRules(reconciliation.rules),
```

## R10-V10

```python
# a half-read rules file or a missing directory leaves nothing to reconcile, so neither the
# report nor the database is written
try:
    reconciliation = reconcileDirectory(arguments.input_dir, rules_path=arguments.rules_path)
except (RulesError, InputDirectoryError) as exc:
    LOG.error('run.abandoned', extra={'reason': str(exc)})
```

## R10-V11

```python
# a value the finding does not carry is null, never an empty string and never an absent key
return {
    'kind': finding.kind.value,
    'resource_id': finding.resource_id,
    'sku': finding.sku,
```

## R10-V12

```python
# an operator can act on a per-file tally, and not on one rejected row of ten thousand
match status:
    case FileStatus.OK | FileStatus.SKIPPED:
        return logging.DEBUG
    case FileStatus.PARTIAL | FileStatus.FAILED:
```

## R10-V13

```python
    # Never opened, so it has no records to accept or reject.
    outcome = FileOutcome(
        path=path.name, file_format=FileFormat.UNKNOWN, status=FileStatus.SKIPPED
    )
inventory.files.append(outcome)
```

## R10-V14

```python
# databases written before 2026/10/01 lack the account_id column, and their rows keep it NULL
columns = {row[1] for row in self.connection.execute('PRAGMA table_info(finding)')}
if 'account_id' not in columns:
    self.connection.execute('ALTER TABLE finding ADD COLUMN account_id TEXT')
self.connection.commit()
```

## R10-V15

```python
    # a billing line names no team, so no rule ignores it on its own evidence
    return record.team is not None and _foldTeamName(record.team) in reconcile_rules.ignored_teams


def _foldTeamName(team: str) -> TeamName:
```
