# Change C1 — a third inventory format

> Read `COMMON.md` first. It states the database and unchanged-behaviour rules that apply to
> every change request.

Finance has a second export. Read it alongside the two formats the tool already handles.

## The format

Files named `*.ledger.tsv`. Tab-separated, one record per line, no header row:

    # exported 2026-02-01 by ledger-svc
    i-0001	compute-gpu	250000	us-east-1
    i-0002	object-store	1200	us-west-2

Four fields in order: `resource_id`, `sku`, `monthly_cents`, `region`. A line whose first
non-whitespace character is `#` is a comment. A blank line holds nothing.

Like the CSV export, this format **carries a cost and names no owning team.**

## What must be true afterwards

- A `*.ledger.tsv` file in the input directory is read and its records take part in the join exactly
  as billing CSV records do.
- A malformed `*.ledger.tsv` is reported per-file like any other malformed input, and does not stop
  the other files.
- A directory holding no `.ledger.tsv` behaves exactly as it did before, in the sense `COMMON.md`
  defines.

Do not change the two formats that already work.
