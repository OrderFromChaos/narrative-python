"""Record each overage in a SQLite database.

The table holds one row for each combination of a team, a total and a quota. A second run over
unchanged reports gives the same combination, so the store adds no row. Each row therefore states
the first run that found that overage:

    $ sqlite3 quota-overages.db 'SELECT team, over_bytes, first_seen FROM overage'
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import StoreError, TeamUsage


class OverageStore:
    def __init__(self, database_path: Path) -> None:
        CREATE_TABLE_SQL = (
            'CREATE TABLE IF NOT EXISTS overage ('
            'team TEXT NOT NULL, '
            'used_bytes INTEGER NOT NULL, '
            'quota_bytes INTEGER NOT NULL, '
            'over_bytes INTEGER NOT NULL, '
            'first_seen TEXT NOT NULL, '
            'UNIQUE (team, used_bytes, quota_bytes))'
        )
        self.database_path = database_path
        try:
            self.connection = sqlite3.connect(database_path)
            self.connection.execute(CREATE_TABLE_SQL)
            self.connection.commit()
        except sqlite3.Error as exc:
            raise _rejectDatabase(database_path, str(exc)) from exc

    def recordOverages(self, teams: Iterable[TeamUsage]) -> int:
        """Insert one row for each overage that the database does not hold.

        Returns:
            The count of rows that this call added, which is 0 on a second run over unchanged
            reports.

        Raises:
            StoreError: The database did not accept the rows.
        """
        INSERT_SQL = (
            'INSERT OR IGNORE INTO overage (team, used_bytes, quota_bytes, over_bytes, first_seen) '
            'VALUES (?, ?, ?, ?, ?)'
        )
        first_seen = datetime.now(UTC).isoformat(timespec='seconds')
        rows: list[_OverageRow] = [(usage.team, usage.used, usage.quota, usage.over, first_seen) for usage in teams]

        before = self.connection.total_changes
        try:
            self.connection.executemany(INSERT_SQL, rows)
            self.connection.commit()
        except sqlite3.Error as exc:
            raise _rejectDatabase(self.database_path, str(exc)) from exc

        added = self.connection.total_changes - before
        LOG.info('overages.recorded', extra={'database': str(self.database_path), 'added': added, 'held': len(rows)})
        return added

    def close(self) -> None:
        self.connection.close()


def _rejectDatabase(database_path: Path, reason: str) -> StoreError:
    LOG.error('database.rejected', extra={'database': str(database_path), 'reason': reason})
    return StoreError(f'{database_path}: {reason}')


### vocabulary #########################################################################

# The DB-API takes a sequence for each row, so the shape of a row has no dataclass form. The alias
# gives the shape a name that reads at the call site.
_OverageRow = tuple[str, int, int, int, str]
