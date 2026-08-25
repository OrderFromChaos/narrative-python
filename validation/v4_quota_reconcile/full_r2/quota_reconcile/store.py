"""Record every overage of a reconciliation run in a SQLite database.

    SELECT * FROM overage
    ('search', 2528876743884, 2199023255552, 329853488332)
    ('platform', 590558003200, 536870912000, 53687091200)

The columns are (team, used_bytes, quota_bytes, overage_bytes), and the first three are the primary
key, so a re-run over unchanged reports adds no row. A team within its quota is not recorded.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from quota_reconcile.common import TeamUsage


class Store:
    """One open SQLite database of recorded overages."""

    def __init__(self, database_path: Path) -> None:
        CREATE_TABLE = (
            'CREATE TABLE IF NOT EXISTS overage ('
            'team TEXT NOT NULL, '
            'used_bytes INTEGER NOT NULL, '
            'quota_bytes INTEGER NOT NULL, '
            'overage_bytes INTEGER NOT NULL, '
            'PRIMARY KEY (team, used_bytes, quota_bytes))'
        )
        self.connection = sqlite3.connect(database_path)
        self.connection.execute(CREATE_TABLE)
        self.connection.commit()

    def recordOverages(self, teams: Iterable[TeamUsage]) -> int:
        """Record the teams that are over quota.

        Returns:
            The number of rows this call added, which is 0 on a re-run over unchanged reports.
        """
        INSERT_OVERAGE = (
            'INSERT OR IGNORE INTO overage (team, used_bytes, quota_bytes, overage_bytes) VALUES (?, ?, ?, ?)'
        )
        rows = [(usage.team, usage.used, usage.quota, usage.overage) for usage in teams if usage.overage]
        cursor = self.connection.executemany(INSERT_OVERAGE, rows)
        self.connection.commit()
        return cursor.rowcount

    def close(self) -> None:
        self.connection.close()
