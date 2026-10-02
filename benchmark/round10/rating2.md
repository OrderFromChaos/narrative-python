# Round 10 — blind rating 2

Fifteen comments from two versions of the comment rules, shuffled. Each shows the comment and the
code around it.

For each: `keep`, `trim: <your version>` or `cut`, and a reason if you have one. Don't read
`rating2_key.md` before answering.

## R10-W01

```python
# read-only: NEVER write inside the input directory, or a later run reads the output
input_dir = Path(args.input_dir)
inside = [str(path) for path in (args.report, args.db) if path.resolve().is_relative_to(input_dir.resolve())]
if inside:
    LOG.error('run.output_inside_input_dir', extra={'paths': ','.join(inside), 'exit_code': EXIT_UNUSABLE})
```

## R10-W02

```python
# read-only: NEVER write inside the input directory
for output_path in (args.report, args.db):
    if output_path.resolve().is_relative_to(input_dir.resolve()):
        LOG.error('output.inside_input_dir', extra={'output': str(output_path), 'input_dir': args.input_dir})
        return ExitCode.UNUSABLE.value
```

## R10-W03

```python
    team: TeamName | None
    source: Path
    location: str  # 'line 4' in a billing file, 'resources[3]' in a scan file


@dataclass(frozen=True)
class FileRead:
```

## R10-W04

```python
    # billed_not_found always has monthly_cents
    return (0, -(finding.monthly_cents or 0), finding.resource_id)
case FindingKind.FOUND_NOT_BILLED:
    return (1, 0, finding.resource_id)
case FindingKind.REGION_MISMATCH:
```

## R10-W05

```python
# ignored teams bill themselves, and billing lines name no team, so drop both sides by scanned resource_id
ignored_team_resources = {record.resource_id for record in records if record.team in reconcile_rules.ignored_teams}
joinable = [
    record
    for record in records
```

## R10-W06

```python
# one hop, not transitive: with a -> b and b -> c, a resolves to b and c stays c
aliases = rules.region_aliases
return aliases.get(billed_region, billed_region) == aliases.get(scanned_region, scanned_region)


```

## R10-W07

```python
# a UNIQUE index treats NULLs as distinct, so IFNULL folds each one to a value no accepted
# record can hold: cents are never negative, and team and regions are never empty
'CREATE UNIQUE INDEX IF NOT EXISTS findings_identity ON findings ('
" kind, resource_id, sku, IFNULL(monthly_cents, -1), IFNULL(team, ''),"
" IFNULL(billed_region, ''), IFNULL(scanned_region, ''), above_grace"
');'
```

## R10-W08

```python
        is not a run of ASCII digits.
"""
CENTS_PATTERN = re.compile(r'[0-9]+')  # ASCII digits only: no sign, space or underscore
FIELD_COUNT = 4

try:
    fields = next(csv.reader([line]))
```

## R10-W09

```python
    # the rules file is typed by hand, so its team names need not match the scanner's case or spacing
    return TeamName(team.strip().casefold())


def _rejectRules(rules_path: Path, reason: str) -> RulesFileError:
```

## R10-W10

```python
# bool is an int subclass, so JSON true would pass the int check
if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
    raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')

return Rules(
```

## R10-W11

```python
    # pinned serialisation: two correct implementations must write byte-identical reports
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def _buildRulesEntry(rules: Rules) -> dict[str, object]:
```

## R10-W12

```python
# a billing line names no team, so excluding only the scanned side turns the line into billed_not_found
exempt_resource_ids = {
    record.resource_id
    for record in records
    if record.origin is InventoryFormat.SCAN_JSON and record.team in reconcile_rules.ignored_teams
```

## R10-W13

```python
class ReconcileRules:
    ignored_skus: frozenset[Sku]
    ignored_teams: frozenset[TeamName]  # stripped and casefolded
    region_aliases: Mapping[RegionName, RegionName]
    grace_cents: Cents


```

## R10-W14

```python
# ASCII digits only: no sign, no space, no underscore, no other script's digits
if re.fullmatch('[0-9]+', cents_text) is None:
    raise _rejectBillingRow(source_basename, line_number, f'monthly_cents {cents_text!r} is not a digit run')

return BillingLine(ResourceId(resource_id), Sku(sku), int(cents_text), Region(region), source_basename)
```

## R10-W15

```python
# None for a file of unknown format, which is never opened
match file_format:
    case FileFormat.BILLING:
        return billing_csv.readBillingFile(path)
    case FileFormat.SCAN:
```
