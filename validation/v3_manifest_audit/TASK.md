# Task V3 — dependency manifest auditor

Audit the dependencies a repository declares against a policy.

## Inputs

Two lockfile formats, both of which you must read:

- `requirements.lock` — one `name==version` per line, `#` comments, blank lines ignored.
- `packages.json` — `{"packages": [{"name": ..., "version": ..., "source": ...}]}`.

One policy file, `policy.json`:

```json
{
  "banned": ["leftpad", "eventstream"],
  "minimum_versions": {"requests": "2.31.0"},
  "allowed_sources": ["pypi", "internal"]
}
```

## What it does

1. Read every manifest in an input directory, whichever format each is.
2. Check each package against the policy: banned name, version below the minimum, source not allowed.
3. Record every finding in SQLite, keyed so a re-run over the same manifest does not double-insert.
4. Print a summary table, and write a JSON report.
5. One malformed manifest must not stop the others. Report per-manifest outcomes at the end.
6. Exit non-zero when any finding is a banned package.

## Constraints

- **Several modules.** The two formats, the policy, the store, the report and the entry point are
  distinct concerns; do not put them in one file.
- It must also be **importable**: another program should be able to call the audit without running
  the command-line tool.
- Python 3.11+. Standard library only. No network — read from the input directory.
- It must run. Include a small fixture directory so `python3 -m <package> <fixture-dir>` works.

## Deliverable

A package directory, plus whatever fixture files it needs. Nothing else.
