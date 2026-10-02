# Round 10 — blind rating 4

10 comments from cycle 2, shuffled. Each shows the comment and the code around it.

For each: `keep`, `trim: <your version>` or `cut`, and a reason if you have one.

## R10-Y01

```python

def readInventoryFiles(inventory_paths: Iterable[Path]) -> tuple[InventoryFile, ...]:
    # order matters: a repeated resource_id is accepted from the first file only
    files: list[InventoryFile] = []
    billing_ids: set[ResourceId] = set()
    scan_ids: set[ResourceId] = set()
    for inventory_path in inventory_paths:
        inventory_file = _readInventoryFile(inventory_path, billing_ids, scan_ids)
```

## R10-Y02

```python

def _readInventoryText(inventory_path: Path) -> str:
    # bytes, then decode: read_text() translates \r\n, which the csv module must see untranslated
    try:
        return inventory_path.read_bytes().decode('utf-8')
    except OSError as exc:
        raise _rejectUnreadableFile(inventory_path, f'unreadable: {exc.strerror}') from exc
    except UnicodeDecodeError as exc:
```

## R10-Y03

```python
    scanned_resources: dict[ResourceId, ScannedResource],
) -> FileOutcome:
    # adds the file's accepted records to the dict for its side
    name = FileName(path.name)
    file_format = _classifyFile(name)
    match file_format:
        case FileFormat.BILLING:
            return _acceptRecords(name, file_format, billing_csv.readBillingFile(path), billing_lines)
```

## R10-Y04

```python

def _parseRow(row: list[str], source_file: str, line_number: int) -> InventoryRecord | RecordRejection:
    CENTS_PATTERN = re.compile(r'[0-9]+')  # not \d or str.isdigit(): both accept non-ASCII digits
    if len(row) != 4:
        return RecordRejection(f'line {line_number}: {len(row)} fields, expected 4')

    resource_id, sku, monthly_cents, region = row
    if not CENTS_PATTERN.fullmatch(monthly_cents):
```

## R10-Y05

```python

class FindingKind(Enum):
    # member order is the report's order of findings and of by_kind
    BILLED_NOT_FOUND = 'billed_not_found'
    FOUND_NOT_BILLED = 'found_not_billed'
    REGION_MISMATCH = 'region_mismatch'


```

## R10-Y06

```python
    scanned_resources: dict[ResourceId, ScannedResource],
) -> str | None:
    # returns the problem that rejects the entry, or None once the entry is accepted
    match entry:
        case Rejection():
            return entry.problem
        case BillingLine():
            return _admitFirst(entry, billing_lines)
```

## R10-Y07

```python
        json.dumps(finding.sources, ensure_ascii=False),
    )
    # a digest and not a UNIQUE over the columns: SQLite treats every NULL as distinct in a UNIQUE key
    fingerprint = hashlib.sha256(json.dumps(columns, ensure_ascii=False).encode('utf-8')).hexdigest()
    return (fingerprint, *columns, first_seen)


### vocabulary #########################################################################
```

## R10-Y08

```python
@dataclass(frozen=True)
class CommandLine:
    input_dir_text: str  # as typed, for the report's input_dir
    rules_path: Path | None
    report_path: Path
    db_path: Path
    verbose: bool

```

## R10-Y09

```python
    raise _rejectRules(rules_path, 'region_aliases is not an object of string to string')
grace_cents = document['grace_cents']
# JSON true is a Python int
if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
    raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')

return ReconcileRules(
    ignored_skus=frozenset(Sku(sku) for sku in ignored_skus),
```

## R10-Y10

```python

def _cellText(value: str | None) -> str:
    # a value the finding does not carry
    return '-' if value is None else value


def _graceCell(finding: Finding) -> str:
    match finding.kind:
```
