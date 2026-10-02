# Task P2 — subscription invoices

Bill each customer for one calendar month of a subscription service, prorating plan changes to the
second, and report every event that could not be billed.

## Inputs

An input directory holding:

- `customers.csv` — a header row `customer_id,name,timezone,state`, then one customer per line.
  `timezone` is an IANA zone name; `state` is a two-letter US state code. `name` is UTF-8 and may
  hold non-ASCII letters.
- `*.events.jsonl` — one JSON object per line, from several exporters:
  `{"customer": "C2", "at": "2028-03-16T00:00:00-04:00", "event": "change", "plan": "pro"}`.
  `at` is ISO 8601 with a UTC offset. `event` is `subscribe`, `change` or `cancel`; `plan` is
  present for `subscribe` and `change`. The order between files is undefined, and an exporter
  that times out sends again, so the same event (all four fields equal) can appear more than once.
- `prices.json`:

```json
{
  "plans": {"basic": "9.99", "starter": "10.00", "pro": "29.00"},
  "tax_rates": {"CA": "0.0725", "NY": "0.08875"}
}
```

`plans` maps a plan to its monthly price in dollars, as a decimal string with two places;
`tax_rates` maps a state to a rate, as a decimal string. Both keys are mandatory. A prices file or
customer file that is unreadable or malformed, or a customer whose zone or state is unknown, stops
the run with exit code 2. `--prices` may name a prices file outside the input directory.

## What it does

The month to bill is given as `--month YYYY-MM`.

1. Read the customers and prices, then every `*.events.jsonl` file in basename order. Other files
   are ignored.
2. A line that is not a JSON object with the fields above, whose `at` has no UTC offset, or whose
   `event` is unknown, is **malformed**. An event for a customer not in `customers.csv` is an
   **unknown customer** event; an event for a plan not in `prices.json` is an **unknown plan** event.
   None of these is billed.
3. Duplicate events count once.
4. Per customer, sort the remaining events by instant and replay them from the start: `subscribe`
   starts a plan, `change` switches to another plan, `cancel` ends the subscription. A `change` or
   `cancel` with no active subscription, or a `subscribe` while one is active, is **out of order**
   and is skipped.
5. The billing month runs from 00:00 on its first day to 00:00 on the first day of the next month,
   in the customer's time zone. Each stretch of the month on one plan is an invoice line, prorated by
   elapsed seconds: `price × seconds on the plan / seconds in the month`. A month with a daylight
   saving change is an hour shorter or longer than its number of days times 24 hours, and the
   proration uses the real length. Round each line to cents, a half cent rounding up.
6. Tax is the customer's state rate times the sum of the lines, rounded once to cents, a half cent
   rounding up.
7. Write the outputs below, and record each customer-month in a SQLite database. Running again over
   the same inputs adds no rows; a run whose inputs change a customer-month updates that row.

## The outputs

`invoices.json`, written with `json.dumps(report, indent=2, ensure_ascii=False) + '\n'`, keys in
this order:

```json
{
  "generated_at": "2028-04-01T09:00:00+00:00",
  "input_dir": "fixture",
  "month": "2028-03",
  "invoices": [
    {"customer_id": "C1", "name": "Ana López",
     "lines": [{"plan": "pro", "start": "2028-03-01T00:00:00-08:00",
                "end": "2028-04-01T00:00:00-07:00", "amount": "29.00"}],
     "subtotal": "29.00", "tax": "2.10", "total": "31.10"}
  ],
  "problems": [
    {"file": "web.events.jsonl", "line": 4, "customer": "C9", "problem": "unknown customer"}
  ],
  "totals": {"invoices": 1, "events": 9, "duplicates": 1, "problems": 1, "billed": "31.10"}
}
```

The numbers above are an example of the shape only. A customer with no plan active during the month gets no
invoice. `invoices` is sorted by `customer_id`, `lines` by `start`, `problems` by `file`, then
`line`. `problem` is one of `malformed`, `unknown customer`, `unknown plan`, `out of order`. Line
`start` and `end` are local times with their offset. Amounts are strings with exactly two decimal
places. `input_dir` is the argument as typed.

A summary table on stdout: one row per invoice, then the totals.

Exit codes: 0 when there are no problems, 1 when there is at least one problem, 2 when the run could
not start.

The invoicing must also be importable: another program calls one function with the input directory,
the month and an optional prices path, and gets the invoices and problems back without any file
being written.

## What is left to you

The package and module layout, the database schema, the table layout, logging, and any behaviour this
specification does not fix.

## The fixture

`fixture/` has four customers in two time zones, two event files and a prices file. Bill it with
`--month 2028-03`. Its cases: the daylight saving change in March, a plan change and a cancellation
mid-month, a subscription that started before the month, a tax of exactly half a cent, a resent
event, and each kind of problem.
