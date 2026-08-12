#!/usr/bin/env python3
"""A ``retry`` decorator with exponential backoff.

    @retry(attempts=5, base_delay=0.1, retry_on=ConnectionError)
    def fetch(url: str) -> bytes:
        ...

The wrapped function keeps its signature as far as a type checker is concerned,
so ``fetch("x", 1)`` is still an error. Delays grow geometrically from
``base_delay`` and are capped at ``max_delay``; by default each delay is jittered
over the interval ``[0, delay]`` so that concurrent callers do not retry in
lockstep. When the attempts are exhausted the last exception is re-raised.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from collections.abc import Callable, Iterator
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 0.1
DEFAULT_MAX_DELAY = 10.0
DEFAULT_MULTIPLIER = 2.0


def backoff_delays(
    attempts: int,
    base_delay: float,
    max_delay: float,
    multiplier: float = DEFAULT_MULTIPLIER,
    jitter: bool = True,
    rng: random.Random | None = None,
) -> Iterator[float]:
    """Yield the ``attempts - 1`` delays that separate ``attempts`` tries."""
    random_ = rng or random
    delay = base_delay
    for _ in range(attempts - 1):
        capped = min(delay, max_delay)
        yield random_.uniform(0.0, capped) if jitter else capped
        delay *= multiplier


def retry(
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    multiplier: float = DEFAULT_MULTIPLIER,
    retry_on: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Build a decorator that retries a call on the given exception types.

    Args:
        attempts: Total number of calls, including the first one. Must be >= 1.
        base_delay: Seconds to wait before the second attempt.
        max_delay: Upper bound on any single delay, applied before jitter.
        multiplier: Factor by which the delay grows after each failure.
        retry_on: Exception type, or tuple of types, that counts as retryable.
            Anything else propagates immediately.
        jitter: Spread each delay uniformly over ``[0, delay]``.
        sleep: Injection point for the sleeping function.
        rng: Injection point for the source of jitter.

    Raises:
        ValueError: If the numeric parameters do not describe a usable schedule.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("delays must not be negative")
    if multiplier < 1:
        raise ValueError("multiplier must be at least 1")

    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            delays = backoff_delays(attempts, base_delay, max_delay, multiplier, jitter, rng)
            for attempt in range(1, attempts + 1):
                try:
                    return function(*args, **kwargs)
                except retry_on as error:
                    if attempt == attempts:
                        logger.warning(
                            "%s failed after %d attempt(s), giving up",
                            function.__qualname__,
                            attempt,
                        )
                        raise
                    delay = next(delays)
                    logger.info(
                        "%s failed on attempt %d/%d (%s); retrying in %.3fs",
                        function.__qualname__,
                        attempt,
                        attempts,
                        error,
                        delay,
                    )
                    sleep(delay)
            raise AssertionError("unreachable: the loop either returns or raises")

        return wrapper

    return decorate


class TransientError(RuntimeError):
    """Stands in for whatever your flaky dependency raises."""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    remaining_failures = 2

    @retry(attempts=4, base_delay=0.05, max_delay=1.0, retry_on=TransientError)
    def flaky(label: str) -> str:
        nonlocal remaining_failures
        if remaining_failures > 0:
            remaining_failures -= 1
            raise TransientError(f"{label}: dependency unavailable")
        return f"{label}: ok"

    print(flaky("first call"))

    @retry(attempts=3, base_delay=0.01, retry_on=TransientError)
    def always_fails() -> None:
        raise TransientError("still unavailable")

    try:
        always_fails()
    except TransientError as error:
        print(f"second call raised the last exception as expected: {error}")

    @retry(attempts=3, base_delay=0.01, retry_on=TransientError)
    def wrong_error() -> None:
        raise ValueError("not retryable")

    try:
        wrong_error()
    except ValueError as error:
        print(f"third call propagated a non-retryable error immediately: {error}")


if __name__ == "__main__":
    main()
