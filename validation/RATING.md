# Blind rating

Three implementations of each task sit in `v1_log_triage/blind/` and `v2_drift_checker/blind/` as
`1.py`, `2.py`, `3.py`. One was written with no style guidance, one with the pre-existing style doc,
one with the skill. The order differs between the two tasks. Strings that would give the arm away
have been redacted.

**Do not open `MANIFEST.json` until you have rated.** `SCORES.json` holds the mechanical results
and is also safe to leave until afterwards — it says nothing about whether the code is any good.

## What to record

For each file, per task:

| | 1.py | 2.py | 3.py |
|---|---|---|---|
| 1–5: is this how I would want it written | | | |
| lines I would comment on in review | | | |

The **marked lines matter more than the number.** A rating tells me which arm won; the marks tell
me which rules were load-bearing and which were noise. If you find yourself wanting to comment on
something no rule covers, that is the most valuable thing you can report — it is a gap in the
skill, not a gap in the code.

Rough anchors for the 1–5, so the numbers mean the same thing across tasks:

- **5** — I would merge this as-is.
- **4** — I would merge after comments; nothing structural.
- **3** — sound but I would want changes before it went in.
- **2** — I would send it back.
- **1** — I would rewrite it.

## The question this answers

Only one comparison decides anything: **skill vs doc.**

Beating the no-guidance arm proves nothing — any style guidance does that, and both unguided arms
already came in as the longest code in their task. If the skill does not beat your doc pasted
verbatim, it has not earned its context budget, and the right move is to cut it back to a short
rule list rather than defend it.

That is a real possible outcome. The two tasks were written before any elicitation and neither
mentions a scan file or a device driver, so nothing in Rounds 1–3 could have been fitted to them.
