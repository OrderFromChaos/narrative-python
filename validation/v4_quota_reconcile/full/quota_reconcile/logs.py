"""Write the log records of this package to standard error.

The formatter prints the event name, then every field of `extra` as one `key=value` pair. The
standard formatter of `logging` discards the fields of `extra`, which holds the counts that an
operator acts on.
"""

from __future__ import annotations

import logging
import sys


_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')

LOG = logging.getLogger('quota_reconcile')


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)
    LOG.propagate = False


### vocabulary #########################################################################


class FieldFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in _STANDARD}
        located = {key: getattr(record, key) for key in _LOCATION}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'
