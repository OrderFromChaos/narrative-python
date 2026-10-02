"""Place a tick in seconds through the set-tempo events of every track of a file.

The tempo is 500,000 microseconds per quarter note before the first set-tempo event. Of two
set-tempo events on one tick, the later in the order given applies.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from fractions import Fraction

from midi_report.vocabulary import TempoChange, TempoMap, TempoSegment, Tick


def buildTempoMap(tempo_changes: Iterable[TempoChange], ticks_per_quarter: int) -> TempoMap:
    DEFAULT_MICROSECONDS_PER_QUARTER = 500_000
    segments = [TempoSegment(Tick(0), 0, DEFAULT_MICROSECONDS_PER_QUARTER)]
    for change in sorted(tempo_changes, key=lambda each: each.tick):
        previous = segments[-1]
        if change.tick == previous.start_tick:
            segments[-1] = TempoSegment(
                previous.start_tick,
                previous.elapsed_tick_microseconds,
                change.microseconds_per_quarter,
            )
            continue
        elapsed = (
            previous.elapsed_tick_microseconds + (change.tick - previous.start_tick) * previous.microseconds_per_quarter
        )
        segments.append(TempoSegment(change.tick, elapsed, change.microseconds_per_quarter))

    return TempoMap(ticks_per_quarter, tuple(segments))


def secondsAtTick(tempo_map: TempoMap, tick: Tick) -> Fraction:
    MICROSECONDS_PER_SECOND = 1_000_000
    segment = tempo_map.segments[bisect_right(tempo_map.segments, tick, key=lambda each: each.start_tick) - 1]
    tick_microseconds = (
        segment.elapsed_tick_microseconds + (tick - segment.start_tick) * segment.microseconds_per_quarter
    )
    return Fraction(tick_microseconds, tempo_map.ticks_per_quarter * MICROSECONDS_PER_SECOND)
