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

## A known violation, kept on purpose

`validation/v1_log_triage/skill.py` carries five comments citing benchmark decision ids — `Q08`,
`Q22`, `Q23`, `Q18` and `R2-08` — in code the skill wrote as if for a user. `R7-D04-comments` and
`R7-D04-comments-scope` forbid exactly that: a file the skill generates is user code wherever it
sits, and an id nobody outside this repository can look up is not a comment, it is negotiation
residue.

The file is **not** edited. It is the evidence that produced the rule, and changing it to conform
would erase the only demonstration of the defect. `SKILL.md` gains the prohibition instead.

Two things worth knowing. `SKILL.md`'s own python blocks contain no such citations, so the skill
never taught this — the agent mirrored the register of a rule document dense with them, which is why
the prohibition has to be explicit rather than implied. And `prepare_blind.py` had already classified
citations as telltales: its `TELLTALES` regex redacts them before rating, so `blind/1.py`,
`blind/2.py` and `blind/3.py` carry none and `SCORES.json` was never affected.

## SCORES.json does not fully reproduce

`v2_drift_checker/skill.py` has no module docstring, so `NAR009` fires on it. `SCORES.json` records
`"checks": 0` for that arm. Confirmed against the checker as shipped at `HEAD`, so the score was
wrong when it was written and no later change caused it. (`R8-D36`)

This is the table `README.md` Status cites as the project's main quantitative claim for itself — the
skill arm at 0 checker findings against the doc arm at 11. One cell of it does not reproduce, and the
other cells were not re-verified. **Regenerate the whole table with `prepare_blind.py` before citing
it again.**

## V3 — the multi-module task, rated openly

`validation/v3_manifest_audit/` is the first held-out task that spans several modules. Round 7 and
round 8 produced roughly 130 rules about multi-module structure and no held-out task exercised any
of them.

**The arms are not v1's arms.** v1 and v2 compared no-guidance against the prior style doc against
the skill. That prior doc is not in this repository and the question is stale. V3 compares:

| arm | context |
|---|---|
| `base` | the task alone |
| `skill` | `SKILL.md` and the config, with **`architecture.md` withheld** |
| `full` | the same plus `architecture.md` |

`skill` against `full` is the comparison that matters: does `architecture.md` earn its context
budget on a program that spans files.

**Blinding is dropped, deliberately.** The directory tree identifies the arm before a line is read,
and normalising the layout would destroy what is being measured. That is a real limitation on the
result, stated up front rather than discovered afterwards as it was for v1.

**The mechanical scores cannot decide it.** Every rule `architecture.md` adds is one no tool checks,
so `skill` and `full` should score alike. If they do, the entire case for `architecture.md` rests on
the human rating in `v3_manifest_audit/RATING.md`.
