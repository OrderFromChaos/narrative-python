"""Read the quota file, and construct a QuotaPolicy accordingly.

    {
      "team_quotas": {"platform": "500G", "search": "2T"},
      "default_quota": "100G",
      "exempt_paths": ["/var/log/audit"]
    }

A team that `team_quotas` does not name gets `default_quota`. A path at or under an exempt path
counts toward no total. `team_quotas` and `exempt_paths` may both be absent; `default_quota` may
not. The first malformed field stops the read.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from quota_reconcile.entries import TeamName
from quota_reconcile.sizes import ByteCount, MalformedSizeError, parseSizeBytes


LOG = logging.getLogger(__name__)


def readQuotaPolicy(quota_json_path: Path) -> QuotaPolicy:
    """Read `quotas.json` into a QuotaPolicy.

    Raises:
        QuotaFileError: the file is not JSON, or a field is absent or of the wrong type, or a
            quota does not read as a size.
    """
    try:
        document = json.loads(quota_json_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise rejectQuotaFile(quota_json_path, 'document', str(exc)) from exc

    if not isinstance(document, dict):
        raise rejectQuotaFile(quota_json_path, 'document', 'expected an object')

    # per-team quotas
    raw_quotas = document.get('team_quotas', {})
    if not isinstance(raw_quotas, dict):
        raise rejectQuotaFile(quota_json_path, 'team_quotas', 'expected an object')
    team_quotas = {
        TeamName(team): readQuotaSize(quota_json_path, f'team_quotas.{team}', raw_size)
        for team, raw_size in raw_quotas.items()
    }

    # exempt paths
    raw_exempt = document.get('exempt_paths', [])
    if not isinstance(raw_exempt, list):
        raise rejectQuotaFile(quota_json_path, 'exempt_paths', 'expected an array')
    for index, raw_exempt_path in enumerate(raw_exempt):
        if not isinstance(raw_exempt_path, str):
            raise rejectQuotaFile(quota_json_path, f'exempt_paths[{index}]', 'expected a string')

    default_quota = readQuotaSize(quota_json_path, 'default_quota', document.get('default_quota'))
    exempt_paths = tuple(Path(text) for text in raw_exempt)
    return QuotaPolicy(team_quotas=team_quotas, default_quota=default_quota, exempt_paths=exempt_paths)


def readQuotaSize(quota_json_path: Path, field_name: str, raw_size: object) -> ByteCount:
    if not isinstance(raw_size, str):
        raise rejectQuotaFile(quota_json_path, field_name, 'expected a size string')

    try:
        return parseSizeBytes(raw_size)
    except MalformedSizeError as exc:
        raise rejectQuotaFile(quota_json_path, field_name, str(exc)) from exc


def rejectQuotaFile(quota_json_path: Path, field_name: str, reason: str) -> QuotaFileError:
    LOG.error(
        'quota.file.rejected',
        extra={'quota_file': str(quota_json_path), 'field': field_name, 'reason': reason},
    )
    return QuotaFileError(f'{quota_json_path}: {field_name}: {reason}')


### vocabulary #########################################################################


@dataclass(frozen=True)
class QuotaPolicy:
    team_quotas: Mapping[TeamName, ByteCount]
    default_quota: ByteCount
    exempt_paths: tuple[Path, ...]

    def resolveQuota(self, team: TeamName) -> ByteCount:
        return self.team_quotas.get(team, self.default_quota)

    def exempt(self, entry_path: Path) -> bool:
        return any(entry_path == root or root in entry_path.parents for root in self.exempt_paths)


class QuotaFileError(RuntimeError):
    """The quota file does not state a policy the program can apply."""
