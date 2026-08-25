"""Record findings in a SQLite file, one row per finding.

    ('billed_not_found', 'i-0004', 'compute-gpu', 250000, None, 'us-east-1', None)
    ('found_not_billed', 'i-0008', 'object-store', None, 'search', None, 'us-west-2')

Rows are keyed on (kind, resource_id), so a re-run over unchanged inputs adds nothing. A finding
already recorded under that key keeps the values it was recorded with, which is what makes the
count of added rows the count of findings new since the last run.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from reconciler.vocabulary import Finding


class FindingStore:
    """One open SQLite connection, holding the findings of every run against one database file."""

    def __init__(self, database_path: Path) -> None:
        self.connection = sqlite3.connect(database_path)
        self._createFindingTable()

    def __enter__(self) -> FindingStore:
        return self

    def __exit__(self, *details: object) -> None:
        self.close()

    def _createFindingTable(self) -> None:
        CREATE_FINDING = (
            'CREATE TABLE IF NOT EXISTS finding ('
            'kind TEXT NOT NULL, '
            'resource_id TEXT NOT NULL, '
            'sku TEXT NOT NULL, '
            'monthly_cents INTEGER, '
            'team TEXT, '
            'billed_region TEXT, '
            'scanned_region TEXT, '
            'PRIMARY KEY (kind, resource_id))'
        )
        self.connection.execute(CREATE_FINDING)
        self.connection.commit()

    def insertFindings(self, findings: Iterable[Finding]) -> int:
        """Record every finding that this database does not already hold under its key.

        Returns:
            The number of rows this call added, which is 0 on a repeat run over unchanged inputs.
        """
        INSERT_FINDING = (
            'INSERT OR IGNORE INTO finding '
            '(kind, resource_id, sku, monthly_cents, team, billed_region, scanned_region) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        rows = [_findingRow(finding) for finding in findings]
        if not rows:
            return 0

        cursor = self.connection.executemany(INSERT_FINDING, rows)
        self.connection.commit()
        return cursor.rowcount

    def close(self) -> None:
        self.connection.close()


def _findingRow(finding: Finding) -> _FindingRow:
    return (
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        finding.monthly_cents,
        finding.team,
        finding.billed_region,
        finding.scanned_region,
    )


### vocabulary #########################################################################

# The DB-API takes one sequence per row, so the row has no dataclass form: passing a dataclass to
# executemany raises ProgrammingError. The alias names the column order instead.
_FindingRow = tuple[str, str, str, int | None, str | None, str | None, str | None]
