"""Load a CSV file into a new SQLite table.

The program reads the header row, then types every column INTEGER, REAL or TEXT from the first
TYPE_SAMPLE_ROWS data rows. An empty field becomes NULL in any column. A row that does not fit those
types is skipped and reported with its line number. The table must not already exist, and a load
that cannot finish drops the table it created, so the same command can run again.

The program exits 1 if it skipped a row or could not start, and 0 otherwise. Each log record is one
JSON object on stderr. Without --verbose, stderr carries the tally and any error. With it, each
skipped row also gets a record of its own.

Usage:
    $ python3 narrative.py readings.csv readings.db measurements
    $ python3 narrative.py readings.csv readings.db measurements --verbose
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sqlite3
import sys
from collections.abc import Iterable, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NewType, TextIO


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
TYPE_SAMPLE_ROWS = 500

LOG = logging.getLogger('csv_to_sqlite')


def main() -> int:
    """Load a CSV file into a new SQLite table and report the rows that did not fit.

    Returns:
        0 when every data row was loaded, 1 when the load could not start or any row was skipped.
    """
    parser = argparse.ArgumentParser(description='Load a CSV file into a SQLite table.')
    parser.add_argument('csv_path', type=Path, help='CSV file to read; its first row is the header')
    parser.add_argument('database', type=Path, help='SQLite file, created if it does not exist')
    parser.add_argument('table', help='table to create and fill; it must not already exist')
    parser.add_argument('--verbose', action='store_true', help='log every skipped row, not just the tally')
    args = parser.parse_args()

    configureLogging(verbose=args.verbose)
    if not validIdentifier(args.table):
        print(f'{args.table!r} is not a usable table name', file=sys.stderr)
        return EXIT_FAILURE

    try:
        schema = readSchema(args.csv_path)
        outcome = loadTable(args.database, TableName(args.table), schema, args.csv_path)
    except LoadError as exc:
        print(f'nothing was loaded: {exc}', file=sys.stderr)
        return EXIT_FAILURE

    reportOutcome(outcome, args.table)
    return EXIT_FAILURE if outcome.rejections else EXIT_SUCCESS


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


def readSchema(csv_path: Path) -> CsvSchema:
    """Read the header, then pick a column type from the first TYPE_SAMPLE_ROWS data rows.

    Only the head of the file is inspected, so a column whose first 500 values are integers and
    whose 501st is 'n/a' becomes an INTEGER column and that one row is skipped at load time. Typing
    from every row instead would mean reading the whole file twice.

    Args:
        csv_path: CSV file whose first row is the header.

    Returns:
        The column names, in file order, and the type inferred for each.

    Raises:
        LoadError: The file cannot be opened, has no header, or names its columns unusably.
    """
    with openCsv(csv_path) as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader, None)
            sample = [row for _, row in zip(range(TYPE_SAMPLE_ROWS), reader, strict=False)]
        except csv.Error as exc:
            raise rejectMalformed(csv_path, reader.line_num) from exc

    if not header:
        raise rejectLoad(f'{csv_path} has no header row')
    if len(set(header)) != len(header):
        raise rejectLoad(f'{csv_path} repeats a column name')

    unusable = [name for name in header if not validIdentifier(name)]
    if unusable:
        raise rejectLoad(f'{csv_path} has unusable column names: {", ".join(repr(name) for name in unusable)}')

    types = tuple(inferColumnType(row[index] for row in sample if index < len(row)) for index in range(len(header)))
    return CsvSchema(tuple(header), types)


def inferColumnType(values: Iterable[str]) -> ColumnType:
    # Empty fields carry no evidence -- they become NULL whatever the column turns out to be -- so a
    # column that is entirely empty in the sample is text, the type that accepts anything later.
    filled = [value for value in values if value]
    if not filled:
        return ColumnType.TEXT
    if all(integerLike(value) for value in filled):
        return ColumnType.INTEGER
    if all(decimalLike(value) for value in filled):
        return ColumnType.REAL
    return ColumnType.TEXT


def loadTable(
    database: Path,
    table: TableName,
    schema: CsvSchema,
    csv_path: Path,
) -> LoadOutcome:
    """Create the table and stream every data row of the CSV into it.

    The inserts are one transaction, committed once at the end, and a load that cannot finish takes
    its own table away with it -- so a failed run leaves the database exactly as it found it and the
    same command can simply be run again.

    Args:
        database: SQLite file, created if it does not exist.
        table: Table to create; refused if it is already there.
        schema: Column names and types, as returned by readSchema().
        csv_path: The same CSV file the schema was read from.

    Returns:
        How many rows were inserted and why each of the others was not.

    Raises:
        LoadError: The database cannot be opened, the table exists, or the CSV became unreadable.
    """
    try:
        connection = sqlite3.connect(database)
    except sqlite3.Error as exc:
        raise rejectLoad(f'cannot open database {database}') from exc

    with closing(connection):
        if tablePresent(connection, table):
            raise rejectLoad(f'table {table!r} already exists in {database}')

        createTable(connection, table, schema)
        try:
            outcome = insertRows(connection, table, schema, csv_path)
        except LoadError:
            # Python 3.11 and earlier commit any open transaction before a DDL statement, so the
            # CREATE above is already durable however this ends. Undoing it by hand is what keeps
            # the next run of the same command from tripping over a table this one left behind.
            connection.rollback()
            connection.execute(f'DROP TABLE "{table}"')
            connection.commit()
            raise

        connection.commit()

    return outcome


def tablePresent(connection: sqlite3.Connection, table: TableName) -> bool:
    EXISTING_SQL = 'SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?'
    return connection.execute(EXISTING_SQL, ('table', table)).fetchone() is not None


def createTable(connection: sqlite3.Connection, table: TableName, schema: CsvSchema) -> None:
    # sqlite3 cannot bind an identifier, so names go into the SQL text quoted. validIdentifier() has
    # already refused everything that would need escaping, which is why this is not an injection.
    columns = ', '.join(f'"{name}" {kind.value}' for name, kind in zip(schema.columns, schema.types, strict=True))
    connection.execute(f'CREATE TABLE "{table}" ({columns})')


def insertRows(
    connection: sqlite3.Connection,
    table: TableName,
    schema: CsvSchema,
    csv_path: Path,
) -> LoadOutcome:
    """Insert every data row that fits the schema and collect a reason for every row that does not.

    Args:
        connection: Open connection; the caller commits.
        table: Table created by createTable(), so its column order matches the schema.
        schema: Column names and types, as returned by readSchema().
        csv_path: CSV file to stream; its header row is skipped here.

    Returns:
        The insert count and one Rejection per skipped row, in file order.

    Raises:
        LoadError: The CSV quoting is malformed, which makes the rest of the file untrustworthy.
    """
    placeholders = ', '.join(['?'] * len(schema.columns))
    INSERT_SQL = f'INSERT INTO "{table}" VALUES ({placeholders})'

    loaded = 0
    rejections: list[Rejection] = []
    with openCsv(csv_path) as handle:
        reader = csv.reader(handle)
        next(reader, None)
        try:
            for row in reader:
                coerced = coerceRow(row, schema)
                if coerced.values is None:
                    rejections.append(Rejection(reader.line_num, coerced.reason))
                    continue

                connection.execute(INSERT_SQL, coerced.values)
                loaded += 1
        except csv.Error as exc:
            # Not a per-row failure: once the parser has lost track of where a field ends, the rows
            # after it are guesses, so degrading here would invent rows rather than skip one.
            raise rejectMalformed(csv_path, reader.line_num) from exc

    logLoadTally(csv_path, loaded, rejections)
    return LoadOutcome(loaded, tuple(rejections))


def coerceRow(row: Sequence[str], schema: CsvSchema) -> CoercedRow:
    """Coerce one row of CSV text to the column types, or say why it does not fit."""
    if len(row) != len(schema.columns):
        return CoercedRow(None, f'expected {len(schema.columns)} fields, found {len(row)}')

    values: list[object] = []
    for name, text, column in zip(schema.columns, row, schema.types, strict=True):
        # An empty field is NULL in every column type: CSV has no other way to spell 'missing', and
        # storing '' in an INTEGER column would make the column read back as text.
        if not text:
            values.append(None)
            continue

        value = coerceValue(text, column)
        if value is None:
            return CoercedRow(None, f'column {name!r}: {text!r} is not {column.value}')
        values.append(value)

    return CoercedRow(tuple(values), '')


def coerceValue(text: str, column: ColumnType) -> int | float | str | None:
    # None means 'does not fit this column'. It is unambiguous because coerceRow() has already dealt
    # with the empty field, which is the only other thing that would map to SQL NULL.
    match column:
        case ColumnType.INTEGER:
            return int(text) if integerLike(text) else None
        case ColumnType.REAL:
            return float(text) if decimalLike(text) else None
        case ColumnType.TEXT:
            return text


def integerLike(text: str) -> bool:
    # int() also accepts '1_0', ' 7 ' and non-ASCII digits. A column holding those is text that
    # happens to look numeric, and retyping it silently would change what round-trips.
    INTEGER_PATTERN = r'[+-]?\d+'
    return text.isascii() and re.fullmatch(INTEGER_PATTERN, text) is not None


def decimalLike(text: str) -> bool:
    # Deliberately narrower than float(), which also accepts 'nan', 'inf' and '1_0': a CSV field
    # spelling 'inf' is far more likely to be a word than an infinity.
    DECIMAL_PATTERN = r'[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?'
    return text.isascii() and re.fullmatch(DECIMAL_PATTERN, text) is not None


def validIdentifier(name: str) -> bool:
    IDENTIFIER_PATTERN = r'[A-Za-z_][A-Za-z0-9_]*'
    return re.fullmatch(IDENTIFIER_PATTERN, name) is not None


def openCsv(csv_path: Path) -> TextIO:
    """Open a CSV file in the mode the csv module needs.

    Args:
        csv_path: File to read. Both passes over the file come through here, so both see one mode.

    Returns:
        The open handle. The caller closes it.

    Raises:
        LoadError: The file is missing, or the operating system refused to open it.
    """
    # newline='' is required by csv: the reader has to see the line endings inside quoted fields.
    # errors='replace' keeps one bad byte from aborting a whole load -- the row it lands in is
    # rejected on its own merits instead, and the other rows still arrive.
    try:
        return csv_path.open(newline='', encoding='utf-8', errors='replace')
    except OSError as exc:
        raise rejectLoad(f'cannot read {csv_path}') from exc


def logLoadTally(csv_path: Path, loaded: int, rejections: Sequence[Rejection]) -> None:
    # The tally is what an operator can act on; an individual bad row only becomes useful once
    # they have decided to go looking, so those stay at DEBUG behind --verbose. A file with 10,000
    # bad rows emits one record at the default level, not 10,000.
    for rejection in rejections:
        LOG.debug('row_skipped', extra={'fields': {'source_line': rejection.line, 'reason': rejection.reason}})

    tally = {'path': str(csv_path), 'loaded': loaded, 'skipped': len(rejections)}
    if rejections:
        LOG.warning('rows_skipped', extra={'fields': tally})
        return

    LOG.info('rows_loaded', extra={'fields': tally})


def reportOutcome(outcome: LoadOutcome, table: str) -> None:
    print(f'loaded {outcome.loaded} rows into {table}, skipped {len(outcome.rejections)}')
    for rejection in outcome.rejections:
        print(f'  line {rejection.line}: {rejection.reason}')


def rejectMalformed(csv_path: Path, line: int) -> LoadError:
    # Both parsing passes hit this, and they must agree on the wording: the schema pass and the load
    # pass read the same file, so a reader who saw one message must recognise the other.
    return rejectLoad(f'{csv_path} is malformed at line {line}')


def rejectLoad(reason: str) -> LoadError:
    # Every raise site routes through here, so the generic fact is recorded exactly once and the
    # handler is free to say what the failure meant to it without repeating the detail.
    LOG.error('load_rejected', extra={'fields': {'reason': reason}})
    return LoadError(reason)


### vocabulary #########################################################################

TableName = NewType('TableName', str)


class ColumnType(Enum):
    """Storage class chosen for a column. The value is the SQL type name, used verbatim in DDL."""

    INTEGER = 'INTEGER'
    REAL = 'REAL'
    TEXT = 'TEXT'


class LoadError(RuntimeError):
    """A load that cannot start or cannot continue, as opposed to a single row that does not fit."""


@dataclass(frozen=True)
class CsvSchema:
    """The header of a CSV file, parsed once, with a type chosen for each column."""

    columns: tuple[str, ...]
    types: tuple[ColumnType, ...]


@dataclass(frozen=True)
class CoercedRow:
    """One source row after coercion: values when it fits the schema, reason when it does not.

    'x,1' against (TEXT, INTEGER) -> CoercedRow(('x', 1), '')
    'x,y' against (TEXT, INTEGER) -> CoercedRow(None, "column 'n': 'y' is not INTEGER")
    """

    values: tuple[object, ...] | None
    reason: str


@dataclass(frozen=True)
class Rejection:
    """A skipped row, identified by the physical line of the file it came from."""

    line: int
    reason: str


@dataclass(frozen=True)
class LoadOutcome:
    loaded: int
    rejections: tuple[Rejection, ...]


class JsonlFormatter(logging.Formatter):
    """Render each record as one JSON object per line, with the message as a stable event name."""

    def format(self, record: logging.LogRecord) -> str:
        # Nested rather than splatted: a field named 'level' or 'event' in the payload must not be
        # able to overwrite the record's own, and LogRecord attributes are a minefield besides.
        fields: Mapping[str, object] = getattr(record, 'fields', {})
        payload = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'event': record.getMessage(),
            'fields': dict(fields),
        }

        return json.dumps(payload, default=str)


if __name__ == '__main__':
    sys.exit(main())
