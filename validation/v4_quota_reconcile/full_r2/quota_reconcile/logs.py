"""The logger that every module of the package writes to, and the formatter that keeps its fields.

    WARNING scan.rejected funcName=readReports lineno=40 module=scan rejected=1 total=4

The standard formatter of logging discards `extra`, so the tally an operator acts on would never
reach the terminal.
"""

from __future__ import annotations

import logging


_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')

LOG = logging.getLogger('quota_reconcile')


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler()
    handler.setFormatter(FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


### vocabulary #########################################################################


class FieldFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in _STANDARD}
        located = {key: getattr(record, key) for key in _LOCATION}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'
