# Task P3 — snapshot pruner

Decide which backup snapshots to keep under a retention policy, delete the rest on request, and
report every file that could not be judged.

## Inputs

- A snapshot directory. A snapshot is a regular file named `db-YYYYMMDDTHHMMSSZ.tar.zst`, where the
  timestamp is the snapshot's instant in UTC. Anything else in the directory (other names,
  subdirectories, symbolic links) is not a snapshot and is never touched.
- A policy file, `--policy PATH`:

```json
{
  "timezone": "America/New_York",
  "keep": {"hourly": 3, "daily": 3, "weekly": 2, "monthly": 2}
}
```

`timezone` is an IANA name. `keep` has the four rules, each a non-negative integer; a rule may be
`0`. A policy that is unreadable or malformed, or has an unknown timezone, stops the run with
exit code 2.

- `--now INSTANT`, an ISO 8601 instant with a UTC offset. Snapshots are judged as of this
  instant, so a run is reproducible.

## What it does

1. List the snapshot directory. A file whose name has the snapshot shape but whose timestamp is not
   a real instant (`db-20281131T000000Z.tar.zst`) is **unparseable**. A snapshot later than `--now`
   is **from the future**. Both are reported and kept, never deleted, and take no part in the
   rules below; neither can be the newest snapshot.
2. For each rule, snapshots fall into periods by local time in the policy's timezone: `hourly` by
   local date and hour, `daily` by local date, `weekly` by ISO week, `monthly` by local year and
   month. Periods follow the local wall clock, so on the night a daylight saving change makes an
   hour occur twice, both copies of that hour are one hourly period.
3. Under a rule with `keep: N`, the newest snapshot of each of the N most recent periods that contain
   a snapshot is kept. Rules are independent: a snapshot kept under one rule does not count toward
   another rule's N. A snapshot is kept when it is kept under at least one rule.
4. The newest snapshot is always kept, regardless of the policy.
5. Every other snapshot is deleted, but only with `--apply`. Without it, nothing is deleted and only the outputs are written.
6. Record each run's decisions in a SQLite database: one row per snapshot per run. A run with the
   same `--now` over the same directory and policy adds no rows.

## The outputs

`plan.json`, written with `json.dumps(plan, indent=2) + '\n'`, keys in this order:

```json
{
  "now": "2028-11-05T08:00:00+00:00",
  "snapshot_dir": "fixture/snapshots",
  "applied": false,
  "keep": [
    {"file": "db-20281105T073000Z.tar.zst", "local": "2028-11-05T02:30:00-05:00",
     "rules": ["hourly", "daily", "weekly", "monthly", "newest"]}
  ],
  "delete": [
    {"file": "db-20281105T053000Z.tar.zst", "local": "2028-11-05T01:30:00-04:00"}
  ],
  "problems": [
    {"file": "db-20281131T000000Z.tar.zst", "problem": "unparseable"}
  ]
}
```

The entries above are an example of the shape only. `keep` and `delete` are sorted newest first;
`rules` gives the rules under which the snapshot is kept, in the order `hourly`, `daily`, `weekly`, `monthly`,
`newest`; `problems` is sorted by `file`. `local` is the snapshot's instant in the policy's timezone,
with its offset. `snapshot_dir` is the argument as typed.

A summary on stdout: one line per snapshot with its decision, then the counts.

Exit codes: 0 when there are no problems, 1 when there is at least one problem, 2 when the run could
not start, or when `--apply` failed to delete a file.

The plan must also be importable: another program calls one function with the snapshot directory,
the policy path and the instant, and gets the plan back without any file being written or deleted.

## What is left to you

The package and module layout, the database schema and location, the summary layout, logging, and
any behaviour this specification does not fix.

## The fixture

`fixture/` has `policy.json` and `snapshots/`. Run it with `--now 2028-11-05T08:00:00Z`. Its cases:
the repeated hour on the night of 2028-11-05, a snapshot whose UTC date differs from its local date,
an unparseable name, a snapshot from the future, a file that is not a snapshot, a subdirectory and a
symbolic link.
