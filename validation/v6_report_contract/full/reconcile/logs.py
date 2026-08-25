"""One logger for the reconciler, and the formatter that prints the fields it attaches.

    ERROR rules.rejected funcName=_rejectRules lineno=81 module=rules path=/tmp/nope/reconcile.json reason=no such file

The message is a stable event name and every value rides in `extra`. The standard formatter of
logging discards `extra`, so the record above would print as `ERROR rules.rejected` and the
operator would never see which file or why. Records go to stderr, which leaves stdout to the table.
"""

from __future__ import annotations

import logging
import sys


_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')

LOG = logging.getLogger('reconcile')


def configureLogging(*, verbose: bool) -> None:
    """Attach the field formatter to LOG, at DEBUG when verbose and at WARNING otherwise.

    A per-record rejection is DEBUG and a per-file tally is WARNING, so the default level shows an
    operator the counts and `--verbose` shows every record behind them.
    """
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.WARNING)


### vocabulary #########################################################################


class _FieldFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in _STANDARD}
        located = {key: getattr(record, key) for key in _LOCATION}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'
