# Round 10 — blind rating 5

4 comments from cycle 3, shuffled. Each shows the comment and the code around it.

For each: `keep`, `trim: <your version>` or `cut`, and a reason if you have one.

## R10-Z01

```python
HEADER = ['resource_id', 'sku', 'monthly_cents', 'region']
try:
    with billing_path.open(encoding='utf-8', newline='') as billing_file:
        reader = csv.reader(billing_file)
        # line_num is the line on which the row just read ends
        numbered_rows = [(reader.line_num, row) for row in reader]
except OSError as exc:
    raise rejectInventoryFile(billing_path, f'unreadable: {exc.strerror}') from exc
except UnicodeDecodeError as exc:
    raise rejectInventoryFile(billing_path, 'not UTF-8') from exc
```

## R10-Z02

```python
            return '-'


def _alignColumns(rows: Sequence[Sequence[str]]) -> list[str]:
    # every column is left-aligned to its widest cell, two spaces apart
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return ['  '.join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip() for row in rows]
```

## R10-Z03

```python
        _buildFinding(FindingKind.BILLED_NOT_FOUND, record, None, grace_cents=grace_cents)
        for resource_id, record in billed.items()
        if resource_id not in scanned
    ),
    # every billed_not_found has a cost
    key=lambda finding: (-(finding.monthly_cents or 0), finding.resource_id),
)
found_not_billed = [
    _buildFinding(FindingKind.FOUND_NOT_BILLED, None, scanned[resource_id], grace_cents=grace_cents)
    for resource_id in sorted(scanned.keys() - billed.keys())
```

## R10-Z04

```python
    return FileFormat.UNKNOWN


def _selectReader(file_format: FileFormat) -> InventoryReader | None:
    # None for a format that has no reader, so its file is skipped unopened
    match file_format:
        case FileFormat.BILLING:
            return billing_csv.readBillingFile
        case FileFormat.SCAN:
            return scan_json.readScanFile
```
