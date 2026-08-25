"""Read the quota file, and construct a QuotaPolicy accordingly.

    {
      "team_quotas": {"platform": "500G", "search": "2T", "archive": "100G"},
      "default_quota": "100G",
      "exempt_paths": ["/var/log/audit"]
    }

`team_quotas` and `exempt_paths` may both be absent, and are then empty. The first malformed field
stops the read.
"""

from __future__ import annotations

import json
from pathlib import Path

from quota_reconcile import sizes
from quota_reconcile.common import ByteCount, MalformedSizeError, QuotaConfigError, QuotaPolicy, TeamName
from quota_reconcile.logs import LOG


def readPolicy(quota_json_path: Path) -> QuotaPolicy:
    """Read every field of the quota file, and construct a QuotaPolicy accordingly.

    Raises:
        QuotaConfigError: the file does not hold a JSON object, or a field is absent, of the wrong
            type, or an unusable size.
    """
    text = quota_json_path.read_text(encoding='utf-8')
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _rejectQuotas(quota_json_path, f'unusable JSON: {exc}') from exc

    if not isinstance(document, dict):
        raise _rejectQuotas(quota_json_path, 'the document is not an object')

    raw_quotas = document.get('team_quotas', {})
    default_quota = document.get('default_quota')
    raw_exempt = document.get('exempt_paths', [])
    if not isinstance(raw_quotas, dict):
        raise _rejectQuotas(quota_json_path, 'team_quotas is not an object')
    if not isinstance(default_quota, str):
        raise _rejectQuotas(quota_json_path, 'default_quota is missing, or is not a string')
    if not isinstance(raw_exempt, list):
        raise _rejectQuotas(quota_json_path, 'exempt_paths is not a list')

    policy = QuotaPolicy(
        team_quotas={
            TeamName(str(team)): _readQuotaSize(quota_json_path, str(team), size_text)
            for team, size_text in raw_quotas.items()
        },
        default_quota=_readQuotaSize(quota_json_path, 'default_quota', default_quota),
        exempt_paths=tuple(_readExemptPath(quota_json_path, path_text) for path_text in raw_exempt),
    )
    return policy


def _readQuotaSize(quota_json_path: Path, team: str, size_text: object) -> ByteCount:
    if not isinstance(size_text, str):
        raise _rejectQuotas(quota_json_path, f'the quota of {team} is not a string')

    try:
        return sizes.parseSize(size_text)
    except MalformedSizeError as exc:
        raise _rejectQuotas(quota_json_path, f'the quota of {team} is unusable: {exc}') from exc


def _readExemptPath(quota_json_path: Path, path_text: object) -> Path:
    if not isinstance(path_text, str):
        raise _rejectQuotas(quota_json_path, 'an exempt path is not a string')

    return Path(path_text)


def _rejectQuotas(quota_json_path: Path, reason: str) -> QuotaConfigError:
    LOG.error('quotas.rejected', extra={'source': str(quota_json_path), 'reason': reason})
    return QuotaConfigError(f'{quota_json_path.name}: {reason}')
