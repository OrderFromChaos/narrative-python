# Proposals from the cycle 10 review (R10-rating11)

Reply with the numbers you approve and any edits, and pick a task for cycle 11.

## 1. Lint "its own"

**Where:** `checks.py`, as `NAR018`, in the same family as `NAR012` to `NAR016`.

**Flags:** `its own`, `their own`, `X's own` in comments and docstrings.

**Message:** `possessive "own" in a comment or docstring: drop "own", or name the owner`

| text | records | hits |
|---|---|---|
| round 10 Claude corpus | 478 | 27 |
| CPython stdlib comments | 1,500 | 0 |

The `no its own` bullet in **Sentence form** (R10-Q41) stays; the check only enforces it.

## 2. pendulum at the boundary

**Where:** the pendulum bullet in `SKILL.md`, **Types**.

> A library that returns `datetime` values, such as `tomllib`, `sqlite3` or a JSON decoder, is a
> boundary: convert each value to pendulum where it enters. Greenfield code uses pendulum always.

**From:** both cycle 10 runs kept `tomllib`'s `datetime` values because "tomllib produces them".

## 3. Next task: something other than enterprise software

All three have pitfalls that are not JSON or TOML type checks, so the bool/int comment has no
reason to appear.

### A. ChordPro transposer (recommended)

Transpose songs in ChordPro format (`[Am]Here comes the [F]sun`) by N semitones, and pick sharps or
flats from the target key.

- **Enharmonics:** `E#` is `F`; `Cb` is `B`. Spelling follows the key: `Bb` in F major, `A#` in
  F# major.
- **Slash chords:** `D/F#` transposes both parts.
- **Chord qualities:** `Cmaj7`, `C7`, `Cm7b5`, `Csus4`, `C6/9`; only the root and bass move.
- **Capo:** a `{capo: 3}` directive changes the sounding key, not the written chords.
- **Lyrics alignment:** a chord-over-lyrics output keeps each chord above its syllable, though a
  transposed chord name can be longer or shorter.

### B. Golden-hour planner for photographers

For a list of places and dates, compute sunrise, sunset and the golden and blue hours, using the
NOAA solar position equations.

- **Polar day and night:** no sunrise at all at 78°N in June or December.
- **Local dates:** an event's local date can differ from its UTC date near the date line.
- **DST:** a sunrise on the morning of a clock change.
- **Atmospheric refraction:** sunrise is when the sun's centre is 0.833° below the horizon, not 0°.
- **Tolerance:** expected times are within a minute, so the output format must round, not truncate.

### C. Chess game replayer

Replay PGN games move by move, reject the first illegal move, and report the final position as FEN
and the result.

- **Castling:** not out of, through or into check, and lost when the king or that rook moves or the
  rook is captured.
- **En passant:** only on the move immediately after the double step.
- **Disambiguation:** `Nbd7`, `R1e2`, and a pinned piece that makes a disambiguation unnecessary.
- **Promotion** and **threefold repetition**, which needs the same castling and en passant rights.

This one is large; a run may take two to three times as long as earlier tasks.
