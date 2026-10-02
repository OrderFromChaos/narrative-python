# Round 10 — blind rating 3

Eighteen comments from cycle 1, shuffled. Each shows the comment and the code around it.

For each: `keep`, `trim: <your version>` or `cut`, and a reason if you have one.

## R10-X01

```python
# DB-API row shape for executemany(), which takes a sequence per row and rejects a dataclass
_FindingRow = tuple[str, str, str, str, int | None, str | None, str | None, str | None, int, str, str]  # noqa: NAR005
```

## R10-X02

```python
# a name stands for itself and its one-hop alias: with a -> b and b -> c, a matches b but not c
aliases = rules.region_aliases
billed_names = {billed_region, aliases.get(billed_region, billed_region)}
scanned_names = {scanned_region, aliases.get(scanned_region, scanned_region)}
return not billed_names.isdisjoint(scanned_names)
```

## R10-X03

```python
# a library caller that configures no logging sees nothing, not the last-resort stderr handler
LOG.addHandler(logging.NullHandler())


def configureLogging(*, verbose: bool) -> None:
```

## R10-X04

```python

HEADER = ['resource_id', 'sku', 'monthly_cents', 'region']
CENTS_PATTERN = re.compile(r'[0-9]+')  # int() alone also takes a sign, spaces, underscores and non-ASCII digits


def readBillingFile(billing_path: Path) -> FileReading[BillingLine]:
    """Read one billing file. A resource_id repeated across rows is not rejected here.
```

## R10-X05

```python
    # bytes, not read_text(): universal newlines would rewrite a carriage return inside a CSV field
    return inventory_bytes.decode('utf-8')
except UnicodeDecodeError as exc:
    raise _rejectInventoryText(path, f'not UTF-8: {exc.reason} at byte {exc.start}') from exc

```

## R10-X06

```python
# a str: Path() would drop a trailing slash that the report must echo
parser.add_argument('input_dir', help='directory of *.billing.csv and *.scan.json files')
parser.add_argument('--rules', type=Path, help='rules file (default: reconcile.json in input_dir)')
parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='JSON report to write')
parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='SQLite file to write')
```

## R10-X07

```python
# read-only: NEVER write inside the input directory, or a later run reads the output as input
for output_path in (args.report, args.database):
    if output_path.resolve().is_relative_to(input_dir.resolve()):
        LOG.error('output.inside_input', extra={'path': str(output_path), 'input_dir': args.input_dir})
        return reconcile.EXIT_UNUSABLE
```

## R10-X08

```python
# isdigit() alone admits non-ASCII digits such as '²'
if not (cents_text.isascii() and cents_text.isdigit()):
    return f'monthly_cents {cents_text!r} is not a non-negative base-ten integer'

return None
```

## R10-X09

```python
# per-record rejections log at DEBUG, so --verbose shows each one
global LOG
handler = logging.StreamHandler()
handler.setFormatter(_FieldFormatter())
LOG.addHandler(handler)
```

## R10-X10

```python
# list before reading rules: a missing input_dir would otherwise report as a missing rules file
inventory_paths = inventory.listInventoryPaths(input_dir, rules_path=resolved_rules_path)
reconcile_rules = rules.readRules(resolved_rules_path)
read_inventory = inventory.readInventory(inventory_paths)
joined = join.joinInventory(read_inventory, reconcile_rules)
```

## R10-X11

```python
# JSON object keys are always strings, so only the values need checking
region_aliases = document['region_aliases']
if not isinstance(region_aliases, dict) or not all(isinstance(alias, str) for alias in region_aliases.values()):
    raise _rejectRules(rules_path, 'region_aliases is not an object of string to string')
# bool is a subclass of int, so isinstance() would admit `true`
```

## R10-X12

```python
    # line_num after each row, so a problem names the line a reader sees in an editor
    rows = [(reader.line_num, row) for row in reader]
except csv.Error as exc:
    raise _rejectBillingText(source, f'not CSV: {exc}') from exc

```

## R10-X13

```python
# returns the reason as a string when the row is rejected
CENTS_PATTERN = re.compile(r'[0-9]+')

if len(row) != len(_BILLING_HEADER):
    return f'{len(row)} fields, not {len(_BILLING_HEADER)}'
```

## R10-X14

```python
# stderr, so the summary table on stdout stays clean for a pipe
global LOG
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(FieldFormatter())
LOG.addHandler(handler)
```

## R10-X15

```python
# bool is a subclass of int, and `true` is no amount of cents
if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
    raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')

return ReconcileRules(
```

## R10-X16

```python
RegionName = NewType('RegionName', str)
TeamName = NewType('TeamName', str)
SourceName = NewType('SourceName', str)  # basename of an inventory file
Cents = NewType('Cents', int)


class FileFormat(Enum):
```

## R10-X17

```python
    # serialisation pinned by the spec: two implementations must write byte-identical reports
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def _buildFindingEntry(finding: Finding) -> dict[str, object]:
```

## R10-X18

```python
# billing side first, so a finding states the billing sku when the two sides disagree
sides = [side for side in (line, resource) if side is not None]
return Finding(
    kind=kind,
    resource_id=sides[0].resource_id,
```
