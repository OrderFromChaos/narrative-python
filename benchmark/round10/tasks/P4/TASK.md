# Task P4 — dependency license audit

Check every pinned dependency of several services against a license policy, and report each one
that the policy does not allow.

## Inputs

An input directory holding:

- `*.lock` — one per service. Each line is `name==version`, optionally followed by an environment
  marker (`; python_version < "3.12"`) and an inline comment (`  # pinned for CVE-2027-1234`). Lines
  that are blank or start with `#` are ignored. Any other line is **malformed**.
- `licenses.json` — the license of each released version, as an SPDX license expression:

```json
{"packages": {"Requests": {"2.31.0": "Apache-2.0"}, "redis": {"4.6.0": "MIT", "7.4.0": "RSALv2 OR SSPL-1.0"}}}
```

- `policy.json`:

```json
{
  "allowed": ["MIT", "BSD-3-Clause", "Apache-2.0"],
  "denied": ["GPL-3.0-only", "AGPL-3.0-only", "SSPL-1.0"],
  "exceptions": [
    {"package": "psycopg2", "license": "LGPL-3.0-or-later", "until": "2028-06-30", "reason": "legal review LR-118"}
  ]
}
```

All three keys are mandatory. A policy or license file that is unreadable or malformed stops the run
with exit code 2.

`--today YYYY-MM-DD` gives the audit date, so a run is reproducible.

## What it does

1. Package names compare after PEP 503 normalisation: lower case, with every run of `-`, `_` and `.`
   replaced by a single `-`. `Flask_SQLAlchemy`, `flask-sqlalchemy` and `flask.sqlalchemy` are one
   package, in the lock files, `licenses.json` and the exceptions alike.
2. For each lock entry, look up the license expression of that exact version. A version with no
   expression is an **unknown license** verdict.
3. An expression is built from license ids, `AND`, `OR` and parentheses. `AND` binds tighter than
   `OR`, so `MIT AND Apache-2.0 OR GPL-3.0-only` means `(MIT AND Apache-2.0) OR GPL-3.0-only`. License
   ids compare case-insensitively; the operators are upper case.
4. An id is **usable** for a package when it is in `allowed`, or when an exception for that
   package and that id is in effect: today is on or before its `until`. The verdict:
   - **allowed** when the expression can be satisfied with usable ids alone;
   - otherwise **denied** when the expression cannot be satisfied without at least one denied id;
   - otherwise **unreviewed**.
5. An exception whose `until` is before today is **expired**. Report it once, whether or not any lock
   still uses the package.
6. Record each verdict in a SQLite database. Running again with the same `--today` over the same
   inputs adds no rows.

## The outputs

`audit.json`, written with `json.dumps(audit, indent=2) + '\n'`, keys in this order:

```json
{
  "today": "2028-06-30",
  "input_dir": "fixture",
  "entries": [
    {"lock": "api.lock", "line": 3, "package": "redis", "version": "7.4.0",
     "license": "RSALv2 OR SSPL-1.0", "verdict": "unreviewed"}
  ],
  "expired_exceptions": [],
  "malformed": [{"lock": "worker.lock", "line": 5, "text": "celery>=5"}],
  "totals": {"entries": 12, "allowed": 9, "denied": 1, "unreviewed": 1, "unknown": 1}
}
```

The numbers above are an example of the shape only. `entries` is sorted by `lock`, then `line`. `package`
is the normalised name. `verdict` is one of `allowed`, `denied`, `unreviewed`, `unknown license`.
`input_dir` is the argument as typed.

A summary table on stdout: every entry that is not allowed, then the totals.

Exit codes: 0 when every entry is allowed and nothing is malformed or expired, 1 otherwise, 2 when the
run could not start.

The audit must also be importable: another program calls one function with the input directory, an
optional policy path and the date, and gets the audit back without any file being written.

## What is left to you

The package and module layout, the expression parser, the database schema and location, the table
layout, logging, and any behaviour this specification does not fix.

## The fixture

`fixture/` has two lock files, `licenses.json` and `policy.json`. Run it with `--today 2028-06-30`.
Its cases: names spelled three ways, a package whose license changed between versions, an expression
that depends on precedence, a lower-case license id, an exception on its last day, an expired
exception, an environment marker with an inline comment, and a malformed line.
