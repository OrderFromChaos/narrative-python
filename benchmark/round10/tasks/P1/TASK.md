# Task P1 — timesheet to payroll

Turn badge-reader punches into weekly pay per employee, and report every punch that could not be
paid.

## Inputs

An input directory holding:

- `roster.csv` — a header row `employee_id,name,hourly_rate,site`, then one employee per line.
  `hourly_rate` is a decimal string with at most two places (`18.50`). `name` is UTF-8 and may hold
  non-ASCII letters. `site` is a key of `site_timezones` in the rules file.
- `*.punches.jsonl` — one JSON object per line, one file per badge reader:
  `{"badge": "E104", "at": "2026-03-07T22:58:30-08:00", "direction": "in", "reader": "R2"}`.
  `at` is ISO 8601 with a UTC offset, with or without seconds. `direction` is `in` or `out`. Lines in
  a file are in recording order; the order between files is undefined. A badge reader whose network
  drops sends its punches again, so the same punch (same `badge`, `at` and `direction`) can appear
  more than once, in one file or across files.

One rules file, `payroll.json`, read from the input directory unless `--rules` names another path:

```json
{
  "site_timezones": {"north": "America/Los_Angeles"},
  "overtime_after_minutes": 2400,
  "overtime_multiplier": "1.5",
  "round_to_minutes": 15
}
```

All four keys are mandatory. `site_timezones` maps a site name to an IANA zone name;
`overtime_after_minutes` and `round_to_minutes` are positive integers; `overtime_multiplier` is a
decimal string. A rules file or roster that is unreadable or malformed, or that has an unknown timezone
or site, stops the run with exit code 2.

## What it does

1. Read the roster and the rules, then every `*.punches.jsonl` file in the input directory, in
   basename order. Other files are ignored.
2. A punch whose line is not a JSON object with the four string fields, whose `at` does not parse
   with an offset, or whose `direction` is neither `in` nor `out`, is a **malformed** punch. A punch
   whose badge is not in the roster is an **unknown badge** punch. Neither is paid.
3. Duplicate punches count once.
4. Per badge, sort the remaining punches by instant. Each `in` followed directly by an `out` is a
   **shift**. Any other punch (an `in` followed by an `in`, an `out` with no `in` before it, a final
   `in`) is **unpaired** and is not paid.
5. A shift's length is the elapsed time between its two instants, so a shift across a daylight
   saving change is paid for the time actually worked. Round each shift's length to the nearest
   multiple of `round_to_minutes`; a length exactly halfway rounds up.
6. A shift belongs to the week containing its `in` punch, in the employee's site time zone. Weeks
   start on Monday at 00:00 local time.
7. Per employee and week: minutes up to `overtime_after_minutes` are regular, the rest overtime.
   Gross pay is `regular_minutes / 60 × rate + overtime_minutes / 60 × rate × multiplier`, computed
   exactly and rounded once to cents, a half cent rounding up.
8. Write the outputs below, and record each employee-week in a SQLite database. Running again over
   the same inputs adds no rows; a run whose inputs change an employee-week's numbers updates that
   row.

## The outputs

`pay.json`, written with `json.dumps(report, indent=2, ensure_ascii=False) + '\n'`, keys in this order:

```json
{
  "generated_at": "2026-03-16T09:00:00+00:00",
  "input_dir": "fixture",
  "weeks": [
    {"employee_id": "E104", "name": "Zoë Ortega", "week_start": "2026-03-02",
     "regular_minutes": 2400, "overtime_minutes": 15, "gross_pay": "734.83"}
  ],
  "problems": [
    {"file": "dock.punches.jsonl", "line": 7, "badge": "E104", "problem": "unpaired in"}
  ],
  "totals": {"employees": 3, "shifts": 21, "duplicates": 1, "problems": 4, "gross_pay": "2716.91"}
}
```

The numbers above are an example of the shape only. `weeks` is sorted by `week_start`, then `employee_id`;
`problems` by `file`, then `line`. `problem` is one of `malformed`, `unknown badge`, `unpaired in`,
`unpaired out`. `gross_pay` is a string with exactly two decimal places. `input_dir` is the
argument as typed.

A summary table on stdout: one row per employee-week, then the totals.

Exit codes: 0 when there are no problems, 1 when there is at least one problem, 2 when the run could
not start (bad rules, bad roster, missing input directory).

The pay computation must also be importable: another program calls one function with the input
directory and an optional rules path, and gets the weeks and problems back without any file being
written.

## What is left to you

The package and module layout, the database schema, the table layout, logging, and any behaviour this
specification does not fix.

## The fixture

`fixture/` has a roster of three employees, two reader files and a rules file. Its cases: a shift
across the 2026-03-08 daylight saving change, a shift that crosses midnight into a new week, a shift
length exactly halfway between two rounding steps, a half-cent gross pay, a retransmitted punch, an
unpaired punch and an unknown badge.
