# T4 — token bucket rate limiter

A token bucket rate limiter. Configurable capacity and refill rate per second. Callers ask to
consume N tokens and are told whether they may proceed, or how long to wait. Refill is computed
from elapsed time rather than a background thread. Support multiple independent buckets keyed by a
caller identifier, with idle buckets expiring after a configurable period. Demonstrate in `main()`:
a burst that exhausts a bucket, the wait, and recovery.

Single file. Python 3.10+. Standard library only. No test suite.
