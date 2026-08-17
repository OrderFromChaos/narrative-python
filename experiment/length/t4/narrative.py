"""Limit how fast each caller may spend, with one token bucket per caller.

A call to consume() answers ALLOWED with the balance left, or THROTTLED with the seconds to wait. A
throttled call spends nothing, so the wait it is quoted stays true for the request it made. A bucket
refills from elapsed time on the next call, not from a background thread. A bucket that no caller
touches for idle_expiry_s is dropped, and that sweep runs only when a new caller arrives.

Running the module shows a burst that empties one bucket, the wait the limiter quotes, the recovery
after that wait, and the idle sweep. The program exits 1 if any step did not behave as described
here, and 0 otherwise. Each log record is one JSON object on stderr.

Usage:
    $ python3 narrative.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import NewType


EXIT_SUCCESS = 0
EXIT_FAILURE = 1

LOG = logging.getLogger('rate_limiter')


def main() -> int:
    """Drive one bucket until it is empty, wait exactly as long as it says, then spend again.

    Returns:
        0 if the limiter behaved as described here, 1 if any step did not -- there are no tests, so
        this doubles as the check that the demonstration still demonstrates something.
    """
    EXPIRY_MARGIN_S = 0.05
    configureLogging()
    config = BucketConfig(capacity_tokens=4.0, refill_per_second=8.0, idle_expiry_s=0.6)
    registry = BucketRegistry(config)
    caller = CallerId('demo')

    burst = [registry.consume(caller, 1.0) for _ in range(5)]
    for number, decision in enumerate(burst, start=1):
        print(f'request {number}: {describe(decision)}')

    exhausted = burst[-1]
    time.sleep(exhausted.retry_after_s)
    recovered = registry.consume(caller, 1.0)
    print(f'after waiting {exhausted.retry_after_s:.3f}s: {describe(recovered)}')

    # Nothing sweeps in the background, so the expiry only happens when a new caller arrives.
    time.sleep(config.idle_expiry_s + EXPIRY_MARGIN_S)
    registry.consume(CallerId('other'), 1.0)
    print(f'{len(registry.buckets)} bucket(s) live after the idle sweep')

    allowed = [decision for decision in burst if decision.verdict is Verdict.ALLOWED]
    if len(allowed) != int(config.capacity_tokens) or recovered.verdict is not Verdict.ALLOWED:
        return EXIT_FAILURE

    return EXIT_SUCCESS if list(registry.buckets) == [CallerId('other')] else EXIT_FAILURE


def configureLogging() -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG)


def describe(decision: Decision) -> str:
    match decision.verdict:
        case Verdict.ALLOWED:
            return f'allowed, {decision.tokens_left:.2f} tokens left'
        case Verdict.THROTTLED:
            return f'throttled, retry in {decision.retry_after_s:.3f}s'


def rejectRequest(reason: str) -> RateLimitError:
    # Every raise site in this module routes through here, so a caller asking for something the
    # limiter can never grant is recorded once, whatever the caller then decides to do about it.
    LOG.error('request_rejected', extra={'fields': {'reason': reason}})
    return RateLimitError(reason)


### vocabulary #########################################################################

CallerId = NewType('CallerId', str)


class Verdict(Enum):
    """What the limiter decided. The value is what appears in a log record or an API response."""

    ALLOWED = 'allowed'
    THROTTLED = 'throttled'


class RateLimitError(RuntimeError):
    """A request or a configuration the limiter cannot honour at any point in the future."""


@dataclass(frozen=True)
class BucketConfig:
    """How every bucket in one registry behaves. Validated once here, trusted everywhere after.

    Attributes:
        capacity_tokens: Bucket size, and therefore the largest burst a caller may make.
        refill_per_second: Tokens added per second of elapsed time, up to the capacity.
        idle_expiry_s: How long a bucket may go untouched before it is dropped.
    """

    capacity_tokens: float
    refill_per_second: float
    idle_expiry_s: float

    def __post_init__(self) -> None:
        """Refuse a configuration that cannot be honoured, at construction.

        Raises:
            RateLimitError: capacity_tokens or refill_per_second is not positive, or idle_expiry_s
                is shorter than the time one bucket needs to refill from empty.
        """
        if self.capacity_tokens <= 0:
            raise rejectRequest(f'capacity_tokens must be positive, got {self.capacity_tokens}')
        if self.refill_per_second <= 0:
            raise rejectRequest(f'refill_per_second must be positive, got {self.refill_per_second}')

        # Dropping a bucket is the same as handing its caller a full one, so an expiry shorter than
        # a refill from empty would let a throttled caller reset itself just by waiting quietly.
        refill_from_empty_s = self.capacity_tokens / self.refill_per_second
        if self.idle_expiry_s < refill_from_empty_s:
            raise rejectRequest(f'idle_expiry_s {self.idle_expiry_s} is below the {refill_from_empty_s}s refill time')


@dataclass(frozen=True)
class Decision:
    """The answer to one consume(): whether to proceed, and if not, how long to wait.

    A throttled decision spends nothing, so retry_after_s is how long until the same request would
    succeed if no one else spends in the meantime.
    """

    verdict: Verdict
    retry_after_s: float
    tokens_left: float


@dataclass
class Bucket:
    """One caller's tokens. Mutable on purpose: this is the thing that changes as time passes."""

    tokens: float
    updated_at: float


@dataclass
class BucketRegistry:
    """Independent buckets keyed by caller, refilled from elapsed time rather than by a thread.

    Attributes:
        config: Capacity, refill rate and expiry, shared by every bucket here.
        clock: Source of monotonic seconds. Injectable so a caller can drive it without sleeping.
        buckets: Live buckets, one per caller seen recently enough not to have been swept.
    """

    config: BucketConfig
    clock: Callable[[], float] = time.monotonic
    buckets: dict[CallerId, Bucket] = field(default_factory=dict)

    def consume(self, caller: CallerId, tokens: float) -> Decision:
        """Try to spend tokens from one caller's bucket.

        Args:
            caller: Identifier the bucket is keyed by; unknown callers start with a full bucket.
            tokens: How many tokens to spend. Nothing is spent unless the whole amount is available.

        Returns:
            ALLOWED with the balance after spending, or THROTTLED with the wait in seconds.

        Raises:
            RateLimitError: The request is not positive, or is larger than the bucket can ever hold.
        """
        if tokens <= 0:
            raise rejectRequest(f'a request must be for a positive number of tokens, got {tokens}')
        if tokens > self.config.capacity_tokens:
            raise rejectRequest(f'{tokens} tokens exceeds the capacity of {self.config.capacity_tokens}')

        now = self.clock()
        bucket = self.bucketFor(caller, now)
        self.refill(bucket, now)
        if bucket.tokens >= tokens:
            bucket.tokens -= tokens
            return Decision(Verdict.ALLOWED, 0.0, bucket.tokens)

        # Partial spending is not offered: a caller told to wait keeps its balance, so the wait it
        # is quoted stays true for the request it actually made.
        retry_after_s = (tokens - bucket.tokens) / self.config.refill_per_second
        LOG.debug('request_throttled', extra={'fields': {'caller': caller, 'retry_after_s': retry_after_s}})
        return Decision(Verdict.THROTTLED, retry_after_s, bucket.tokens)

    def bucketFor(self, caller: CallerId, now: float) -> Bucket:
        existing = self.buckets.get(caller)
        if existing is not None:
            return existing

        # The sweep runs only when the registry is about to grow. On every call it would be a scan
        # of every caller per request; never, and one bucket per caller ever seen would be kept.
        self.expireIdle(now)
        fresh = Bucket(self.config.capacity_tokens, now)
        self.buckets[caller] = fresh
        return fresh

    def refill(self, bucket: Bucket, now: float) -> None:
        # max(..., 0) because the clock is injectable: a caller that hands back a smaller reading
        # than last time must not remove tokens that were already earned.
        elapsed_s = max(now - bucket.updated_at, 0.0)
        bucket.tokens = min(bucket.tokens + elapsed_s * self.config.refill_per_second, self.config.capacity_tokens)
        bucket.updated_at = now

    def expireIdle(self, now: float) -> None:
        stale = [
            caller for caller, bucket in self.buckets.items() if now - bucket.updated_at > self.config.idle_expiry_s
        ]

        for caller in stale:
            del self.buckets[caller]

        if stale:
            LOG.debug('buckets_expired', extra={'fields': {'expired': len(stale), 'live': len(self.buckets)}})


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
