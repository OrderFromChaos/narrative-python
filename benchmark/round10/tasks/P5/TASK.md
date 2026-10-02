# Task P5 — configuration layer audit

Merge layered TOML configuration files into one configuration per environment, and report every
problem in the result.

## Inputs

An input directory with:

- `layers.toml`:

```toml
current_version = "1.10.0"
secret_key_pattern = "(?i)(password|secret|token)$"

[environments]
staging = ["base", "staging"]
prod = ["base", "staging", "prod"]
canary = ["base", "prod", "canary"]
```

  Each environment is a list of layer names, applied left to right. A layer name `x` is the file
  `x.toml` in the input directory.
- One `<layer>.toml` per layer name.
- `deprecated.toml`:

```toml
[[key]]
path = "db.pool_size"
removed_in = "1.9.0"
replacement = "db.pool.max"
```

`current_version` and every `removed_in` are versions of the form `MAJOR.MINOR.PATCH`. A layer file,
`layers.toml` or `deprecated.toml` that is missing or not valid TOML stops the run with exit code 2.

## What it does

1. **Merge.** For each environment, start from an empty table and apply its layers in order. Where
   both the merged result and the layer have a table at the same key, merge the two tables key by
   key, recursively. Any other value at the same key, an array included, replaces the earlier
   value.
2. **Type change.** A layer that sets a key already set by an earlier layer of the same environment,
   with a value of another TOML type, is a **type change**. The TOML types are string, integer,
   float, boolean, datetime, date, time, array and table. `true` and `1` are of different types, and
   so are `25` and `25.0`.
3. **Deprecated key.** A key of the merged result whose dotted path is a `path` in `deprecated.toml`
   is a **removed key** when its `removed_in` is at or below `current_version`, and a **deprecated
   key** otherwise.
4. **Secret.** A key of the merged result whose last path segment matches `secret_key_pattern` and
   whose value is a non-empty string is a **secret in config**.
5. **Rollout.** Under the merged `flags` table, every flag's `rollout` must be an integer from 0 to
   100. Under the merged `experiments` table, the `share` values of each experiment's arms must be
   integers that sum to 100. A value out of range or a sum other than 100 is a **bad rollout**.

## The outputs

`audit.json`, written with `json.dumps(audit, indent=2, sort_keys=False) + '\n'`, keys in this order:

```json
{
  "input_dir": "fixture",
  "environments": [
    {"name": "canary", "layers": ["base", "prod", "canary"],
     "config": {"cache": {"enabled": true}},
     "findings": [
       {"kind": "type change", "path": "flags.search_v2.rollout", "layer": "canary",
        "detail": "integer in prod, float in canary"}
     ]}
  ],
  "totals": {"environments": 3, "errors": 4, "warnings": 1}
}
```

The values above are an example of the shape only. `environments` is sorted by name and `findings`
by `path`, then `kind`. `config` is the merged configuration with keys sorted at every level; a
datetime, date or time is written as its ISO 8601 string. A **deprecated key** is a warning; every
other kind is an error. `input_dir` is the argument as typed.

A summary on stdout: one line per finding, then the totals.

Exit codes: 0 when there are no errors, 1 when there is at least one error, 2 when the run could not
start.

The audit must also be importable: another program calls one function with the input directory and
gets the audit back without any file being written.

## What is left to you

The package and module layout, the `detail` wording, the summary layout, logging, and any behaviour
this specification does not fix.

## The fixture

`fixture/` has `layers.toml`, `deprecated.toml` and four layer files. Its cases: a removed version
that sorts after the current version as a string, a boolean replaced by an integer, an integer
replaced by a float, an array replaced by a shorter array, an environment that skips a layer, dotted
keys and table headers for the same table, an empty secret, a key that contains `token` but does not
end with it, a rollout out of range and experiment shares that sum to 99.
