#!/usr/bin/env python3
"""A token bucket rate limiter with one independent bucket per caller.

A bucket holds up to ``capacity`` tokens and regains ``refill_rate`` of them per
second. Consuming N tokens is allowed when at least N are present; otherwise the
caller is told how long to wait before the request would succeed. Refill is
computed lazily from the elapsed time on each call, so no background thread is
involved and an idle limiter costs nothing.

    limiter = RateLimiter(RateLimit(capacity=10, refill_rate=5))
    decision = limiter.consume("user-42", 3)
    if not decision.allowed:
        time.sleep(decision.retry_after)

Buckets that have not been touched for ``idle_ttl`` seconds are discarded, which
bounds memory when the caller identifiers are unbounded (IP addresses, say). A
bucket is only dropped once it has refilled to capacity, so expiry can never
hand out tokens that a live bucket had already spent.

The limiter is safe to share between threads.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

Clock = Callable[[], float]

DEFAULT_IDLE_TTL = 300.0
CLEANUP_INTERVAL = 60.0


@dataclass(frozen=True, slots=True)
class RateLimit:
    """The shape of every bucket the limiter hands out."""

    capacity: float
    refill_rate: float

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be positive")


@dataclass(frozen=True, slots=True)
class Decision:
    """The answer to a single ``consume`` call."""

    allowed: bool
    tokens_remaining: float
    retry_after: float
    """Seconds to wait before retrying; zero when the request was allowed."""

    def __bool__(self) -> bool:
        return self.allowed


@dataclass(slots=True)
class TokenBucket:
    """A single bucket. Not synchronised; the limiter owns the lock."""

    limit: RateLimit
    tokens: float = field(init=False)
    updated_at: float

    def __post_init__(self) -> None:
        self.tokens = self.limit.capacity

    def refill(self, now: float) -> None:
        """Credit the tokens earned since the last call, up to capacity."""
        elapsed = max(0.0, now - self.updated_at)
        self.updated_at = now
        self.tokens = min(self.limit.capacity, self.tokens + elapsed * self.limit.refill_rate)

    def consume(self, tokens: float, now: float) -> Decision:
        """Take ``tokens`` if they are available, otherwise report the wait."""
        self.refill(now)
        if tokens <= self.tokens:
            self.tokens -= tokens
            return Decision(True, self.tokens, 0.0)
        deficit = tokens - self.tokens
        return Decision(False, self.tokens, deficit / self.limit.refill_rate)

    def is_expired(self, now: float, idle_ttl: float) -> bool:
        """True if the bucket is untouched for ``idle_ttl`` and has refilled fully.

        The tokens are projected forward rather than read from the field, which
        is stale between calls because refill is lazy.
        """
        idle = now - self.updated_at
        if idle < idle_ttl:
            return False
        return self.tokens + idle * self.limit.refill_rate >= self.limit.capacity


class RateLimiter:
    """A collection of independent token buckets keyed by caller identifier."""

    def __init__(
        self,
        limit: RateLimit,
        *,
        idle_ttl: float = DEFAULT_IDLE_TTL,
        cleanup_interval: float = CLEANUP_INTERVAL,
        clock: Clock = time.monotonic,
    ) -> None:
        """
        Args:
            limit: Capacity and refill rate applied to every bucket.
            idle_ttl: Seconds of inactivity after which a full bucket is dropped.
            cleanup_interval: Minimum seconds between sweeps for expired buckets.
            clock: Monotonic source of seconds; injectable for tests and demos.
        """
        if idle_ttl <= 0:
            raise ValueError("idle_ttl must be positive")
        self._limit = limit
        self._idle_ttl = idle_ttl
        self._cleanup_interval = cleanup_interval
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[str, TokenBucket] = {}
        self._last_cleanup = clock()

    def consume(self, key: str, tokens: float = 1.0) -> Decision:
        """Ask to spend ``tokens`` from ``key``'s bucket.

        Raises:
            ValueError: If ``tokens`` is not positive, or exceeds the capacity —
                a request that large could never be granted, and returning a
                ``retry_after`` for it would be a lie.
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        if tokens > self._limit.capacity:
            raise ValueError(
                f"cannot consume {tokens} tokens from a bucket of capacity {self._limit.capacity}"
            )
        with self._lock:
            now = self._clock()
            self._maybe_cleanup(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(self._limit, updated_at=now)
                self._buckets[key] = bucket
            return bucket.consume(tokens, now)

    def tokens_available(self, key: str) -> float:
        """Tokens ``key`` could spend right now, without spending any."""
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return self._limit.capacity
            bucket.refill(self._clock())
            return bucket.tokens

    def reset(self, key: str) -> None:
        """Forget a caller, restoring it to a full bucket."""
        with self._lock:
            self._buckets.pop(key, None)

    def __len__(self) -> int:
        """Number of buckets currently held in memory."""
        with self._lock:
            return len(self._buckets)

    def _maybe_cleanup(self, now: float) -> None:
        """Drop expired buckets, at most once per ``cleanup_interval``."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        expired = [
            key
            for key, bucket in self._buckets.items()
            if bucket.is_expired(now, self._idle_ttl)
        ]
        for key in expired:
            del self._buckets[key]


def main() -> None:
    idle_ttl = 1.0
    limiter = RateLimiter(
        RateLimit(capacity=5, refill_rate=10.0),
        idle_ttl=idle_ttl,
        cleanup_interval=0.5,
    )

    print("burst of 7 requests against a bucket of 5 tokens refilling at 10/s:")
    wait = 0.0
    for index in range(1, 8):
        decision = limiter.consume("alice", 1)
        verdict = (
            "allowed" if decision else f"denied, retry in {decision.retry_after:.3f}s"
        )
        print(f"  request {index}: {verdict} ({decision.tokens_remaining:.2f} tokens left)")
        wait = max(wait, decision.retry_after)

    print(f"\nwaiting {wait:.3f}s for the bucket to refill...")
    time.sleep(wait)
    decision = limiter.consume("alice", 1)
    print(f"  after the wait: {'allowed' if decision.allowed else 'denied'}")

    print("\nbuckets are independent:")
    decision = limiter.consume("bob", 5)
    print(
        f"  bob's first request spends all 5 tokens at once: "
        f"{'allowed' if decision.allowed else 'denied'}, "
        f"{decision.tokens_remaining:.2f} left"
    )
    alice_tokens = limiter.tokens_available("alice")
    print(f"  alice's own bucket is untouched by it: {alice_tokens:.2f} tokens")

    print(f"\nidle buckets expire after {idle_ttl}s:")
    print(f"  live buckets before: {len(limiter)}")
    time.sleep(idle_ttl + 0.1)
    limiter.consume("carol", 1)  # any call may trigger the sweep
    print(f"  live buckets after a later call: {len(limiter)}")


if __name__ == "__main__":
    main()
