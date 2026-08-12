# Q23 follow-up — what "log at the raise site *and* the handle site" costs in a parser

Real code, not a snippet: each variant is `parseRecord` from `validation/v1_log_triage/skill.py`,
edited in place, whole-file. All four run on 3.10.18 and pass `ruff check`, `ruff format --check`,
`pylint --rcfile`, `mypy --strict`, `checks.py` and `vermin -t=3.10` **clean**. No variant is
disqualified by the toolchain; this one is decided on output, not on lint.

Fixture: one file, 10,000 malformed lines spread evenly over all seven distinct failure reasons
(the six raise sites in `parseRecord` plus the one inside `parseTimestamp`), and 100 good lines.

## The same two raise sites, three ways

```python
# V1 — helper (what the agent wrote). One DEBUG record for all six raise sites.
    except json.JSONDecodeError as exc:
        raise rejectLine(f'not valid JSON: {exc.msg}') from exc

    if not isinstance(payload, dict):
        raise rejectLine(f'top-level value is {type(payload).__name__}, not an object')

def rejectLine(reason: str) -> MalformedLineError:
    LOG.debug('line_rejected', extra={'reason': reason})
    return MalformedLineError(reason)
```

```python
# V2 — inline. A literal reading of Q23: a LOG call beside every raise.
    except json.JSONDecodeError as exc:
        reason = f'not valid JSON: {exc.msg}'
        LOG.debug('line_rejected', extra={'reason': reason})
        raise MalformedLineError(reason) from exc

    if not isinstance(payload, dict):
        reason = f'top-level value is {type(payload).__name__}, not an object'
        LOG.debug('line_rejected', extra={'reason': reason})
        raise MalformedLineError(reason)
```

The `reason` local is not padding — without it the f-string is written twice per site, which is
exactly the rote diffing R2b-P0 exists to prevent. Three lines per site is the honest cost.

```python
# V3 — handle site only. No raise-site logging at all; scanLogs already logs the drop.
    except json.JSONDecodeError as exc:
        raise MalformedLineError(f'not valid JSON: {exc.msg}') from exc

    if not isinstance(payload, dict):
        raise MalformedLineError(f'top-level value is {type(payload).__name__}, not an object')
```

```python
# V4 — V1, but the handle site tallies instead of narrating. Only the level policy changes.
            except MalformedLineError as exc:
                LOG.debug('line_skipped', extra={'source': str(path), 'line': line_number, ...})
                malformed.append(MalformedLine(path, line_number, str(exc)))
                dropped += 1
                continue
        # One actionable record per file: an operator cannot act on line 4471 of 10000, only on
        # "this file is mostly garbage".
        if dropped:
            LOG.warning('lines_skipped', extra={'source': str(path), 'dropped': dropped, 'of': len(lines)})
```

## Measured — 10,000 malformed lines, one file

| | V1 helper | V2 inline | V3 handle-only | V4 tallied |
|---|---|---|---|---|
| raise-site block, lines | **28** | **41** (+46%) | **28** | 28 |
| helper, lines | 5 | 0 | 0 | 5 |
| whole file, lines | 497 | 503 | 490 | 504 |
| log calls a reader must keep in sync | 1 | **6** | 0 | 1 |
| records emitted, `--verbose` (DEBUG) | 21,429 | **21,429** | 11,429 | 21,430 |
| stderr bytes, `--verbose` | 3.40 MB | 3.40 MB | 2.01 MB | 3.38 MB |
| records emitted, **default** (INFO) | 10,001 | 10,001 | 10,001 | **2** |
| stderr bytes, default | 1.85 MB | 1.85 MB | 1.85 MB | **268 B** |

**V1 and V2 emit byte-identical logs.** Verified record by record, ignoring only the wall-clock
`time` field and the report path in the last line: 21,429 of 21,429 identical. V2 buys 13 extra
lines and five extra maintenance points for literally zero observable difference. It is the rule
followed literally, and it is strictly dominated.

The GAPS prediction of 20k lines is confirmed and slightly beaten — 21,429, because
`parseTimestamp` also logs at its own raise site, so 1,428 lines get logged three times.

## What V3 actually loses

Nothing, on this program, measured:

- Raise-site record fields: `{reason}`. Handle-site record fields: `{source, line, reason}`.
  The handle site is a **strict superset**.
- The multiset of 10,000 `reason` strings at the raise site is **equal** to the multiset at the
  handle site (7 distinct reasons, 1,428–1,429 each). Nothing appears in one and not the other.
- V1's and V3's `line_skipped` records are identical, all 10,000.

What V3 loses is *structural*, not present in this fixture: the raise-site log is insurance against
a caller that catches and does not log. `parseRecord` has exactly **one** caller today. The moment
there are two, or one of them swallows `MalformedLineError`, V3 goes silent and V1 does not. That is
a real difference and it is not visible in any number above.

## Levels — the skill says nothing, and the guess is backwards

The agent chose DEBUG at raise, WARNING at handle. Measured, that is the wrong way round for a
degrade-and-report loop (Q24): the raise-site DEBUG costs **nothing in production** (suppressed at
the default INFO level), while the handle-site WARNING emits 10,000 records and 1.85 MB for one bad
file, every run, in production. The 20k-lines objection in GAPS is really a 10k-lines objection, and
it belongs to Q24, not Q23.

V4 changes only the levels — per-line to DEBUG, one per-file tally to WARNING — and takes the
default-level output from 10,001 records to **2**, with no loss of detail under `--verbose` (21,430
records) and none in the JSON report, which lists every malformed line either way.

Proposed rule: **the level of a per-item failure is bounded by what an operator can act on.** In a
loop that degrades and continues, the item logs at DEBUG at both sites and the *tally* logs once at
WARNING; the level rises to ERROR only where the failure aborts the unit of work. A record no one
can act on individually is a DEBUG record however severe it sounds.

## Recommendation

V1. And restate Q23 as: **the raise site records the generic fact once — however you factor that,
including a helper that logs and returns the exception — and the handle site records what it meant
here.** Add: in a degrade-and-report loop, the handle site logs the *aggregate*, not the item.

Counter-argument, stated fairly: `raise rejectLine(...)` is an unusual shape. A reader who has not
seen `rejectLine` cannot tell from the raise site that anything is logged, and a helper that both
logs and constructs is doing two things. V2 is honest at every site and needs no lookup. The reply
is the byte-identical logs plus six sync points versus one — but the readability objection is real
and V2 is not indefensible, only more expensive.

**Question: does the raise-site log survive as a rule at all once you accept that here it is
provably redundant with the handle site, and its only value is insurance against a second caller
that does not yet exist?**
