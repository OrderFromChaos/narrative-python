# Validation — does the skill beat the doc?

Held out of elicitation entirely. Nothing in Round 1-3 touches these two problems, so the skill
cannot have been fitted to them.

## Protocol

For each task, generate three implementations:

| arm | context given |
|---|---|
| `base` | the task statement only |
| `doc` | task + the full pre-existing style doc pasted in |
| `skill` | task + the finished `narrative` skill |

Then:

1. Strip identifying comments, shuffle, present as `1.py` / `2.py` / `3.py` with the mapping held
   back.
2. Rate each 1-5 for "is this how I would want it written", and mark every line you would comment
   on in review.
3. Score all three mechanically: `ruff check`, `pylint`, `mypy --strict`, `checks.py`.
4. Unblind.

**The result that matters is `skill` vs `doc`, not `skill` vs `base`.** Beating an empty context
proves nothing — any style guidance does that. If the skill does not beat the doc pasted verbatim,
it has not earned its context budget and should be cut back to a shorter rule list. That is a real
possible outcome, not a failure mode to design around.

## Task V1 — log triage tool

> Read a directory of JSONL log files written by the ingest pipeline. Each line has `timestamp`,
> `level`, `event`, and arbitrary extra fields. Produce a report: counts by event, the five
> slowest operations by a `duration_ms` field where present, and every `ERROR` line grouped by
> `event` with the first three examples of each. Handle malformed lines without aborting. Accept a
> time window and a minimum level. Write the report as both a terminal table and a JSON file.

Exercises: boundary parsing of untrusted JSON, error granularity, config strategy, closed sets for
level, collection typing, structured logging about a structured-logging tool, degrade-vs-abort.

## Task V2 — calibration drift checker

> Given a SQLite table of calibration readings (`device_id`, `taken_at`, `reference_value`,
> `measured_value`), find devices whose measurement error has drifted beyond tolerance. For each
> device compute the rolling mean error over the last N readings, compare against a per-device
> tolerance loaded from config, and classify as OK / WARN / FAIL. Emit a summary and exit nonzero
> if any device is FAIL.

Exercises: numeric code, closed sets with exhaustive dispatch, `NewType` on `device_id`, dataclass
modelling, per-device config lookup, the extraction-threshold question, and a natural home for a
property-based test on the rolling-mean invariant.

## Notes

Neither task mentions a device driver or a scan file, so P1 and P2 do not leak into them. V2
deliberately has a pure numeric core, which is where the R2-12 answer will show up if it is real.
