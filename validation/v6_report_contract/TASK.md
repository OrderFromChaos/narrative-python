# Task V6 — billing reconciler, with the outputs pinned

Match what a cloud bill charges for against what an asset scan found, and report every mismatch.

This is a join, not a total. Every record on one side is matched to at most one record on the other,
and the records that fail to match are the point of the report.

This is Task V5 with one change: **the outputs are specified.** V5 said "write a JSON report" and
fixed nothing about it, so two correct implementations produced reports of different scope, and the
two report modules could not be compared. Section "The outputs" below closes that. Everything under
"What is left to you" stays open on purpose.

## Inputs

Two inventory formats, both of which you must read:

- `*.billing.csv` — a header row, then `resource_id,sku,monthly_cents,region` per line. Written by
  the finance export. **It carries no owning team.**
- `*.scan.json` — `{"scanned_at": ..., "resources": [{"id": ..., "sku": ..., "team": ..., "region": ...}]}`.
  Written by the asset scanner. **It carries the owning team and no cost.**

One rules file, `reconcile.json`, read from the input directory unless `--rules` names another path:

```json
{
  "ignored_skus": ["support-plan"],
  "region_aliases": {"us-east-1": "use1"},
  "grace_cents": 500
}
```

All three keys are mandatory, and each is type-checked: `ignored_skus` a list of strings,
`region_aliases` an object of string to string, `grace_cents` a non-negative integer. A rules file
that is unreadable, is not an object, omits a key, or holds a value of the wrong type stops the run
with exit code 2. `--rules` may name a path outside the input directory, and a rules file inside the
input directory is never treated as an inventory file nor reported among the per-file outcomes.

## What it does

1. Read every inventory file in an input directory, whichever format each is.
2. Join billing lines to scanned resources on `resource_id`. A **record** whose `sku` appears in
   `ignored_skus` is dropped before the join. Dropping one side does not drop the other: see
   *The join, settled*, which governs wherever this numbered list is loose.
3. Report three kinds of mismatch:
   - **billed_not_found** — a billing line with no scanned resource. You are paying for nothing.
   - **found_not_billed** — a scanned resource with no billing line. Unbilled usage.
   - **region_mismatch** — both sides matched, but the regions differ after `region_aliases` is
     applied. `us-east-1` and `use1` are the same region when the rules file says so.
4. Rank `billed_not_found` by `monthly_cents`, largest first. A finding whose cost is at or below
   `grace_cents` is recorded but does not affect the exit code.
5. Record every finding in SQLite, keyed so a re-run over unchanged inputs does not double-insert.
6. Print a summary table, and write a JSON report.
7. One malformed input file must not stop the others. Report per-file outcomes at the end.
8. Exit non-zero when any `billed_not_found` finding is above `grace_cents`.

## The join, settled

These decide which findings exist. They are fixed so that two correct implementations find the same
set.

- **The ignore is applied per side, before the join.** A billing line whose `sku` is ignored is
  dropped before matching, and so is a scanned resource whose `sku` is ignored. When the two sides
  disagree on `sku` and only one is ignored, the ignored side drops and the other side survives
  unmatched, which yields a finding.
- **A sku disagreement between two matched records is not a finding.** The three kinds are the
  whole list.
- **Region aliases resolve one hop, not transitively.** With `a` mapped to `b` and `b` mapped to
  `c`, `a` and `c` do not compare equal. Two names that map to the same name do compare equal.
- **A region absent or empty on either side is not a `region_mismatch`.** It is a rejected record,
  counted in that file's `rejected` tally.
- **A `resource_id` repeated on the same side keeps the first record.** Each later one is a rejected
  record and a problem string on that file.
- **Comparison is exact.** Do not fold case and do not trim whitespace on `resource_id`, `sku` or
  `region`.
- **A matched pair that agrees produces no record anywhere.**
- **Files are read in ascending basename order**, which is also the order they are reported in. A
  `resource_id` repeated on the same side across two files therefore keeps the record from the
  earlier basename.
- **Only the top level of the input directory is read.** No recursion, and no file whose name starts
  with `.`.

### What makes a record rejected

This list is closed. A record that fails none of these is accepted, and no other condition rejects
one.

A billing line is rejected when its row does not hold exactly four fields, when `monthly_cents` is
not a base-ten integer or is negative, when `resource_id`, `sku` or `region` is empty, or when its
`resource_id` already appeared on the billing side.

A scanned resource is rejected when it is not a JSON object, when it lacks any of `id`, `sku`,
`team` or `region`, when any of those four is not a string or is empty, or when its `id` already
appeared on the scan side.

Three clauses above need pinning down, because each one hides a second reading:

- **"Already appeared" means "was accepted".** A rejected record reserves nothing, so a later valid
  record carrying the same `resource_id` is accepted.
- **A blank line in a `*.billing.csv` is not a record.** It is neither accepted nor rejected and
  produces no problem string. Every file ending in a newline would otherwise reject a phantom row.
- **`monthly_cents` is a run of ASCII digits and nothing else.** No sign, no surrounding space, no
  underscore. `"0750"` is 750; `"+750"`, `" 750"` and `"7_50"` are rejected.

A `*.billing.csv` must open with the header `resource_id,sku,monthly_cents,region` exactly. Fields
are read by position, not by name, and the header is not a record.

A rejected record contributes one `problems` string, is counted in that file's `rejected` tally, and
reaches neither the join nor any total. The file keeps its other records.

A whole file fails — `status` `failed`, `accepted` and `rejected` both `0`, one `problems` string —
when it is not valid JSON, when its top level is not an object holding a `resources` list, or when a
`*.billing.csv` has no header row. A file holding a header and no data rows is `ok` with `accepted`
`0`.

## The outputs

**Two correct implementations must produce byte-identical report JSON for the same input**, except
for three things: `generated_at`, `input_dir`, and the wording of the strings inside each `problems`
array. The *length* of every `problems` array is fixed by this document; only the prose in it is
yours. That is the test of whether you have read this section.

Byte-identical needs the serialisation pinned, so write the file exactly this way:

```python
path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n'
)
```

**The program never writes inside the input directory.** Treat that directory as read-only, so no
output file can turn up in a later run's `files` array.

**Every object in the report keeps the key order shown in this document**, top level and nested
alike. Do not pass `sort_keys=True`. Where a *value* is sorted — `ignored_skus`, the keys of
`region_aliases`, `sources` — this document says so at that value. `by_kind` holds the three kinds
in the order `billed_not_found`, `found_not_billed`, `region_mismatch`.

`generated_at` is the run's start time, written by
`datetime.now(UTC).isoformat(timespec='seconds')`, which gives `2026-03-04T11:20:00+00:00`.
`input_dir` is the path exactly as it was given on the command line.

Exit code 2 writes no report and no database. An input directory that exists and holds no inventory
file is not an error: the run reports empty `findings` and `files` arrays, zero totals, and exits 0.
An input directory that does not exist, or is not a directory, is exit code 2.

### The JSON report

Written to the path given by `--report`, default `report.json` in the working directory. Exactly
these top-level keys, in this order:

```json
{
  "generated_at": "2026-03-04T11:20:00+00:00",
  "input_dir": "fixture",
  "rules": {"ignored_skus": ["support-plan"], "region_aliases": {"us-east-1": "use1"}, "grace_cents": 500},
  "totals": {
    "billing_lines": 10, "scanned_resources": 8,
    "ignored_billing": 3, "ignored_scanned": 1, "matched": 4,
    "findings": 7, "above_grace": 2,
    "by_kind": {"billed_not_found": 3, "found_not_billed": 3, "region_mismatch": 1}
  },
  "findings": [],
  "files": [],
  "exit_code": 1
}
```

`rules` echoes the rules that were applied. `ignored_skus` is sorted, and so are the keys of
`region_aliases`. Each `totals` member counts:

| member | counts |
|---|---|
| `billing_lines` | accepted billing records, across every file, before the ignore |
| `scanned_resources` | accepted scanned records, across every file, before the ignore |
| `ignored_billing` | those `billing_lines` the ignore then dropped |
| `ignored_scanned` | those `scanned_resources` the ignore then dropped |
| `matched` | pairs that joined, whether or not their regions agreed |
| `findings` | the length of the `findings` array |
| `above_grace` | findings whose `above_grace` is true |
| `by_kind` | findings of each kind; the three values sum to `findings` |

**Every sort in this document orders by Unicode code point**, which is what Python's `sorted` does
to `str` by default. Do not apply locale collation.

One `findings` entry, with exactly these keys in this order:

```json
{
  "kind": "billed_not_found",
  "resource_id": "min-flint-5520",
  "sku": "gpu-accelerated-1",
  "monthly_cents": 41200,
  "team": null,
  "billed_region": "na1",
  "scanned_region": null,
  "above_grace": true,
  "sources": ["core.billing.csv"]
}
```

- `kind` is one of the three literal strings above.
- A value the finding does not carry is JSON `null`. Never omit the key, and never write `""`.
- **Which values a finding carries follows from which side it has**, and nothing else:

  | | `billed_not_found` | `found_not_billed` | `region_mismatch` |
  |---|---|---|---|
  | `sku` | from the billing line | from the scanned resource | from the billing line |
  | `monthly_cents` | the cost | `null` | the cost |
  | `team` | `null` | the owning team | the owning team |
  | `billed_region` | the region | `null` | the region |
  | `scanned_region` | `null` | the region | the region |

  A `region_mismatch` matched on both sides, so it carries everything. When the two sides disagree
  on `sku`, the finding states the billing side's.
- `billed_region` and `scanned_region` are the **raw** strings as the files wrote them, not the
  aliased forms.
- `above_grace` is true only for a `billed_not_found` whose `monthly_cents` is **strictly greater
  than** `grace_cents`. It is false on the other two kinds.
- `sources` lists, sorted, the basenames of the files that supplied an **accepted** record to the
  finding. A record that was rejected supplied nothing, so its file is not listed even when it
  named the same `resource_id`.

Findings are ordered: every `billed_not_found` first, by `monthly_cents` descending and then
`resource_id` ascending; then every `found_not_billed` by `resource_id` ascending; then every
`region_mismatch` by `resource_id` ascending. A finding at or below the grace stays in the ranked
list.

One `files` entry per file the program considered, ordered by `path`, with exactly these keys:

```json
{"path": "broken.scan.json", "format": "scan", "status": "failed", "accepted": 0, "rejected": 0, "problems": ["..."]}
```

- `path` is the basename. Never an absolute path: the report must compare across machines.
- `format` is `billing`, `scan`, or `unknown`, **decided by the filename suffix alone.** A
  `*.scan.json` holding no JSON is still `scan`, and it fails.
- `status` is `ok`, `partial` (some records rejected), `failed` (the file was unreadable as a
  whole), or `skipped` (`format` is `unknown`).
- `accepted` and `rejected` count the records of that file that the reader **accepted** and
  **rejected**, by the closed list under *What makes a record rejected*. The ignore runs after
  reading and moves no record between the two, so an ignored record is `accepted` here and appears
  in `billing_lines` or `scanned_resources`. Both counts are `0` on a `failed` or `skipped` file.
- A `skipped` file has `accepted` `0`, `rejected` `0` and `problems` `[]`. It was never opened.
- `problems` holds one string per rejected record or per file-level failure, and is `[]` when there
  are none. The wording is yours. `rejected` and `len(problems)` need not agree: one file-level
  failure is one problem and no rejected records.

A file in the input directory that matches neither `*.billing.csv` nor `*.scan.json` is reported
with `status` `skipped`, and the rules file itself is not reported at all.

### The summary table

Printed to stdout. One row per finding, in the report's order, under these column headings in this
order:

```
kind  resource  sku  team  monthly  billed_region  scanned_region  grace
```

The `grace` cell reads `over` when `above_grace` is true, `within` on a `billed_not_found` that is
not, and `-` on the other two kinds. A cell the finding does not carry reads `-`. `monthly` is
formatted as you see fit, provided the unit is unambiguous.

Below the findings, print one row per `files` entry, and below that a summary naming the totals.
Widths, padding, rules and section headings are yours.

### Exit codes

- `0` — no `billed_not_found` finding is above the grace.
- `1` — at least one is.
- `2` — the rules file or the input directory was unusable, so nothing was reconciled.

An unreadable input file does not by itself change the exit code. It can manufacture
`billed_not_found` findings, and those are what set it.

## What is left to you

These are open, and a reviewer will read what you chose. Do not treat the list above as a hint
about any of them.

- How many modules there are, what they are called, and where each boundary falls.
- The name, signature and return type of the importable entry point.
- The SQLite file name, its schema, its table names, and what the dedup key is.
- How the table is laid out, and how the sections are headed.
- The wording of every problem string and every log line.
- Whether the program logs at all, and to where.

## Constraints

- **Several modules.** The two formats, the rules file, the join, the store, the report and the
  entry point are distinct concerns; do not put them in one file.
- It must also be **importable**: another program should be able to run the reconciliation without
  running the command-line tool.
- Python 3.11+. Standard library only. No network — read from the input directory.
- It must run. `python3 -m <package> <fixture-dir>` works against the fixture directory supplied
  with this task.

## The fixture

**This task ships its own fixture; do not write one.** It sits in `fixture/` next to this file, and
it exercises a malformed file, all three finding kinds, the grace boundary, an ignored sku on both
sides, and an alias pair in each direction. `EXPECTED.md` states what it should produce.

## Deliverable

A package directory. Nothing else.
