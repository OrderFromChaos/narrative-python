# Task P10 — change request: key signatures, tempo range, a channel filter

`fixture/midi_report/` is a working MIDI file analyser, written to `fixture/ORIGINAL_TASK.md`. Make
the three changes below in that package. Keep everything the original specification requires, and
keep the package passing `verify.py`.

Use the standard library only.

## 1. Key signature

Meta event `FF 59 02 sf mi` is a key signature. `sf` is the number of sharps (1 to 7) or flats (-1
to -7), stored as a signed byte, and `mi` is 0 for major and 1 for minor. A key-signature event with
`sf` outside -7 to 7 or `mi` other than 0 or 1 is ignored.

Each file in `midi.json` gets `"key_signature"`: the first valid key signature by tick, then track
order, as the key's name, or `null` when there is none. Names use `b` and `#`:

| sf | -7 | -6 | -5 | -4 | -3 | -2 | -1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| major | Cb | Gb | Db | Ab | Eb | Bb | F | C | G | D | A | E | B | F# | C# |
| minor | Ab | Eb | Bb | F | C | G | D | A | E | B | F# | C# | G# | D# | A# |

followed by ` major` or ` minor`: `"Eb major"`, `"C minor"`.

## 2. Tempo range

Each file gets `"bpm": {"min": …, "max": …}`, over every tempo in effect for some part of the file's
length. Beats per minute is 60,000,000 divided by the microseconds per quarter note, rounded with
`round(x, 3)`. The default of 500,000 counts when it is in effect before the first set-tempo
event. A set-tempo event at or after the file's last end-of-track event is in effect for no time
and does not count.

## 3. A channel filter

`--channel N`, with N from 1 to 16, restricts the analysis to that channel: the notes, the pitch
range, the longest note, the polyphony, the hanging notes and the orphan offs. Drum hits count only
when N is 10. The length, the time signature, the tempo fields and the key signature are unchanged.
The report gets a top-level `"channel"`: N, or `null` without the option. The totals add up the
filtered values.

## The summary line

Each summary line also has the key signature when the file has one.

## What is left to you

Where the changes go in the package, the summary layout, and any behaviour this specification does
not fix.

## The fixture

`fixture/midi/` has the five files of the original task and `sonata.mid`. Its cases: an invalid key
signature (sf = 9) at tick 0 before a valid one, a key signature in flats stored as a signed byte, a
tempo change after the default was in effect, a tempo change on the end-of-track tick, and notes on
channels 1 and 3.
