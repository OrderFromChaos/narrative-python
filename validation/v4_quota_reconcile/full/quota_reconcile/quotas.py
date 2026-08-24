"""Read the quota file, and answer what it states about a team and about a path.

The file holds one JSON object:

    {"team_quotas": {"platform": "500G"}, "default_quota": "100G", "exempt_paths": ["/var/log/audit"]}

A quota is a size with a unit suffix. A team that `team_quotas` does not name gets `default_quota`.
A path below an exempt path is also exempt, thus `/var/log/audit/2026.log` is exempt when the file
names `/var/log/audit`.

The first malformed field stops the read. A quota file that the program reads only in part does not
state what the operator asked the program to do.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from quota_reconcile import byte_size
from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import ByteCount, MalformedSizeError, QuotaFileError, QuotaPolicy, TeamName


QUOTA_FILENAME = 'quotas.json'


def readQuotaPolicy(quota_path: Path) -> QuotaPolicy:
    """Read every quota that the file states.

    Raises:
        QuotaFileError: The file is unreadable, or it holds no JSON object, or one of its fields is
            absent or malformed.
    """
    document = _readQuotaDocument(quota_path)

    # read the fields
    raw_quotas = document.get('team_quotas')
    if not isinstance(raw_quotas, dict):
        raise _rejectQuotaFile(quota_path, 'team_quotas does not hold an object')
    raw_exempt = document.get('exempt_paths')
    if not isinstance(raw_exempt, list):
        raise _rejectQuotaFile(quota_path, 'exempt_paths does not hold a list')

    exempt_paths: list[Path] = []
    for raw_path in raw_exempt:
        if not isinstance(raw_path, str):
            raise _rejectQuotaFile(quota_path, 'an entry of exempt_paths does not hold text')
        exempt_paths.append(Path(raw_path))

    team_quotas = {TeamName(team): _parseQuota(size, team, quota_path) for team, size in raw_quotas.items()}
    policy = QuotaPolicy(
        team_quotas=team_quotas,
        default_quota=_parseQuota(document.get('default_quota'), 'default_quota', quota_path),
        exempt_paths=tuple(exempt_paths),
    )
    return policy


def resolveQuota(team: TeamName, policy: QuotaPolicy) -> ByteCount:
    return policy.team_quotas.get(team, policy.default_quota)


def exemptFromQuota(path: Path, policy: QuotaPolicy) -> bool:
    return any(path.is_relative_to(exempt) for exempt in policy.exempt_paths)


def _readQuotaDocument(quota_path: Path) -> Mapping[str, object]:
    try:
        quota_text = quota_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        raise _rejectQuotaFile(quota_path, str(exc)) from exc
    try:
        document = json.loads(quota_text)
    except json.JSONDecodeError as exc:
        raise _rejectQuotaFile(quota_path, str(exc)) from exc

    if not isinstance(document, dict):
        raise _rejectQuotaFile(quota_path, 'the file holds no JSON object')
    return document


def _parseQuota(size: object, field_name: str, quota_path: Path) -> ByteCount:
    if not isinstance(size, str):
        raise _rejectQuotaFile(quota_path, f'{field_name} does not hold text')

    try:
        return byte_size.parseByteSize(size)
    except MalformedSizeError as exc:
        raise _rejectQuotaFile(quota_path, f'{field_name} does not hold a size') from exc


def _rejectQuotaFile(quota_path: Path, reason: str) -> QuotaFileError:
    LOG.error('quota_file.rejected', extra={'quota_file': str(quota_path), 'reason': reason})
    return QuotaFileError(f'{quota_path}: {reason}')
