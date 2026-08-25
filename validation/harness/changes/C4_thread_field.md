# Change C4 — carry a new field from the billing export to the report

> Read `COMMON.md` first. It states the database and unchanged-behaviour rules that apply to
> every change request.

Finance needs to know which account a charge sits in, so the export now carries it and the report
must show it.

## The format change

`*.billing.csv` gains a fifth column, `account_id`, after `region`:

    resource_id,sku,monthly_cents,region,account_id
    i-0001,compute-gpu,250000,us-east-1,acct-4417
    i-0002,object-store,1200,us-west-2,acct-9002

The column is **required**. A billing file whose header lacks it is malformed and is reported as
such, like any other malformed input.

The scan format does not gain the field and does not change.

## What must be true afterwards

- Every finding that came from a billing record carries its `account_id`, in the summary table and
  in the JSON report.
- A finding with no billing side — one raised from a scanned resource alone — carries no
  `account_id`, and states that absence rather than inventing a value.
- The SQLite rows carry it too, and a re-run over unchanged input still adds no row. An existing
  database is brought forward, per `COMMON.md`.
- `account_id` takes part in no matching. It is carried, not compared.

This is the change that asks whether a new field threads from a reader, through the join, to three
outputs.
