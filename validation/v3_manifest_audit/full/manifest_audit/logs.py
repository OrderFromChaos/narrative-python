"""The one logger that every module of the audit writes to.

The logger name is constant, so it carries no information. The formatter prints the module, the line
and the function instead, followed by every field that the call site passed in `extra`. The standard
formatter drops those fields, and the tally counts that an operator acts on are all in them.

A per-item failure goes to DEBUG and the per-manifest tally goes to WARNING. `--verbose` lowers the
level to DEBUG and shows the items.
"""

from __future__ import annotations

import logging
import sys


_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')

LOG = logging.getLogger('manifest_audit')


def configureLogging(*, verbose: bool) -> None:
    """Attach the field formatter to the shared logger and set its level.

    An importing program that never calls this gets the standard library default, which is silence
    below WARNING and a bare message above it. The command-line tool calls it once, in `main`.
    """
    global LOG

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


### vocabulary #########################################################################################


class FieldFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD}
        located = {key: getattr(record, key) for key in _LOCATION}
        fields = ' '.join(f'{k}={v}' for k, v in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'
