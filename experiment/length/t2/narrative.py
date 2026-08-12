from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import ParamSpec, TypeVar


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
BACKOFF_MULTIPLIER = 2.0

LOG = logging.getLogger('retry')
ATTEMPTS_MADE: dict[str, int] = {}

P = ParamSpec('P')
T = TypeVar('T')


def main() -> int:
    """Demonstrate the decorator against a call that fails twice, then one that never succeeds.

    Returns:
        0 if both demonstrations behaved as described, 1 if either did not.
    """
    configureLogging()
    policy = RetryPolicy(
        max_attempts=4,
        base_delay_s=0.05,
        max_delay_s=0.4,
        retryable=(ConnectionError,),
    )

    # The decorator is applied here rather than at module level, so that reading the file top-down
    # never lands on a call to something defined further down. `fetch` keeps the signature of
    # unstableFetch: mypy rejects fetch('report.json', fail_times='2') at this call site.
    fetch = retrying(policy)(unstableFetch)
    recovered = fetch('report.json', fail_times=2)
    print(f'{recovered} after {ATTEMPTS_MADE["report.json"]} attempts')

    try:
        fetch('outage.json', fail_times=99)
    except ConnectionError as exc:
        print(f'gave up after {ATTEMPTS_MADE["outage.json"]} attempts: {exc}')

    if ATTEMPTS_MADE['report.json'] != 3:
        return EXIT_FAILURE
    return EXIT_SUCCESS if ATTEMPTS_MADE['outage.json'] == policy.max_attempts else EXIT_FAILURE


def configureLogging() -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG)


def retrying(policy: RetryPolicy) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Build a decorator that retries its function under the given policy.

    The wrapper is typed with a ParamSpec, so the decorated function keeps its own signature for the
    type checker rather than degrading to (*args: Any, **kwargs: Any) -> Any.

    Args:
        policy: How many attempts to make, how long to wait between them, and what to retry.

    Returns:
        A decorator. Applying it does not change what the function returns or raises: the exception
        from the final attempt propagates with its own traceback, not wrapped in anything.
    """

    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def attempt(*args: P.args, **kwargs: P.kwargs) -> T:
            # The last attempt is deliberately outside the loop. It has nothing to wait for and
            # nothing to fall back to, which is also why there is no unreachable line after it.
            for number in range(1, policy.max_attempts):
                try:
                    return function(*args, **kwargs)
                except policy.retryable as exc:
                    delay = backoffDelay(policy, number)
                    reportAttempt(function.__name__, number, delay, exc)
                    time.sleep(delay)

            try:
                return function(*args, **kwargs)
            except policy.retryable as exc:
                fields = {'call': function.__name__, 'attempts': policy.max_attempts, 'error': str(exc)}
                LOG.warning('retry_exhausted', extra={'fields': fields})
                raise

        return attempt

    return decorate


def backoffDelay(policy: RetryPolicy, number: int) -> float:
    # Attempt 1 waits base_delay_s, attempt 2 twice that, and so on until max_delay_s caps it. No
    # jitter: this is a single-caller retry, not a herd of clients rediscovering a server together.
    return min(policy.base_delay_s * BACKOFF_MULTIPLIER ** (number - 1), policy.max_delay_s)


def reportAttempt(
    call: str,
    number: int,
    delay: float,
    exc: Exception,
) -> None:
    # An operator cannot act on one failed attempt that a later one repaired, so this is DEBUG. The
    # record that is actionable is retry_exhausted, which is where the call finally gave up.
    fields = {'call': call, 'attempt': number, 'delay_s': round(delay, 3), 'error': str(exc)}
    LOG.debug('retry_scheduled', extra={'fields': fields})


def unstableFetch(name: str, fail_times: int) -> str:
    """Stand-in for a flaky call: raise ConnectionError until it has been called fail_times times."""
    global ATTEMPTS_MADE
    ATTEMPTS_MADE[name] = ATTEMPTS_MADE.get(name, 0) + 1
    if ATTEMPTS_MADE[name] <= fail_times:
        raise ConnectionError(f'{name} is unreachable')

    return f'fetched {name}'


def rejectPolicy(reason: str) -> RetryConfigError:
    # One raise site's worth of logging for all four guards, so a rejected policy is recorded once
    # and the caller is free to add what it meant without repeating the detail.
    LOG.error('policy_rejected', extra={'fields': {'reason': reason}})
    return RetryConfigError(reason)


### vocabulary #########################################################################


class RetryConfigError(RuntimeError):
    """A retry policy that cannot be honoured, caught at construction rather than mid-backoff."""


@dataclass(frozen=True)
class RetryPolicy:
    """How a call is retried. Validated once, on construction, and trusted everywhere after that.

    Attributes:
        max_attempts: Total calls including the first, so 1 means no retry at all.
        base_delay_s: Wait after the first failure, in seconds.
        max_delay_s: Ceiling the doubling stops at, in seconds.
        retryable: Exception types worth a second call. Anything else propagates immediately.
    """

    max_attempts: int
    base_delay_s: float
    max_delay_s: float
    retryable: tuple[type[Exception], ...]

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise rejectPolicy(f'max_attempts must be at least 1, got {self.max_attempts}')
        if self.base_delay_s <= 0:
            raise rejectPolicy(f'base_delay_s must be positive, got {self.base_delay_s}')
        if self.max_delay_s < self.base_delay_s:
            raise rejectPolicy(f'max_delay_s {self.max_delay_s} is below base_delay_s {self.base_delay_s}')
        if not self.retryable:
            raise rejectPolicy('retryable is empty, which would retry nothing')


class JsonlFormatter(logging.Formatter):
    """Render each record as one JSON object per line, with the message as a stable event name."""

    def format(self, record: logging.LogRecord) -> str:
        # Nested rather than splatted: a field named 'level' or 'event' in the payload must not be
        # able to overwrite the record's own, and LogRecord attributes are a minefield besides.
        fields: Mapping[str, object] = getattr(record, 'fields', {})
        payload = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'event': record.getMessage(),
            'fields': dict(fields),
        }

        return json.dumps(payload, default=str)


if __name__ == '__main__':
    sys.exit(main())
