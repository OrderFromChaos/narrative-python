# Comments written under the shipped stance (variant T)

Four V6 runs (billing reconciler), cycles 2 and 3. Every `#` comment block, with the 3 lines of code after it.
Pragmas (`noqa`, `ruff:`) and `###` dividers are left out. Packages:

- `scratchpad/cycle2/v6_T_1`
- `scratchpad/cycle2/v6_T_2`
- `scratchpad/cycle3/v6_T_3`
- `scratchpad/cycle3/v6_T_4`

## v6_T_1: 7 comments

**1. billing_reconciler/__main__.py:53**

```python
# no type=Path: Path drops a trailing slash, and the report must state the argument exactly
|     parser.add_argument('input_dir', help='directory of *.billing.csv and *.scan.json files')
|     parser.add_argument('--rules', type=Path, help='rules file (default: reconcile.json in INPUT_DIR)')
|     parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='JSON report to write')
```

**2. billing_reconciler/__main__.py:64**

```python
# read-only: NEVER write inside the input directory
|     inside = [str(path) for path in (args.report, args.db) if path.resolve().is_relative_to(input_dir.resolve())]
|     if inside:
|         LOG.error('output.inside_input_dir', extra={'paths': inside, 'input_dir': args.input_dir})
```

**3. billing_reconciler/billing_csv.py:46 (eol)**

```python
    CENTS_PATTERN = re.compile(r'[0-9]+')  # not \d or str.isdigit(): both accept non-ASCII digits
```

**4. billing_reconciler/inventory.py:121**

```python
# read_text() translates newlines, which alters a newline quoted inside a CSV field
|     try:
|         file_bytes = path.read_bytes()
|     except OSError as exc:
```

**5. billing_reconciler/join.py:40**

```python
# one hop: an alias's target is not looked up again
|         if aliases.get(billed.region, billed.region) != aliases.get(resource.region, resource.region):
|             findings.append(_buildFinding(FindingKind.REGION_MISMATCH, billed, resource, rules.grace_cents))
| 
```

**6. billing_reconciler/rules.py:62**

```python
# bool is a subclass of int, and JSON true is not a count of cents
|     if type(grace_cents) is not int or grace_cents < 0:
|         raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')
| 
```

**7. billing_reconciler/vocabulary.py:19**

```python
# member order is the order of the report's findings and of its by_kind object
|     BILLED_NOT_FOUND = 'billed_not_found'
|     FOUND_NOT_BILLED = 'found_not_billed'
|     REGION_MISMATCH = 'region_mismatch'
```

## v6_T_2: 6 comments

**8. billing_reconciler/__main__.py:53**

```python
# read-only: NEVER write inside the input directory, or a later run reads the output as input
|     for output_path in (args.report, args.db):
|         if output_path.resolve().is_relative_to(input_dir.resolve()):
|             parser.error(f'{output_path} is inside the input directory {input_dir}')
```

**9. billing_reconciler/inventory.py:57**

```python
# requires basename order: a record from an earlier basename is accepted over a later one with its resource_id
|     paths_by_format = {
|         file_format: [path for path in inventory_paths if _detectFormat(path) is file_format]
|         for file_format in FileFormat
```

**10. billing_reconciler/report.py:42**

```python
# pinned serialisation: two runs over the same input must write identical bytes
|     report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
| 
| 
```

**11. billing_reconciler/rules.py:59**

```python
# bool is an int subclass, and JSON true must not pass as 1
|     if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
|         raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')
| 
```

**12. billing_reconciler/store.py:88**

```python
# a UNIQUE over the nullable columns treats every NULL as distinct, so the key is one non-null text value
|     identity = [
|         finding.kind.value,
|         finding.resource_id,
```

**13. billing_reconciler/vocabulary.py:35**

```python
# member order is the report's order
|     BILLED_NOT_FOUND = 'billed_not_found'
|     FOUND_NOT_BILLED = 'found_not_billed'
|     REGION_MISMATCH = 'region_mismatch'
```

## v6_T_3: 2 comments

**14. reconciler/join.py:39**

```python
# aliases resolve one hop: with a->b and b->c, a and c compare unequal
|     aliases = rules.region_aliases
|     mismatched_pairs = [
|         (line, resource)
```

**15. reconciler/rules.py:50**

```python
# without the bool test, JSON true passes as 1
|     if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
|         raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')
| 
```

## v6_T_4: 3 comments

**16. billing_reconciler/__main__.py:60**

```python
# read-only: NEVER write inside the input directory
|         if input_dir.resolve() in output_path.resolve().parents:
|             LOG.error('output.inside_input_dir', extra={'output_path': str(output_path)})
|             return ExitCode.UNUSABLE.value
```

**17. billing_reconciler/billing.py:70**

```python
# isdigit() alone admits non-ASCII digits such as '²'
|         if not (cents_text.isascii() and cents_text.isdigit()):
|             problem = f'monthly_cents {cents_text!r} is not a run of ASCII digits'
|             rejections.append(_rejectBillingLine(source, line_number, problem))
```

**18. billing_reconciler/rules.py:53**

```python
# bool subclasses int, and `true` is no amount of cents
|     if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
|         raise _rejectRules(rules_path, 'grace_cents is not a non-negative integer')
| 
```
