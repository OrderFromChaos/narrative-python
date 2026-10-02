"""Pair each note start with its end within one track.

An end closes the earliest open start of its channel and pitch. A start still open at the track's
end closes there and counts as hanging. Channel 10 is percussion: its starts count as drum hits and
its ends are skipped, so it has no notes, hanging notes or orphan offs.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from midi_report.vocabulary import (
    Channel,
    Note,
    NoteEnd,
    NotePairing,
    NoteStart,
    Pitch,
    TempoChange,
    Tick,
    TimeSignature,
    Track,
)


_DRUM_CHANNEL = Channel(10)


def pairNotes(track: Track) -> NotePairing:
    """Pair the note starts and ends of one track, and count drum hits, hanging notes and orphan offs."""
    open_starts: defaultdict[_NoteKey, deque[Tick]] = defaultdict(deque)
    notes: list[Note] = []
    drum_hits = 0
    orphan_offs = 0
    for event in track.events:
        match event:
            case NoteStart() if event.channel == _DRUM_CHANNEL:
                drum_hits += 1
            case NoteStart():
                open_starts[_NoteKey(event.channel, event.pitch)].append(event.tick)
            case NoteEnd() if event.channel == _DRUM_CHANNEL:
                pass
            case NoteEnd():
                starts = open_starts[_NoteKey(event.channel, event.pitch)]
                if not starts:
                    orphan_offs += 1
                    continue
                notes.append(Note(event.channel, event.pitch, starts.popleft(), event.tick))
            case TempoChange() | TimeSignature():
                pass

    hanging = 0
    for key, starts in open_starts.items():
        hanging += len(starts)
        notes.extend(Note(key.channel, key.pitch, start, track.end_tick) for start in starts)

    return NotePairing(tuple(notes), drum_hits, hanging, orphan_offs)


### vocabulary #########################################################################


@dataclass(frozen=True)
class _NoteKey:
    channel: Channel
    pitch: Pitch
