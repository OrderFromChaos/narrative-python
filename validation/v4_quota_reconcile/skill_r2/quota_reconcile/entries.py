"""The UsageEntry record that both usage report formats parse into.

    UsageEntry(path=PosixPath('/srv/index/shard-01'), size_bytes=751619276800, team='search', host='node-b')
    UsageEntry(path=PosixPath('/srv/build/artifacts'), size_bytes=1610612736, team=None, host=None)

`team` and `host` are null when the report that gave the entry named neither, which is every entry
of a `*.usage` file. Sizes are plain byte counts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import NewType

from quota_reconcile.sizes import ByteCount


LOG = logging.getLogger(__name__)


def rejectEntry(report_path: Path, locator: str, reason: str) -> MalformedReportError:
    LOG.debug('report.entry.rejected', extra={'report': str(report_path), 'locator': locator, 'reason': reason})
    return MalformedReportError(f'{locator}: {reason}')


### vocabulary #########################################################################

TeamName = NewType('TeamName', str)
HostName = NewType('HostName', str)


@dataclass(frozen=True)
class UsageEntry:
    path: Path
    size_bytes: ByteCount
    team: TeamName | None
    host: HostName | None


class MalformedReportError(RuntimeError):
    """A usage report holds a line or an element that does not read as an entry."""
