"""Types shared between the modules of midi_report.

Ticks count from the start of their track. Channels are numbered 1 to 16. Seconds are exact
fractions.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import NewType


Tick = NewType('Tick', int)
Channel = NewType('Channel', int)
Pitch = NewType('Pitch', int)


class UnreadableFileError(RuntimeError):
    pass


@dataclass(frozen=True)
class SmfHeader:
    format: int
    ticks_per_quarter: int


@dataclass(frozen=True)
class NoteStart:
    tick: Tick
    channel: Channel
    pitch: Pitch


@dataclass(frozen=True)
class NoteEnd:
    tick: Tick
    channel: Channel
    pitch: Pitch


@dataclass(frozen=True)
class TempoChange:
    tick: Tick
    microseconds_per_quarter: int


@dataclass(frozen=True)
class TimeSignature:
    tick: Tick
    numerator: int
    denominator: int


TrackEvent = NoteStart | NoteEnd | TempoChange | TimeSignature


@dataclass(frozen=True)
class Track:
    events: tuple[TrackEvent, ...]
    end_tick: Tick  # the end-of-track event, or the last event when the chunk ends without one


@dataclass(frozen=True)
class SmfFile:
    header: SmfHeader
    tracks: tuple[Track, ...]


@dataclass(frozen=True)
class TempoSegment:
    start_tick: Tick
    elapsed_tick_microseconds: int  # sum of ticks times microseconds per quarter before start_tick
    microseconds_per_quarter: int


@dataclass(frozen=True)
class TempoMap:
    ticks_per_quarter: int
    segments: tuple[TempoSegment, ...]


@dataclass(frozen=True)
class Note:
    channel: Channel
    pitch: Pitch
    start_tick: Tick
    end_tick: Tick


@dataclass(frozen=True)
class NotePairing:
    notes: tuple[Note, ...]
    drum_hits: int
    hanging: int
    orphan_offs: int


@dataclass(frozen=True)
class TimedNote:
    channel: Channel
    pitch: Pitch
    start_seconds: Fraction
    seconds: Fraction


@dataclass(frozen=True)
class FileAnalysis:
    format: int
    tracks: int
    ticks_per_quarter: int
    seconds: Fraction
    time_signature: TimeSignature | None
    tempo_changes: int
    notes: int
    drum_hits: int
    lowest: Pitch | None
    highest: Pitch | None
    longest: TimedNote | None
    max_polyphony: int
    hanging: int
    orphan_offs: int


@dataclass(frozen=True)
class AnalysedFile:
    file_name: str
    analysis: FileAnalysis


@dataclass(frozen=True)
class UnreadableFile:
    file_name: str
    error: str


FileOutcome = AnalysedFile | UnreadableFile
