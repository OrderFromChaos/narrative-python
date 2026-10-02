"""The logger of midi_report, and a formatter for a person at a terminal.

DEBUG smf.rejected funcName=_rejectFile lineno=51 module=smf reason=SMPTE time is not supported
DEBUG midi.unreadable error=SMPTE time is not supported file=smpte.mid funcName=analysePath lineno=87 module=__main__
WARNING midi.unreadable_files funcName=main lineno=71 module=__main__ total=5 unreadable=2
"""

from __future__ import annotations

import logging


_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')

LOG = logging.getLogger('midi_report')


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler()
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
