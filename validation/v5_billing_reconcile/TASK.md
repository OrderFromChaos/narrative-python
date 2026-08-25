# Task V5 — billing reconciler

Match what a cloud bill charges for against what an asset scan found, and report every mismatch.

This is a join, not a total. Every record on one side is matched to at most one record on the other,
and the records that fail to match are the point of the report.

## Inputs

Two inventory formats, both of which you must read:

- `*.billing.csv` — a header row, then `resource_id,sku,monthly_cents,region` per line. Written by
  the finance export. **It carries no owning team.**
- `*.scan.json` — `{"scanned_at": ..., "resources": [{"id": ..., "sku": ..., "team": ..., "region": ...}]}`.
  Written by the asset scanner. **It carries the owning team and no cost.**

One rules file, `reconcile.json`:

```json
{
  "ignored_skus": ["support-plan"],
  "region_aliases": {"us-east-1": "use1"},
  "grace_cents": 500
}
```

## What it does

1. Read every inventory file in an input directory, whichever format each is.
2. Join billing lines to scanned resources on `resource_id`. A resource whose `sku` appears in
   `ignored_skus` takes part in no join and appears in no finding.
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

## Constraints

- **Several modules.** The two formats, the rules file, the join, the store, the report and the
  entry point are distinct concerns; do not put them in one file.
- It must also be **importable**: another program should be able to run the reconciliation without
  running the command-line tool.
- Python 3.11+. Standard library only. No network — read from the input directory.
- It must run. Include a small fixture directory so `python3 -m <package> <fixture-dir>` works.

## Notes on the data

- `resource_id` in the CSV and `id` in the JSON name the same thing.
- The two formats do not carry the same fields, and the difference is not an oversight in this spec.
- A `region_alias` maps a long name to a short one. The mapping is not symmetric in the file, and
  both directions must compare equal.
- The fixture must exercise a malformed input file, and at least one finding of each of the three
  kinds, so that requirements 3 and 7 are visible when the tool runs.

## Deliverable

A package directory, plus whatever fixture files it needs. Nothing else.
