# Task V1 — log triage tool

Read a directory of JSONL log files written by an ingest pipeline. Each line has `timestamp`,
`level`, `event`, and arbitrary extra fields.

Produce a report:
- counts by event
- the five slowest operations by a `duration_ms` field, where present
- every `ERROR` line grouped by `event`, with the first three examples of each

Requirements:
- Handle malformed lines without aborting.
- Accept a time window and a minimum level.
- Write the report as both a terminal table and a JSON file.

Single file. Python 3.10+. Standard library only.
