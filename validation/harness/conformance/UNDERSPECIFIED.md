# Underspecified in Task V5

Every question below is one the conformance suite wanted to ask and could not, because
`validation/v5_billing_reconcile/TASK.md` does not settle it. Each line quotes the spec text that
leaves the question open.

Two correct implementations may differ on any of these. A suite that asserted on them would score
one implementation's choice as another implementation's bug.

## The JSON report

1. The report file name and directory. > "Print a summary table, and write a JSON report." The suite
   therefore accepts a `--report`-style flag or discovers a newly written `*.json`.
2. The report schema: field names, and whether findings are grouped by kind or listed flat. > "write
   a JSON report". The suite reads several plausible shapes and skips when it can read none.
3. Whether the findings must be in the report at all, rather than only in SQLite and the table. >
   "Record every finding in SQLite ... Print a summary table, and write a JSON report."
4. The spelling of the three kind names in the report. > "**billed_not_found**". The bold text names
   the kinds in prose; it does not state that these are the literal report values.
5. Whether the report carries the per-file outcomes, the rules that were applied, or a run timestamp.
6. Whether a matched pair with equal regions produces an "ok" record anywhere, or nothing at all. >
   "the records that fail to match are the point of the report."

## Ranking

7. Which artifact must show the rank: the report, the table, the SQLite rows, or all three. > "Rank
   `billed_not_found` by `monthly_cents`, largest first." The suite asserts on the JSON report order,
   which is the only machine-readable artifact the spec requires.
8. The tie-break when two `billed_not_found` findings have equal `monthly_cents`. > "Rank
   `billed_not_found` by `monthly_cents`, largest first."
9. Any ordering for `found_not_billed` and `region_mismatch`. > requirement 4 ranks only
   `billed_not_found`.
10. Whether a finding at or below `grace_cents` still appears in the ranked list, or is separated
    out. > "A finding whose cost is at or below `grace_cents` is recorded but does not affect the
    exit code."

## The rules file

11. Where `reconcile.json` is read from: the input directory, the working directory, or a flag. >
    "One rules file, `reconcile.json`" and "No network — read from the input directory." The suite
    writes it into the input directory, and falls back to also placing a copy in the arm directory.
12. Whether `reconcile.json` is mandatory, and what happens when it is absent or itself malformed. No
    spec text covers this.
13. The default for each key when the key is missing: `ignored_skus`, `region_aliases`,
    `grace_cents`. The example shows all three present.
14. Whether `reconcile.json` in the input directory is also treated as an inventory file, or excluded.
    > "Read every inventory file in an input directory".
15. Whether `grace_cents` may be absent, zero, or negative.

## The join

16. What a duplicate `resource_id` on the same side means. > "Every record on one side is matched to
    at most one record on the other" constrains the match, not the input.
17. What happens when the two sides disagree on `sku`. > "Join billing lines to scanned resources on
    `resource_id`." A sku disagreement is not one of the three kinds and has no defined outcome.
18. Which side's `sku` decides an ignore when the two sides disagree, and whether one ignored side is
    enough. > "A resource whose `sku` appears in `ignored_skus` takes part in no join".
19. Whether `resource_id`, `sku` and `region` comparisons fold case or trim whitespace. No spec text
    covers this.
20. Whether an empty `resource_id` or an empty `region` is a finding, a malformed row, or ignored.

## Regions

21. Whether region aliases chain: `a` to `b` and `b` to `c` making `a` and `c` equal. > "The mapping
    is not symmetric in the file, and both directions must compare equal." This fixes one pair only.
22. Whether two long names that alias to the same short name compare equal to each other.
23. Which spelling the report shows for a mismatched or aliased region, the raw value or the
    canonical one. > "the regions differ after `region_aliases` is applied".
24. Whether a missing `region` on one side is a `region_mismatch`, a malformed record, or neither.

## Malformed input and per-file outcomes

25. What "malformed" covers: invalid JSON, a missing header, a wrong column count, a non-integer
    `monthly_cents`, a missing `team`, an empty file, an unknown extra column. > "One malformed input
    file must not stop the others." The suite uses truncated JSON, which no reading can accept.
26. Whether one bad row makes the whole file malformed, or only that row is dropped. > "One malformed
    input **file**".
27. What a per-file outcome contains, and where it is written. > "Report per-file outcomes at the
    end." The suite only asserts that each input file is named somewhere in the output or the report.
28. Whether a malformed file alone changes the exit code. > requirement 8 fixes the exit code on
    `billed_not_found` only, and requirement 7 does not mention the exit code.
29. What happens to a file in the input directory that matches neither `*.billing.csv` nor
    `*.scan.json`: ignored, or reported as malformed. > "Read every inventory file in an input
    directory, whichever format each is."
30. Whether subdirectories of the input directory are read.
31. What happens when the input directory holds no inventory file at all, or does not exist.

## The SQLite store

32. The database file name, its directory, the table names and the column names. > "Record every
    finding in SQLite".
33. What the key is. > "keyed so a re-run over unchanged inputs does not double-insert." The suite
    only asserts that a second run over an identical input adds no row.
34. Whether "unchanged inputs" means byte-identical files or the same set of findings.
35. Whether a changed input updates the stored row or inserts a second one, and whether a finding
    that has gone away is deleted.
36. Whether the store holds anything besides findings, such as one row per run or per file. The suite
    therefore counts only rows that name the fixture resources.

## Exit codes and the command line

37. Which non-zero value. > "Exit non-zero when any `billed_not_found` finding is above
    `grace_cents`."
38. Whether the exit code is 0 in every other case. The spec states one direction only. The suite
    asserts 0 when no `billed_not_found` is above the grace, which is the reading that "does not
    affect the exit code" supports.
39. Whether `grace_cents` is compared against each finding or against the total of all
    `billed_not_found`. > "A finding whose cost is at or below `grace_cents`" reads per finding.
40. Any command-line option beyond the input directory. > "`python3 -m <package> <fixture-dir>`".
41. Whether the tool accepts more than one input directory, or a single file.

## The printed table

42. The columns, their order, their widths, and whether the table goes to stdout or stderr. > "Print
    a summary table." The suite only asserts that something is printed, and never parses it.
43. Whether the table lists every finding or only a summary count per kind.

## The importable entry point

44. The name, module, signature and return type of the importable API. > "another program should be
    able to run the reconciliation without running the command-line tool." The suite searches for a
    public callable that returns a result naming both fixture resources, and reports SKIP rather than
    FAIL when it finds none, because no name is fixed.
45. Whether the importable API is allowed to write the report, the database, or the table as a side
    effect, or must return the findings and let the caller decide.
46. Whether the package must be importable without the reconciliation running, which the suite does
    assert, since a package that runs the tool on import cannot be used by another program.

## The data

47. Whether `scanned_at` is used or recorded anywhere. It appears in the format and in no requirement.
48. Whether `monthly_cents` may be negative, fractional, or absent. > "`resource_id,sku,monthly_cents,region`".
49. Whether `team` must be carried into the findings that have a scanned side. > "**It carries the
    owning team and no cost.**" and "The two formats do not carry the same fields, and the difference
    is not an oversight in this spec." The difference is called out as deliberate, but no requirement
    says what the team is for.
50. Whether the CSV may be quoted, may hold extra columns, or may use a different column order under
    the same header. > "a header row, then `resource_id,sku,monthly_cents,region` per line".
