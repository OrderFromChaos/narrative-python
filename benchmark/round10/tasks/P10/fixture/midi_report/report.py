"""Render file outcomes as the midi.json report and as summary lines.

    {
      "file": "overlap.mid",
      "format": 0,
      "tracks": 1,
      "division": 120,
      "seconds": 3.0,
      "time_signature": "4/4",
      "tempo_changes": 0,
      "notes": 4,
      "drum_hits": 0,
      "lowest": "C4",
      "highest": "G4",
      "longest": {
        "name": "C4",
        "channel": 1,
        "start": 0.0,
        "seconds": 1.0
      },
      "max_polyphony": 2,
      "hanging": 1,
      "orphan_offs": 1,
      "error": null
    },
    {
      "file": "smpte.mid",
      "error": "SMPTE time is not supported"
    }

    etude.mid        2.500000 s  3/4  5 notes A0-C8, 0 drum hits, polyphony 3, 0 hanging, 0 orphan offs
    smpte.mid      unreadable: SMPTE time is not supported
    5 files, 2 unreadable, 12 notes, 4 drum hits

Seconds are rounded to 6 places. Pitch 60 is C4. The time signature is 4/4 when the file has no time-signature event.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from midi_report.vocabulary import AnalysedFile, FileOutcome, Pitch, TimedNote, TimeSignature, UnreadableFile


def buildReport(raw_input_dir: str, outcomes: Sequence[FileOutcome]) -> dict[str, object]:
    totals = _countTotals(outcomes)
    return {
        'input_dir': raw_input_dir,
        'files': [_describeOutcome(outcome) for outcome in outcomes],
        'totals': {
            'files': totals.files,
            'unreadable': totals.unreadable,
            'notes': totals.notes,
            'drum_hits': totals.drum_hits,
        },
    }


def _countTotals(outcomes: Sequence[FileOutcome]) -> _Totals:
    analyses = [outcome.analysis for outcome in outcomes if isinstance(outcome, AnalysedFile)]
    return _Totals(
        files=len(outcomes),
        unreadable=len(outcomes) - len(analyses),
        notes=sum(analysis.notes for analysis in analyses),
        drum_hits=sum(analysis.drum_hits for analysis in analyses),
    )


def _describeOutcome(outcome: FileOutcome) -> dict[str, object]:
    """Describe one file as its entry in midi.json."""
    match outcome:
        case UnreadableFile():
            return {'file': outcome.file_name, 'error': outcome.error}
        case AnalysedFile():
            analysis = outcome.analysis
            return {
                'file': outcome.file_name,
                'format': analysis.format,
                'tracks': analysis.tracks,
                'division': analysis.ticks_per_quarter,
                'seconds': _roundSeconds(analysis.seconds),
                'time_signature': _formatTimeSignature(analysis.time_signature),
                'tempo_changes': analysis.tempo_changes,
                'notes': analysis.notes,
                'drum_hits': analysis.drum_hits,
                'lowest': None if analysis.lowest is None else _nameNote(analysis.lowest),
                'highest': None if analysis.highest is None else _nameNote(analysis.highest),
                'longest': None if analysis.longest is None else _describeLongestNote(analysis.longest),
                'max_polyphony': analysis.max_polyphony,
                'hanging': analysis.hanging,
                'orphan_offs': analysis.orphan_offs,
                'error': None,
            }


def _describeLongestNote(longest: TimedNote) -> dict[str, object]:
    return {
        'name': _nameNote(longest.pitch),
        'channel': longest.channel,
        'start': _roundSeconds(longest.start_seconds),
        'seconds': _roundSeconds(longest.seconds),
    }


def summariseOutcomes(outcomes: Sequence[FileOutcome]) -> list[str]:
    width = max(len(outcome.file_name) for outcome in outcomes)
    lines = [f'{outcome.file_name:<{width}}  {_summariseOutcome(outcome)}' for outcome in outcomes]
    totals = _countTotals(outcomes)
    lines.append(
        f'{totals.files} files, {totals.unreadable} unreadable, {totals.notes} notes, {totals.drum_hits} drum hits',
    )
    return lines


def _summariseOutcome(outcome: FileOutcome) -> str:
    match outcome:
        case UnreadableFile():
            return f'unreadable: {outcome.error}'
        case AnalysedFile():
            analysis = outcome.analysis
            pitch_range = 'no pitches'
            if analysis.lowest is not None and analysis.highest is not None:
                pitch_range = f'{_nameNote(analysis.lowest)}-{_nameNote(analysis.highest)}'
            return (
                f'{_roundSeconds(analysis.seconds):>10.6f} s  {_formatTimeSignature(analysis.time_signature)}  '
                f'{analysis.notes} notes {pitch_range}, {analysis.drum_hits} drum hits, '
                f'polyphony {analysis.max_polyphony}, {analysis.hanging} hanging, {analysis.orphan_offs} orphan offs'
            )


def _formatTimeSignature(time_signature: TimeSignature | None) -> str:
    # a Standard MIDI File without a time signature is in 4/4
    if time_signature is None:
        return '4/4'

    return f'{time_signature.numerator}/{time_signature.denominator}'


def _nameNote(pitch: Pitch) -> str:
    NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    return f'{NAMES[pitch % 12]}{pitch // 12 - 1}'


def _roundSeconds(seconds: Fraction) -> float:
    PLACES = 6
    return round(float(seconds), PLACES)


### vocabulary #########################################################################


@dataclass(frozen=True)
class _Totals:
    files: int
    unreadable: int
    notes: int
    drum_hits: int
