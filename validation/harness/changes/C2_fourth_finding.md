# Change C2 — a fourth kind of mismatch

> Read `COMMON.md` first. It states the database and unchanged-behaviour rules that apply to
> every change request.

Two sides can agree on the resource and disagree on what it is. Report that.

## The new finding

**`sku_mismatch`** — both sides carry a record for the same `resource_id`, the resource takes part in
the join, and the two `sku` values differ.

- It is reported like the three kinds that already exist: in the summary table, in the JSON report,
  and in SQLite.
- It carries the billed `sku` and the scanned `sku`, so an operator can see both.
- It ranks after `region_mismatch`.
- It never affects the exit code, whatever the cost of the resource.

A resource may produce both a `sku_mismatch` and a `region_mismatch` on the same run. Report both.

## What must be true afterwards

- A matched pair whose skus differ produces exactly one `sku_mismatch` finding.
- A matched pair whose skus agree produces none.
- `ignored_skus` still removes a resource before any of this, so an ignored resource produces no
  `sku_mismatch` either.
- Input that produced no sku disagreement behaves exactly as it did before, in the sense
  `COMMON.md` defines. This change adds a column and a counted kind, so its output is not
  byte-identical and is not expected to be.
- The fixture exercises the new finding, so a run over it shows a `sku_mismatch`.
- An existing database is brought forward, per `COMMON.md`.
