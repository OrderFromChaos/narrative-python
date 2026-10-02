"""Analyse a directory of Standard MIDI Files: their notes, placed in seconds.

Usage:
    $ python3 -m midi_report fixture
    $ python3 -m midi_report fixture --output reports/midi.json --verbose

Writes midi.json and prints one summary line per file, then the totals. Files are read in basename
order. An unreadable file is reported and the other files are still analysed.

Exit codes:
    0  every file was read
    1  at least one file is unreadable
    2  no input directory, or no *.mid file in it

Modules, in reading order:
    smf         bytes of a file to tracks of typed events
    tempo       ticks to seconds through the set-tempo events
    pairing     note starts paired with their ends, per track
    analysis    analyseMidiFile(), the importable entry point
    report      midi.json and the summary lines
    logs        the logger and its formatter
    vocabulary  the types the modules pass between them
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from midi_report import analysis, logs, report
from midi_report.logs import LOG
from midi_report.vocabulary import AnalysedFile, FileOutcome, UnreadableFile, UnreadableFileError


MIDI_GLOB = '*.mid'
DEFAULT_OUTPUT_PATH = Path('midi.json')
EXIT_SUCCESS = 0
EXIT_UNREADABLE = 1
EXIT_NO_INPUT = 2


def main() -> int:
    """Analyse every *.mid file of the input directory, write midi.json and print the summary."""
    parser = argparse.ArgumentParser(description='Analyse a directory of Standard MIDI Files.')
    parser.add_argument('input_dir', help='directory of *.mid files')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT_PATH, help='where to write the JSON report')
    parser.add_argument('--verbose', action='store_true', help='log each rejected file')
    args = parser.parse_args()
    raw_input_dir: str = args.input_dir
    output_path: Path = args.output
    logs.configureLogging(verbose=args.verbose)

    input_dir = Path(raw_input_dir)
    if not input_dir.is_dir():
        print(f'input directory not found: {raw_input_dir}', file=sys.stderr)
        return EXIT_NO_INPUT
    midi_paths = sorted((path for path in input_dir.glob(MIDI_GLOB) if path.is_file()), key=lambda path: path.name)
    if not midi_paths:
        print(f'no {MIDI_GLOB} file in {raw_input_dir}', file=sys.stderr)
        return EXIT_NO_INPUT

    outcomes = [analysePath(midi_path) for midi_path in midi_paths]
    output_path.write_text(json.dumps(report.buildReport(raw_input_dir, outcomes), indent=2) + '\n', encoding='utf-8')
    for line in report.summariseOutcomes(outcomes):
        print(line)

    unreadable = sum(isinstance(outcome, UnreadableFile) for outcome in outcomes)
    if unreadable:
        LOG.warning('midi.unreadable_files', extra={'unreadable': unreadable, 'total': len(outcomes)})
        return EXIT_UNREADABLE

    return EXIT_SUCCESS


def analysePath(midi_path: Path) -> FileOutcome:
    try:
        smf_bytes = midi_path.read_bytes()
    except OSError as exc:
        LOG.debug('midi.read_failed', extra={'file': midi_path.name, 'error': exc.strerror})
        return UnreadableFile(midi_path.name, f'cannot read the file: {exc.strerror}')

    try:
        file_analysis = analysis.analyseMidiFile(smf_bytes)
    except UnreadableFileError as exc:
        LOG.debug('midi.unreadable', extra={'file': midi_path.name, 'error': str(exc)})
        return UnreadableFile(midi_path.name, str(exc))

    return AnalysedFile(midi_path.name, file_analysis)


if __name__ == '__main__':
    sys.exit(main())
