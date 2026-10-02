"""Analyse Standard MIDI Files: their notes, placed in seconds.

>>> from pathlib import Path
>>> from midi_report import analyseMidiFile
>>> analyseMidiFile(Path('fixture/etude.mid').read_bytes()).longest
TimedNote(channel=1, pitch=21, start_seconds=Fraction(1, 2), seconds=Fraction(29, 16))
"""

from midi_report.analysis import analyseMidiFile
from midi_report.vocabulary import FileAnalysis, TimedNote, TimeSignature, UnreadableFileError


__all__ = ['FileAnalysis', 'TimeSignature', 'TimedNote', 'UnreadableFileError', 'analyseMidiFile']
