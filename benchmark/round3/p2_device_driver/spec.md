# p2 — device driver

## The problem

A driver for a lab instrument reached over a line-oriented socket protocol, written with asyncio.
The instrument it runs against is an in-process `asyncio.start_server` on loopback, so no hardware
is needed.

1. States: `DISCONNECTED`, `CONNECTING`, `READY`, `POLLING`, `FAULTED`. Legal transitions only; an
   illegal transition is a bug and must be loud.
2. `connect()` opens the connection, sends `b'HELLO\n'`, and expects `b'READY\n'` within a timeout.
   On timeout or a wrong banner it retries with exponential backoff (0.5s, 1s, 2s, capped) for at
   most 4 attempts, then goes `FAULTED`.
3. A poll loop on an `asyncio.Task` sends `b'STATUS\n'` every N seconds and parses the reply
   `b'OK <temp_c> <pressure_kpa>\n'` into the latest reading.
4. Two consecutive poll failures tear the connection down and re-run the connect sequence. If the
   reconnect fails, the driver goes `FAULTED` and polling stops.
5. The latest reading and the current state are readable by the caller at any time.
6. `close()` stops the poll task and closes the connection, is safe to call twice, and leaves
   nothing pending.
7. `main()` drives the driver against the fake instrument for a few seconds and prints readings. The
   fake drops the link partway through, so the reconnect path is exercised on every run.

`a_module_state.py`, `b_state_dict.py` and `c_typed_attrs.py` implement this identically: same
protocol, same timings, same retry and reconnect behaviour, same output. They differ only in how the
driver's runtime state is held. Style is now identical across all three, so state-handling is the
only variable left.

## Review instructions

- Rank the three.
- Name three things you would change in your top pick.
- Name one thing you would steal from each of the other two.
- Is an explicit transition table worth it for five states, or is that ceremony?
