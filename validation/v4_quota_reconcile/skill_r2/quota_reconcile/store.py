"""Record every overage in a SQLite file.

    sqlite> SELECT * FROM overage;
    platform|590558003200|536870912000|53687091200|2026-08-25T01:48:00.512394+00:00

Rows are keyed on team, used_bytes and quota_bytes, so a re-run over unchanged reports adds
nothing. Sizes are plain byte counts, and recorded_at is UTC in ISO 8601 and holds the time of the
run that first saw the overage. A team within its quota gets no row.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from quota_reconcile.reconcile import TeamUsage


LOG = logging.getLogger(__name__)


def recordOverages(database_path: Path, teams: Iterable[TeamUsage]) -> int:
    """Insert one row for each team over quota, and create the table if it is absent.

    Returns:
        The number of rows this call added, which is 0 on a re-run over unchanged reports.
    """
    SCHEMA = (
        'CREATE TABLE IF NOT EXISTS overage ('
        'team TEXT NOT NULL, '
        'used_bytes INTEGER NOT NULL, '
        'quota_bytes INTEGER NOT NULL, '
        'over_bytes INTEGER NOT NULL, '
        'recorded_at TEXT NOT NULL, '
        'PRIMARY KEY (team, used_bytes, quota_bytes))'
    )
    INSERT = 'INSERT OR IGNORE INTO overage VALUES (?, ?, ?, ?, ?)'

    recorded_at = datetime.now(UTC).isoformat()
    rows: list[OverageRow] = [
        (team.team, team.used_bytes, team.quota_bytes, team.over_bytes, recorded_at)
        for team in teams
        if team.overQuota()
    ]

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(SCHEMA)

        before = connection.total_changes
        connection.executemany(INSERT, rows)
        connection.commit()
        added = connection.total_changes - before

    LOG.info('overages.recorded', extra={'database': str(database_path), 'offered': len(rows), 'added': added})
    return added


### vocabulary #########################################################################

# The DB-API takes one sequence per row and rejects a dataclass with
# `ProgrammingError: parameters are of unsupported type`, so the row shape is an alias.
OverageRow = tuple[str, int, int, int, str]
