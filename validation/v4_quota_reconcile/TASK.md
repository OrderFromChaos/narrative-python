# Task V4 — storage quota reconciler

Reconcile what a fleet of hosts reports it is storing against the quota each team is allowed.

## Inputs

Two usage-report formats, both of which you must read:

- `*.usage` — one `path<TAB>size` per line, `#` comments, blank lines ignored. Size carries a unit
  suffix: `4096`, `12K`, `1.5G`, `800M`, `2T`. **This format names no owning team.**
- `*.usage.json` — `{"host": ..., "entries": [{"path": ..., "bytes": ..., "team": ...}]}`. Sizes are
  plain integers. **This format names the owning team on every entry.**

One quota file, `quotas.json`:

```json
{
  "team_quotas": {"platform": "500G", "search": "2T"},
  "default_quota": "100G",
  "exempt_paths": ["/var/log/audit"]
}
```

## What it does

1. Read every usage report in an input directory, whichever format each is.
2. Total the usage per team, and compare each total against that team's quota. A team the quota file
   does not name gets `default_quota`. A path listed in `exempt_paths` counts toward no total.
3. Rank the teams that are over quota, worst overage first, and rank each team's paths by size.
4. Record every overage in SQLite, keyed so a re-run over unchanged reports does not double-insert.
5. Print a summary table, and write a JSON report.
6. One malformed report must not stop the others. Report per-file outcomes at the end.
7. Exit non-zero when any team is over quota.

## Constraints

- **Several modules.** The two formats, the quota file, the store, the report and the entry point
  are distinct concerns; do not put them in one file.
- It must also be **importable**: another program should be able to run the reconciliation without
  running the command-line tool.
- Python 3.11+. Standard library only. No network — read from the input directory.
- It must run. Include a small fixture directory so `python3 -m <package> <fixture-dir>` works.

## Notes on the data

- Size units are powers of 1024: `1K` is 1024 bytes, `1M` is 1024K, and so on. A size may carry a
  decimal point. A bare number is bytes.
- The two formats do not carry the same fields, and the difference is not an oversight in this spec.
- The fixture must exercise a malformed report, so that requirement 6 is visible when the tool runs.

## Deliverable

A package directory, plus whatever fixture files it needs. Nothing else.
