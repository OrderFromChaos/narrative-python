"""Keep every finding in SQLite, so that a second audit of an unchanged manifest adds no rows.

Two audits can hold two databases at once, so this is a class and not a module. It owns the
connection, which is a handle, so nothing outside this module imports `sqlite3`.

The manifest, the package, the version and the violation are the key. An unchanged manifest produces
the same four values on every run, and `INSERT OR IGNORE` drops the repeat. The detail text is
outside the key, so a reworded message does not create a second row.

The connection is a handle with a lifetime, so open the store in a `with` block:

    with FindingStore(Path('audit.db')) as store:
        stored = store.storeFindings(findings)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import Self

from manifest_audit.errors import rejectStore
from manifest_audit.vocabulary import Finding


class FindingStore:
    """One open SQLite database of findings."""

    def __init__(self, database: Path) -> None:
        """Open the database and create the table when it is absent.

        Raises:
            StoreError: SQLite could not open the file or create the table.
        """
        SCHEMA = (
            'CREATE TABLE IF NOT EXISTS finding ('
            '  manifest  TEXT NOT NULL,'
            '  package   TEXT NOT NULL,'
            '  version   TEXT NOT NULL,'
            '  violation TEXT NOT NULL,'
            '  detail    TEXT NOT NULL,'
            '  PRIMARY KEY (manifest, package, version, violation)'
            ')'
        )

        self.database = database
        try:
            self.connection = sqlite3.connect(database)
            self.connection.execute(SCHEMA)
            self.connection.commit()
        except sqlite3.Error as exc:
            raise rejectStore(database, f'cannot open: {exc}') from exc

    def storeFindings(self, findings: Iterable[Finding]) -> int:
        """Insert every finding that is not already there.

        Returns:
            The number of rows this call added, which is 0 on a repeat run.

        Raises:
            StoreError: SQLite refused the insert.
        """
        INSERT = (
            'INSERT OR IGNORE INTO finding (manifest, package, version, violation, detail) '
            'VALUES (?, ?, ?, ?, ?)'
        )

        # The DB-API takes a sequence per row and rejects a dataclass, so the record is flattened
        # here and nowhere else.
        rows = [
            (str(found.manifest), found.package, found.version, found.violation.value, found.detail)
            for found in findings
        ]
        try:
            cursor = self.connection.executemany(INSERT, rows)
            self.connection.commit()
        except sqlite3.Error as exc:
            raise rejectStore(self.database, f'cannot write {len(rows)} findings: {exc}') from exc

        return cursor.rowcount

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        failure_type: type[BaseException] | None,
        failure: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
