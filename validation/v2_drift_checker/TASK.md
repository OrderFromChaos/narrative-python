# Task V2 — calibration drift checker

Given a SQLite table of calibration readings (`device_id`, `taken_at`, `reference_value`,
`measured_value`), find devices whose measurement error has drifted beyond tolerance.

For each device:
- compute the rolling mean error over the last N readings
- compare against a per-device tolerance loaded from config
- classify as OK / WARN / FAIL

Emit a summary. Exit nonzero if any device is FAIL.

Single file. Python 3.10+. Standard library only, except `hypothesis` if you write property tests.
