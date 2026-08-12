#!/usr/bin/env python3
"""Load a CSV file into a SQLite table, choosing a column type from the data.

The CSV must have a header row. Each column is typed by looking at a sample of
the rows: a column whose sampled values all parse as integers becomes INTEGER,
one whose values all parse as floats becomes REAL, anything else becomes TEXT.
Because the sample is bounded, a row beyond the sample can still contradict the
inferred type; such rows are skipped rather than aborting the load, and are
reported at the end with their line number and the reason.

An empty field is stored as NULL in a numeric column and as an empty string in
a text column.
"""

from __future__ import annotations

import argparse
import csv
import math
import sqlite3
import sys
from collections.abc import Iterator, Sequence
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from pathlib import Path

BATCH_SIZE = 1_000
DEFAULT_SAMPLE_ROWS = 1_000


class ColumnType(Enum):
    """A SQLite storage class we are willing to infer."""

    INTEGER = "INTEGER"
    REAL = "REAL"
    TEXT = "TEXT"


def parse_int(raw: str) -> int:
    """Parse a plain decimal integer.

    Stricter than ``int``: underscore separators are rejected so that a value
    such as ``1_000`` is treated as text, which is almost certainly what a CSV
    author meant by it.
    """
    if "_" in raw:
        raise ValueError("underscores are not accepted in numbers")
    return int(raw)


def parse_float(raw: str) -> float:
    """Parse a finite float, rejecting underscores and ``inf``/``nan``."""
    if "_" in raw:
        raise ValueError("underscores are not accepted in numbers")
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("infinities and NaN are not accepted")
    return value


def coerce(value: str, column_type: ColumnType) -> object | None:
    """Convert a raw CSV field to the Python value stored in the column.

    Raises ``ValueError`` if the field does not fit the column's type.
    """
    if column_type is ColumnType.TEXT:
        return value
    if not value.strip():
        return None
    if column_type is ColumnType.INTEGER:
        return parse_int(value)
    return parse_float(value)


class FieldError(Exception):
    """A single field could not be coerced to its column's type."""

    def __init__(self, position: int, value: str, column_type: ColumnType, cause: ValueError):
        super().__init__(f"{value!r} is not a valid {column_type.value.lower()} ({cause})")
        self.position = position


def coerce_row(row: Sequence[str], types: Sequence[ColumnType]) -> tuple[object | None, ...]:
    """Coerce every field of a row, reporting which field failed if one does."""
    coerced: list[object | None] = []
    for position, (value, column_type) in enumerate(zip(row, types)):
        try:
            coerced.append(coerce(value, column_type))
        except ValueError as error:
            raise FieldError(position, value, column_type, error) from error
    return tuple(coerced)


def infer_column_type(values: Sequence[str]) -> ColumnType:
    """Pick the narrowest type that accepts every non-empty sampled value."""
    populated = [value for value in values if value.strip()]
    if not populated:
        return ColumnType.TEXT
    for candidate, parse in ((ColumnType.INTEGER, parse_int), (ColumnType.REAL, parse_float)):
        try:
            for value in populated:
                parse(value)
        except ValueError:
            continue
        return candidate
    return ColumnType.TEXT


@dataclass(frozen=True, slots=True)
class SkippedRow:
    line: int
    reason: str


@dataclass(frozen=True, slots=True)
class LoadReport:
    loaded: int
    skipped: list[SkippedRow]


class CsvLoadError(Exception):
    """The CSV cannot be loaded at all, as opposed to a single bad row."""


def quote_identifier(name: str) -> str:
    """Quote a table or column name for interpolation into SQL."""
    return '"' + name.replace('"', '""') + '"'


def normalise_header(header: Sequence[str]) -> list[str]:
    """Give every column a unique, non-empty name."""
    names: list[str] = []
    seen: dict[str, int] = {}
    for position, raw in enumerate(header, start=1):
        name = raw.strip() or f"column_{position}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        names.append(name if count == 0 else f"{name}_{count + 1}")
    return names


def read_header_and_sample(
    path: Path, encoding: str, sample_rows: int
) -> tuple[list[str], list[ColumnType]]:
    """Read the header row and infer a type per column from the first rows."""
    with path.open(newline="", encoding=encoding) as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise CsvLoadError("the file is empty; a header row is required") from None
        columns = normalise_header(header)
        sample = [row for row in islice(reader, sample_rows) if len(row) == len(columns)]
    by_column = zip(*sample) if sample else ()
    types = [infer_column_type(values) for values in by_column]
    types.extend(ColumnType.TEXT for _ in range(len(columns) - len(types)))
    return columns, types


def iter_coerced_rows(
    path: Path,
    encoding: str,
    columns: Sequence[str],
    types: Sequence[ColumnType],
    skipped: list[SkippedRow],
) -> Iterator[tuple[object | None, ...]]:
    """Yield one tuple per convertible row, recording the rest in ``skipped``."""
    with path.open(newline="", encoding=encoding) as handle:
        reader = csv.reader(handle)
        next(reader, None)  # header, already consumed by the inference pass
        for row in reader:
            if len(row) != len(columns):
                skipped.append(
                    SkippedRow(
                        reader.line_num,
                        f"expected {len(columns)} fields, found {len(row)}",
                    )
                )
                continue
            try:
                yield coerce_row(row, types)
            except FieldError as error:
                skipped.append(
                    SkippedRow(
                        reader.line_num,
                        f"column {columns[error.position]!r}: {error}",
                    )
                )


def create_table(
    connection: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    types: Sequence[ColumnType],
    replace: bool,
) -> None:
    quoted_table = quote_identifier(table)
    if replace:
        connection.execute(f"DROP TABLE IF EXISTS {quoted_table}")
    definitions = ", ".join(
        f"{quote_identifier(name)} {column_type.value}"
        for name, column_type in zip(columns, types)
    )
    try:
        connection.execute(f"CREATE TABLE {quoted_table} ({definitions})")
    except sqlite3.OperationalError as error:
        raise CsvLoadError(f"cannot create table {table!r}: {error}") from error


def load(
    csv_path: Path,
    database_path: Path,
    table: str,
    *,
    encoding: str = "utf-8",
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
    replace: bool = False,
) -> LoadReport:
    """Load ``csv_path`` into ``table`` of the SQLite database at ``database_path``."""
    columns, types = read_header_and_sample(csv_path, encoding, sample_rows)
    skipped: list[SkippedRow] = []
    loaded = 0
    placeholders = ", ".join("?" * len(columns))
    with closing(sqlite3.connect(database_path)) as connection, connection:
        create_table(connection, table, columns, types, replace)
        statement = f"INSERT INTO {quote_identifier(table)} VALUES ({placeholders})"
        rows = iter_coerced_rows(csv_path, encoding, columns, types, skipped)
        while batch := list(islice(rows, BATCH_SIZE)):
            connection.executemany(statement, batch)
            loaded += len(batch)
    return LoadReport(loaded=loaded, skipped=skipped)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv_path", type=Path, help="CSV file to read, including a header row")
    parser.add_argument("database", type=Path, help="SQLite database, created if absent")
    parser.add_argument("table", help="name of the table to create")
    parser.add_argument(
        "--encoding", default="utf-8", help="text encoding of the CSV (default: utf-8)"
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=DEFAULT_SAMPLE_ROWS,
        help=f"rows examined to infer column types (default: {DEFAULT_SAMPLE_ROWS})",
    )
    parser.add_argument(
        "--replace", action="store_true", help="drop the table first if it already exists"
    )
    args = parser.parse_args(argv)
    if args.sample_rows < 1:
        parser.error("--sample-rows must be at least 1")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = load(
            args.csv_path,
            args.database,
            args.table,
            encoding=args.encoding,
            sample_rows=args.sample_rows,
            replace=args.replace,
        )
    except (CsvLoadError, OSError, UnicodeDecodeError, csv.Error, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for row in report.skipped:
        print(f"line {row.line}: {row.reason}", file=sys.stderr)
    print(f"loaded {report.loaded} row(s), skipped {len(report.skipped)}")
    return 1 if report.skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
