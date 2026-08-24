"""Read the quota file, and answer the quota of a team from it.

The quota file names a quota for some teams, one default quota for every other team, and the paths
that count toward no total. `team_quotas` and `exempt_paths` are optional, and `default_quota` is
not.

    {"team_quotas": {"platform": "500G"}, "default_quota": "100G", "exempt_paths": ["/var/log/audit"]}

A path is exempt when it is an exempt path, or when it sits below one. `/var/log/audit` therefore
makes `/var/log/audit/2024.log` exempt, and leaves `/var/log/auditor` alone.

The quota file tells the program what to do, so one bad field stops the program. The reader raises
on the first bad field instead of skipping it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from quota_reconcile.sizes import parseSizeText
from quota_reconcile.vocabulary import Bytes, QuotaFileError, SizeTextError, TeamName


DEFAULT_QUOTA_FILE_NAME = 'quotas.json'

LOG = logging.getLogger(__name__)


def readQuotaFile(quota_json_path: Path) -> QuotaPolicy:
    """Read the quota file as the policy of one run.

    Raises:
        QuotaFileError: the file is absent, it does not hold JSON, or it holds a bad field.
    """
    if not quota_json_path.is_file():
        raise rejectQuotaFile(quota_json_path, 'the quota file is absent')

    try:
        document = json.loads(quota_json_path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise rejectQuotaFile(quota_json_path, 'the quota file does not open') from exc
    except json.JSONDecodeError as exc:
        raise rejectQuotaFile(quota_json_path, 'the quota file does not hold JSON') from exc

    if not isinstance(document, dict):
        raise rejectQuotaFile(quota_json_path, 'the top level of the quota file is not an object')

    # every field of the file, in the order the example in the module docstring names them
    team_quotas = parseTeamQuotas(quota_json_path, document.get('team_quotas', {}))
    default_quota = parseQuotaSize(quota_json_path, 'default_quota', document.get('default_quota'))
    exempt_paths = parseExemptPaths(quota_json_path, document.get('exempt_paths', []))

    LOG.info(
        'quotas.read',
        extra={'source': str(quota_json_path), 'teams': len(team_quotas), 'exempt': len(exempt_paths)},
    )

    return QuotaPolicy(team_quotas=team_quotas, default_quota=default_quota, exempt_paths=exempt_paths)


def parseTeamQuotas(quota_json_path: Path, raw_quotas: object) -> Mapping[TeamName, Bytes]:
    if not isinstance(raw_quotas, dict):
        raise rejectQuotaFile(quota_json_path, 'the team_quotas field is not an object')

    team_quotas: dict[TeamName, Bytes] = {}
    for raw_team, size_text in raw_quotas.items():
        team = TeamName(str(raw_team))
        team_quotas[team] = parseQuotaSize(quota_json_path, team, size_text)
    return team_quotas


def parseQuotaSize(quota_json_path: Path, field: str, size_text: object) -> Bytes:
    if not isinstance(size_text, str):
        raise rejectQuotaFile(quota_json_path, f'the quota of {field} is absent, or it is not a string')

    try:
        return parseSizeText(size_text)
    except SizeTextError as exc:
        raise rejectQuotaFile(quota_json_path, f'the quota of {field} is not a size') from exc


def parseExemptPaths(quota_json_path: Path, raw_paths: object) -> tuple[Path, ...]:
    if not isinstance(raw_paths, list):
        raise rejectQuotaFile(quota_json_path, 'the exempt_paths field is not a list')

    exempt_paths: list[Path] = []
    for raw_path in raw_paths:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise rejectQuotaFile(quota_json_path, 'an exempt path is empty, or it is not a string')
        exempt_paths.append(Path(raw_path.strip()))
    return tuple(exempt_paths)


def rejectQuotaFile(quota_json_path: Path, reason: str) -> QuotaFileError:
    LOG.error('quotas.rejected', extra={'source': str(quota_json_path), 'reason': reason})
    return QuotaFileError(f'{quota_json_path}: {reason}')


### vocabulary #########################################################################


@dataclass(frozen=True)
class QuotaPolicy:
    """The quotas and the exempt paths of one run.

    Two policies can exist at one time, because a caller can read two quota files and compare them.
    """

    team_quotas: Mapping[TeamName, Bytes]
    default_quota: Bytes
    exempt_paths: tuple[Path, ...]

    def resolveQuota(self, team: TeamName) -> Bytes:
        """Give the quota of a team, which is the default quota for a team the file does not name."""
        return self.team_quotas.get(team, self.default_quota)

    def exempt(self, entry_path: Path) -> bool:
        """Tell whether a path counts toward no total."""
        ancestors = entry_path.parents
        return any(entry_path == exempt_path or exempt_path in ancestors for exempt_path in self.exempt_paths)
