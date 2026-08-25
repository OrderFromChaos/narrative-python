"""The logger every reconciler module writes to, and a formatter that keeps its `extra` fields.

    INFO run.recorded added=0 findings=5 funcName=main lineno=59 module=__main__

The standard formatter of logging drops everything in `extra`, so a tally would print as a bare
event name with no number in it. Each record carries the module, the line and the function that
emitted it, because one logger name serves the whole package.
"""

from __future__ import annotations

import logging
import sys


LOG = logging.getLogger('reconciler')

_STANDARD_FIELDS = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION_FIELDS = ('module', 'lineno', 'funcName')


def configureLogging(*, verbose: bool) -> None:
    global LOG

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


### vocabulary #########################################################################


class _FieldFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in _STANDARD_FIELDS}
        located = {key: getattr(record, key) for key in _LOCATION_FIELDS}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'
