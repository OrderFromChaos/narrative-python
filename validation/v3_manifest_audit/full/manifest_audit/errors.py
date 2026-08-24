"""Every failure the audit reports, and the one place that records each one.

An exception type belongs to no single module, because any module may catch one. Both format
parsers and the module that dispatches between them raise `ManifestError`, so the type and the
helper that builds it sit here rather than in one of the three.

A `reject*` function logs the fact and returns the exception. The caller raises it, so a guard stays
two lines and the raise site records the fact exactly once:

    raise rejectManifest(path, f'not UTF-8: {exc.reason}') from exc
"""

from __future__ import annotations

from pathlib import Path

from manifest_audit.logs import LOG


def rejectManifest(manifest: Path, reason: str) -> ManifestError:
    # DEBUG, because one bad manifest is an item in a batch that continues. The caller counts them
    # and logs the tally at WARNING, which is the number an operator can act on.
    LOG.debug('manifest.rejected', extra={'manifest': str(manifest), 'reason': reason})
    return ManifestError(f'{manifest}: {reason}')


def rejectPolicy(policy: Path, reason: str) -> PolicyError:
    # ERROR, because the policy is the configuration and not the batch. The program stops.
    LOG.error('policy.rejected', extra={'policy': str(policy), 'reason': reason})
    return PolicyError(f'{policy}: {reason}')


def rejectStore(database: Path, reason: str) -> StoreError:
    LOG.error('store.rejected', extra={'database': str(database), 'reason': reason})
    return StoreError(f'{database}: {reason}')


### vocabulary #########################################################################################


class ManifestError(RuntimeError):
    """A manifest was unreadable, or its content did not fit the format its name declares."""


class PolicyError(RuntimeError):
    """The policy file was unreadable, or it did not describe a policy."""


class StoreError(RuntimeError):
    """The finding database refused a read or a write."""
