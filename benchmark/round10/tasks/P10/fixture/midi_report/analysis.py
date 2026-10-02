"""Analyse the bytes of one Standard MIDI File into a FileAnalysis.

    >>> analyseMidiFile(Path('fixture/groove.mid').read_bytes())
    FileAnalysis(format=1, tracks=3, ticks_per_quarter=480, seconds=Fraction(2, 1),
        time_signature=TimeSignature(tick=0, numerator=6, denominator=8), tempo_changes=2, notes=3, drum_hits=4,
        lowest=40, highest=76,
        longest=TimedNote(channel=2, pitch=40, start_seconds=Fraction(0, 1), seconds=Fraction(6, 5)),
        max_polyphony=2, hanging=0, orphan_offs=0)

time_signature is None when the file has no time-signature event. lowest, highest and longest are None when the file
has no notes. The call writes no file and prints nothing.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from fractions import Fraction
from typing import TypeVar

from midi_report import pairing, smf, tempo
from midi_report.vocabulary import FileAnalysis, Note, TempoChange, TempoMap, TimedNote, TimeSignature, Track


def analyseMidiFile(smf_bytes: bytes) -> FileAnalysis:
    """Analyse one file.

    Raises:
        UnreadableFileError: the file does not parse as a Standard MIDI File with ticks per quarter note.
    """
    smf_file = smf.parseSmf(smf_bytes)
    tempo_changes = _collectEvents(smf_file.tracks, TempoChange)
    tempo_map = tempo.buildTempoMap(tempo_changes, smf_file.header.ticks_per_quarter)
    pairings = [pairing.pairNotes(track) for track in smf_file.tracks]
    notes: list[Note] = []
    for track_pairing in pairings:
        notes.extend(track_pairing.notes)
    pitches = [note.pitch for note in notes]
    end_tick = max((track.end_tick for track in smf_file.tracks), default=None)
    # of time signatures on one tick, min() returns the first in track order
    time_signature = min(_collectEvents(smf_file.tracks, TimeSignature), key=lambda each: each.tick, default=None)

    analysis = FileAnalysis(
        format=smf_file.header.format,
        tracks=len(smf_file.tracks),
        ticks_per_quarter=smf_file.header.ticks_per_quarter,
        seconds=Fraction(0) if end_tick is None else tempo.secondsAtTick(tempo_map, end_tick),
        time_signature=time_signature,
        tempo_changes=len(tempo_changes),
        notes=len(notes),
        drum_hits=sum(track_pairing.drum_hits for track_pairing in pairings),
        lowest=min(pitches, default=None),
        highest=max(pitches, default=None),
        longest=_findLongestNote(notes, tempo_map),
        max_polyphony=_measureMaxPolyphony(notes),
        hanging=sum(track_pairing.hanging for track_pairing in pairings),
        orphan_offs=sum(track_pairing.orphan_offs for track_pairing in pairings),
    )
    return analysis


def _collectEvents(tracks: Iterable[Track], event_type: type[_EventT]) -> list[_EventT]:
    """Collect the events of one type, in track order and then file order."""
    events: list[_EventT] = []
    for track in tracks:
        events.extend(event for event in track.events if isinstance(event, event_type))

    return events


def _findLongestNote(notes: Iterable[Note], tempo_map: TempoMap) -> TimedNote | None:
    """Find the note that lasts the most seconds.

    Ties go to the earliest start, then the lowest pitch, then the lowest channel.
    """
    timed_notes: list[TimedNote] = []
    for note in notes:
        start_seconds = tempo.secondsAtTick(tempo_map, note.start_tick)
        seconds = tempo.secondsAtTick(tempo_map, note.end_tick) - start_seconds
        timed_notes.append(TimedNote(note.channel, note.pitch, start_seconds, seconds))

    return min(
        timed_notes,
        key=lambda timed: (-timed.seconds, timed.start_seconds, timed.pitch, timed.channel),
        default=None,
    )


def _measureMaxPolyphony(notes: Sequence[Note]) -> int:
    # an end sorts before a start on the same tick, so a note ending as another starts doesn't overlap it
    START = 1
    END = -1
    edges = sorted([(note.start_tick, START) for note in notes] + [(note.end_tick, END) for note in notes])
    sounding = 0
    max_polyphony = 0
    for _, step in edges:
        sounding += step
        max_polyphony = max(max_polyphony, sounding)

    return max_polyphony


### vocabulary #########################################################################


_EventT = TypeVar('_EventT', TempoChange, TimeSignature)
