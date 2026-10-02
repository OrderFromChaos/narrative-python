# Task P7 — MIDI file analyser

Read Standard MIDI Files, pair every note's start with its end, place each note in seconds, and
report what each file plays.

Use no MIDI library: the standard library only.

## Inputs

An input directory of `*.mid` files, read in basename order. Each is a Standard MIDI File:

- A file is a sequence of chunks. Each chunk is a 4-byte ASCII type, a 4-byte big-endian length,
  then that many bytes. The first chunk is `MThd` with three 16-bit big-endian fields: format (0 or
  1), the number of track chunks, and the division. Track chunks have type `MTrk`. A chunk of any
  other type is skipped.
- When the top bit of the division is 0, the division is ticks per quarter note. When it is 1, the
  file uses SMPTE time, which this program does not support.
- A track is a sequence of events. Each event starts with a delta time in ticks since the previous
  event of the same track, written as a variable-length quantity: 7 bits per byte, most significant
  first, with the top bit set on every byte except the last.
- After the delta time comes a status byte, or a data byte under **running status**:
  - `8n` note off and `9n` note on, each with two data bytes (pitch, velocity). `An`, `Bn` and `En`
    also take two data bytes, `Cn` and `Dn` take one. `n` is the channel, 0 to 15.
  - A data byte (top bit 0) where a status byte is expected repeats the last channel status byte of
    the track. Meta events leave running status unchanged.
  - `FF type length data` is a meta event, with the length as a variable-length quantity. The ones
    that matter here: `51` set tempo (3 bytes, microseconds per quarter note), `58` time signature
    (numerator, then the denominator as a power of two, then two bytes not used here), `2F`
    end of track.
  - `F0 length data` and `F7 length data` are system exclusive events, skipped.

## What it does

1. **Parse** each file. A file is **unreadable** when it does not start with `MThd`, when a chunk or
   an event runs past the end of the data, or when it uses SMPTE time. An unreadable file is
   reported with an error and the other files are still analysed.
2. **Tempo.** Set-tempo events apply from their tick onward to every track of the file, whichever
   track they are in. Before the first one the tempo is 500,000 microseconds per quarter note. A
   tick's time in seconds is the sum, over each tempo span before it, of the span's ticks times its
   microseconds per quarter note, divided by the division and by 1,000,000.
3. **Notes.** A note on with velocity above 0 starts a note. A note off, or a note on with velocity 0,
   ends a note of the same channel and pitch. When several such notes are open, it ends the one that
   started first. An end with no open note is an **orphan off** and is otherwise ignored. A note
   still open at the end-of-track event of its track ends there and is **hanging**.
4. **Drums.** Channel 10 (`n` = 9) is percussion. Its note starts are counted as drum hits and take no
   part in the notes, the pitch range, the longest note or the polyphony.
5. **Per file:**
   - the time signature of the first time-signature event, as `numerator/denominator`, or `4/4` when
     there is none
   - the number of set-tempo events
   - the length in seconds: the time of the latest end-of-track event
   - the number of notes, the lowest and highest pitch as note names, and the longest note. Pitch 60
     is `C4`, and names use sharps: `C`, `C#`, `D`, … `B`, with the octave as pitch // 12 - 1. The
     longest note is the one with the most seconds. Ties go to the earliest start, then the lowest
     pitch.
   - the maximum polyphony: the most notes sounding at once. A note counts from its start up to its
     end, so a note that ends on the tick another starts does not overlap it.
   - the hanging notes and orphan offs.
6. Channels in the output are numbered 1 to 16, as musicians number them.

## The outputs

`midi.json`, written with `json.dumps(report, indent=2) + '\n'`:

```json
{
  "input_dir": "fixture",
  "files": [
    {"file": "a.mid", "format": 0, "tracks": 1, "division": 96, "seconds": 2.0,
     "time_signature": "4/4", "tempo_changes": 1, "notes": 4, "drum_hits": 0,
     "lowest": "C4", "highest": "G4",
     "longest": {"name": "C4", "channel": 1, "start": 0.0, "seconds": 1.0},
     "max_polyphony": 3, "hanging": 0, "orphan_offs": 0, "error": null}
  ],
  "totals": {"files": 1, "unreadable": 0, "notes": 4, "drum_hits": 0}
}
```

`files` is in basename order. Every number of seconds is rounded with `round(x, 6)`. A file with no
notes has `null` for `lowest`, `highest` and `longest`. An unreadable file has `error` set to a
short message and only `file` beside it. `input_dir` is the argument as typed.

A summary on stdout: one line per file, then the totals.

Exit codes: 0 when every file was read, 1 when a file is unreadable, 2 when the input directory is
missing or has no `*.mid` file.

The analysis must also be importable: another program calls one function with the bytes of a file
and gets the analysis back.

## What is left to you

The package and module layout, the error wording, the summary layout, logging, and any behaviour
this specification does not fix.

## The fixture

`fixture/` has five files. Its cases: running status across a meta event, a note on with velocity 0
as a note off, a tempo change in the middle of a note, a tempo map in the first track of a format 1
file that sets the time of the other tracks, a 6/8 time signature, a drum track, a retriggered pitch
while the first is still held, an orphan off, a hanging note, a note ending on the tick the next
starts, an unknown chunk, a system exclusive event, SMPTE time and a truncated file.
