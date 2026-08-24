"""Record every overage in a SQLite database.

The primary key of a row is the team, the byte total and the quota. A second run over unchanged
reports therefore computes the same key and adds no row, and a run that finds a changed total adds
one row. `first_seen` holds the time of the run that added the row, and a later run does not move
it.

    run 1, platform uses 612G of 500G  ->  1 row added
    run 2, the reports do not change   ->  0 rows added
    run 3, platform uses 700G of 500G  ->  1 row added
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from quota_reconcile.vocabulary import Reconciliation


LOG = logging.getLogger(__name__)


def openOverageStore(database_path: Path) -> sqlite3.Connection:
    """Open the database, and make the overage table when the database does not hold it yet."""
    SCHEMA_SQL = (
        'CREATE TABLE IF NOT EXISTS overage ('
        'team TEXT NOT NULL, '
        'used_bytes INTEGER NOT NULL, '
        'quota_bytes INTEGER NOT NULL, '
        'overage_bytes INTEGER NOT NULL, '
        'first_seen TEXT NOT NULL, '
        'PRIMARY KEY (team, used_bytes, quota_bytes))'
    )
    connection = sqlite3.connect(database_path)
    connection.execute(SCHEMA_SQL)
    connection.commit()
    return connection


def recordOverages(connection: sqlite3.Connection, result: Reconciliation) -> int:
    """Add one row per overage of this run.

    Returns:
        The count of the rows that this call added, which is 0 for a run over unchanged reports.
    """
    INSERT_SQL = (
        'INSERT OR IGNORE INTO overage '
        '(team, used_bytes, quota_bytes, overage_bytes, first_seen) '
        'VALUES (?, ?, ?, ?, ?)'
    )
    first_seen = datetime.now(UTC).isoformat(timespec='seconds')
    rows: list[OverageRow] = [
        (str(team.team), int(team.used), int(team.quota), int(team.overage), first_seen) for team in result.overages
    ]

    before = connection.total_changes
    connection.executemany(INSERT_SQL, rows)
    connection.commit()
    added = connection.total_changes - before
    LOG.info('overages.recorded', extra={'added': added, 'offered': len(rows)})
    return added


### vocabulary #########################################################################

# The DB-API takes a plain sequence per row, so this shape has no dataclass form: `executemany`
# raises `ProgrammingError: parameters are of unsupported type` for anything else.
OverageRow = tuple[str, int, int, int, str]
