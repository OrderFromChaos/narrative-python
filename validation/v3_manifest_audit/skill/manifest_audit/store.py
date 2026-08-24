"""Record audit findings in SQLite, one row per manifest, package and rule.

The primary key is (manifest, package, kind). A second run over the same manifest therefore
updates the row it wrote before instead of adding one. The update refreshes the version and the
detail and keeps `first_seen`, so the store shows when a violation appeared and what it looks like
now.

The table has no schema version. Delete the database file to start again.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from manifest_audit.policy import Finding


LOG = logging.getLogger(__name__)


def openStore(database: Path) -> sqlite3.Connection:
    """Open the finding database, and create the table when it is absent."""
    SCHEMA = (
        'CREATE TABLE IF NOT EXISTS finding ('
        'manifest TEXT NOT NULL, '
        'package TEXT NOT NULL, '
        'version TEXT NOT NULL, '
        'kind TEXT NOT NULL, '
        'detail TEXT NOT NULL, '
        'first_seen TEXT NOT NULL, '
        'PRIMARY KEY (manifest, package, kind))'
    )

    connection = sqlite3.connect(database)
    connection.execute(SCHEMA)
    connection.commit()
    return connection


def recordFindings(connection: sqlite3.Connection, findings: Iterable[Finding]) -> int:
    """Write every finding, and refresh each row an earlier run already wrote.

    Returns:
        The number of findings the batch wrote, which is not the number of new rows.
    """
    UPSERT = (
        'INSERT INTO finding (manifest, package, version, kind, detail, first_seen) '
        'VALUES (?, ?, ?, ?, ?, ?) '
        'ON CONFLICT (manifest, package, kind) '
        'DO UPDATE SET version = excluded.version, detail = excluded.detail'
    )
    first_seen = datetime.now(UTC).isoformat(timespec='seconds')

    rows: list[FindingRow] = [
        (str(finding.manifest), finding.package, finding.version, finding.kind.value, finding.detail, first_seen)
        for finding in findings
    ]
    connection.executemany(UPSERT, rows)
    connection.commit()

    LOG.info('store.findings_recorded', extra={'rows': len(rows)})
    return len(rows)


### vocabulary #########################################################################

### `executemany` takes one sequence per row and rejects a dataclass with
### `ProgrammingError: parameters are of unsupported type`, so the row shape gets a name instead.
FindingRow = tuple[str, str, str, str, str, str]
