# NAR008 is wrong more often than it is right

`NAR008` fires on any statement of three or more lines that another statement follows. This measures
whether that has anything to do with where a blank line belongs.

## Method

Twelve functions, written in the house style, with **every internal blank line removed**. Eight
short (bodies of 3 to 11 lines), four long (14 to 26). The author marked up where the blank lines
belong, without seeing where the checker fires. The checker was then run against the author's own
version.

```
nar008_stripped_short.py    8 functions, blanks removed
nar008_stripped_long.py     4 functions, blanks removed
nar008_golden_long.py       the author's markup of the long four
```

Anything `NAR008` still reports on the golden file is a blank line it wants and the author did not.

## Result

| | |
|---|---|
| blank lines the author placed | **23** |
| `NAR008` findings | 12 |
| findings that landed on one of them | **5** |
| false positives | 7 — 58% of everything it says |
| false negatives | 18 — 78% of what was wanted |
| **precision / recall** | **42% / 22%** |

`nar008_stripped_long.py` produces 6 findings. `nar008_golden_long.py`, the corrected version,
still produces 2.

## The two findings that survive correction

```python
    connection.executemany(
        'INSERT OR IGNORE INTO readings VALUES (?, ?)',
        [(reading.device_id, reading.celsius) for reading in readings],
    )
    connection.commit()                                     # NAR008 wants a blank line here
```

```python
    LOG.warning(
        'batch_done',
        extra={'stored': len(readings), 'refused': len(refusals), 'pruned': deleted.rowcount},
    )
    report = RoundReport(len(readings), len(refusals), deleted.rowcount)   # and here
```

Both are a statement and the statement that continues its work. Writing them apart asserts a
boundary that is not there, and `SKILL.md` says a blank line inside a function has exactly one
meaning.

## Where it is silent and a blank line belongs

`parseFrame`, 15 lines, **zero findings**. The author placed three:

```python
    if len(raw) != struct.calcsize(FRAME_FORMAT):
        raise CorruptFrameError(f'{device_id}: wrong length')
    if not raw.startswith(MAGIC):
        raise CorruptFrameError(f'{device_id}: bad magic')

    magic, celsius, checksum = struct.unpack(FRAME_FORMAT, raw)

    # validate
    expected = int(abs(celsius) * 100) % CHECKSUM_MODULUS
    if checksum != expected:
        raise CorruptFrameError(f'{device_id}: checksum {checksum} wanted {expected}')
    ...

    reading = Reading(device_id, round(celsius, 2))
    return reading
```

Arrival guards, decode, validate, build. Four steps, three boundaries, no multi-line statement
anywhere — so the check has nothing to say about the function it should have the most to say about.

`driftSlope`, 14 lines of linear arithmetic, also zero findings and four author blanks. That one
refutes the reading that blanks mark workflow *phases*: a pure computation was grouped into
calculation steps.

## R6-10 is refuted on its own case

`R6-10` kept `NAR008` as written, on two grounds. Both fail.

> the blank line is correct: defining a record and serialising it are logically distinct operations

That exact shape was put to the author:

```python
    record = {
        'device_id': reading.device_id,
        'celsius': reading.celsius,
        'site_code': site_code,
        'schema': 1,
    }
    LOG.info('reading', extra=record)
    return record
```

**No blank line.** The author reads building a record and emitting it as one step.

> the real fault is upstream — a large dict should not be passed around, so it should be a frozen
> dataclass

`logging` takes `extra=` as a dict by API. A frozen dataclass is not accepted. The remedy does not
exist for the case that fires most, because `Q08` mandates structured log calls and any call with
four fields explodes past three lines.

`R6-10` is not wrong. It is narrower than its wording: it was decided on one shape, and recorded as
"keep `NAR008` as written".

## Recommendation

**Delete `NAR008`. Keep the prose rule, which was right all along.**

`SKILL.md` already says a blank line separates logically self-contained blocks and that this is its
only meaning. That sentence needs no change. What the markup adds:

- blank lines **recur into nested blocks** — one function placed four inside a single loop body
- **length is not the trigger**, in either direction
- **a multi-line statement and the statement consuming its value are one step**
- a body of **8 lines or under takes no internal blanks at all**
- a blank precedes a `return` when the phase before it is unrelated, not when the value was just
  built

None of that is mechanically checkable, which is why the recommendation is deletion rather than a
better proxy.

## Counter-argument, stated fairly

**One marker, one sitting.** These are one person's blank lines on twelve functions written for the
purpose. A second pass on the same code could differ, and no repeat was taken.

**The functions were built to probe the rule.** They over-represent multi-line statements followed
by their consumers, which is the shape the check is worst at. A random sample of real code would
score `NAR008` better than 42%.

**Deleting a check removes the only mechanical enforcement of blank-line discipline the style has.**
`NAR008` is wrong often, but the rule that replaces it is enforced by nobody. The honest position is
that this trades a noisy check for no check, and that the noisy check was still catching 5 real
cases out of 23.

**A narrower check was available and not taken.** Exempting a statement whose successor consumes its
value would have fixed all three of the shapes that started this, kept a mechanical rule, and cost
one function in `checks.py`. It was rejected because the measurement shows the remaining signal is
weak, not because it would not work.
