"""Record the findings of a run in SQLite, keyed so a re-run over unchanged inputs adds no row.

    sqlite> SELECT kind, resource_id, monthly_cents, above_grace, sources FROM finding LIMIT 1;
    billed_not_found|min-flint-5520|41200|1|["core.billing.csv"]

Rows are keyed on (input_dir, kind, resource_id), where input_dir is the resolved absolute path, so
a run from another working directory reconciles the same estate rather than a second one. A finding
that changed between runs replaces its row and the table states the current reconciliation.

Two stores can hold two databases at once, so the connection opens in the constructor and the
caller closes it with `with`.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from reconcile.logs import LOG
from reconcile.vocabulary import Finding


DEFAULT_DATABASE_PATH = Path('reconcile.db')


class FindingStore:
    def __init__(self, database_path: Path) -> None:
        SCHEMA = (
            'CREATE TABLE IF NOT EXISTS finding ('
            '  input_dir TEXT NOT NULL,'
            '  kind TEXT NOT NULL,'
            '  resource_id TEXT NOT NULL,'
            '  sku TEXT NOT NULL,'
            '  monthly_cents INTEGER,'
            '  team TEXT,'
            '  billed_region TEXT,'
            '  scanned_region TEXT,'
            '  above_grace INTEGER NOT NULL,'
            '  sources TEXT NOT NULL,'
            '  last_seen_at TEXT NOT NULL,'
            '  PRIMARY KEY (input_dir, kind, resource_id)'
            ')'
        )
        self._connection = sqlite3.connect(database_path)
        self._connection.execute(SCHEMA)
        self._connection.commit()

    def __enter__(self) -> FindingStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._connection.close()

    def recordFindings(self, input_dir: Path, findings: Iterable[Finding]) -> int:
        """Write every finding of one reconciliation of input_dir.

        Returns:
            The number of rows the table gained, which is 0 on a re-run over unchanged inputs.
        """
        INSERT = (
            'INSERT OR REPLACE INTO finding ('
            '  input_dir, kind, resource_id, sku, monthly_cents, team,'
            '  billed_region, scanned_region, above_grace, sources, last_seen_at'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        )
        estate = str(input_dir.resolve())
        last_seen_at = datetime.now(UTC).isoformat(timespec='seconds')
        rows = [_buildFindingRow(estate, finding, last_seen_at) for finding in findings]

        before = self._countRows()
        self._connection.executemany(INSERT, rows)
        self._connection.commit()

        added = self._countRows() - before
        LOG.info('store.recorded', extra={'input_dir': estate, 'written': len(rows), 'added': added})
        return added

    def _countRows(self) -> int:
        counted = self._connection.execute('SELECT count(*) FROM finding').fetchone()
        return int(counted[0])


def _buildFindingRow(estate: str, finding: Finding, last_seen_at: str) -> _FindingRow:
    return (
        estate,
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        finding.monthly_cents,
        finding.team,
        finding.billed_region,
        finding.scanned_region,
        int(finding.above_grace),
        json.dumps(list(finding.sources), ensure_ascii=False),
        last_seen_at,
    )


### vocabulary #########################################################################

# One row per finding, in the column order of the INSERT. The DB-API takes a sequence per row and
# raises ProgrammingError on a dataclass, so the shape stays a tuple and the alias gives it a name.
_FindingRow = tuple[str, str, str, str, int | None, str | None, str | None, str | None, int, str, str]
