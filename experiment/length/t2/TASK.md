# T2 — retry decorator

A decorator that retries a function on failure with exponential backoff. Configurable: maximum
attempts, base delay, maximum delay, and which exception types count as retryable. It must preserve
the wrapped function's signature for type checkers. On final failure it raises the last exception.
Include a short demonstration in `main()` against a function that fails twice then succeeds.

Single file. Python 3.10+. Standard library only. No test suite.
