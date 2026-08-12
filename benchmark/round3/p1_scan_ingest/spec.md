# P1 — Scanner batch ingest

## The problem

A batch ingest step for a materials-inspection scanner. Given a directory of binary `.scan` files:

1. Parse a fixed 32-byte header with `struct`: magic `b'ISCN'` (4 bytes), version `uint16`, scan_id `uint32`,
   sample_ref 12-byte null-padded ASCII, pixel_count `uint32`, repetitions `uint16`, checksum `uint32`.
2. Look up `sample_ref` in a config mapping loaded once from a JSON file (stand-in for the spreadsheet-derived
   config). The config supplies an expected `pixel_count` and a `site_code`.
3. Validate: magic matches; version is supported (1 or 2); sample_ref is in the config; pixel_count matches the
   config's expected value; checksum matches a recomputed sum over the payload (everything after the header).
4. Insert a row into SQLite (`sqlite3`, no ORM): scan_id, sample_ref, site_code, pixel_count, repetitions,
   source filename, ingested_at.
5. Move the file to `archive/` on success, `quarantine/` on failure.
6. Idempotent: re-running over the same input must not double-insert. UNIQUE constraint on scan_id, conflict handled.
7. Partial batch failure: one bad file must not abort the batch. Per-file outcome summary at the end.
8. Structured JSONL logging: one JSON object per line to `jsonl_logs/scan_ingest.jsonl`, with at minimum timestamp,
   level, event, and the relevant fields.

All three files implement this identically. Same outcomes, same summary, same rows in the database. Standard library
only. Each runs standalone:

```
python3 a_procedural.py <input_dir> <config.json> --db <path.db>
```

## Review instructions

Style is now identical across all three — same rules, same tooling, same clean run — so architecture is the only variable left.

1. Rank the three.
2. Name three things you would change in your top pick.
3. Name one thing you would steal from each of the other two.
4. Flag anything that reads as over-engineered, and anything that reads as under-specified.
