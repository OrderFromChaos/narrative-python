"""Drive a lab instrument over a line-oriented socket protocol, with asyncio.

The driver sends HELLO and expects the READY banner. It then sends STATUS every POLL_INTERVAL_S
seconds and parses each OK reply into the latest reading. Two failed polls in a row drop the session
and run the connect sequence again. Four failed connect attempts leave the driver FAULTED. The
caller can read the current state and the latest reading at any point.

This is one of three implementations of the same driver. This one keeps the runtime state in
module-level variables.

Running the module needs no hardware. It starts a fake instrument on loopback, drives the driver
against it for OBSERVATION_COUNT observations, and prints the state and the latest reading each time
on stdout. The fake drops the link partway through, so every run exercises the reconnect path. The
program exits 1 if the driver never connected or ended FAULTED, and 0 otherwise.

Usage:
    $ python3 a_module_state.py
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import re
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import NewType


# Everything a reader would have to open a function to justify now lives inside that function. The
# three wire literals stay out here because the driver and the in-process fake below are two
# participants speaking one protocol, and a copy inside each is a copy that can drift.
BACKOFF_BASE_S = 0.5
BACKOFF_CAP_S = 2.0
POLL_INTERVAL_S = 0.25
REPLY_TIMEOUT_S = 1.0
BACKOFF_FACTOR = 2.0
DROP_AFTER_STATUS = 3
MAX_CONNECT_ATTEMPTS = 4
MAX_POLL_FAILURES = 2
OBSERVATION_COUNT = 12
FAKE_INSTRUMENT_HOST = '127.0.0.1'
HELLO_REQUEST = b'HELLO\n'
READY_BANNER = b'READY\n'
STATUS_REQUEST = b'STATUS\n'

LOG = logging.getLogger('device')


def main() -> int:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    return asyncio.run(runSession())


async def runSession() -> int:
    """Drive the instrument against an in-process fake and print what the driver sees.

    The fake drops the link after DROP_AFTER_STATUS replies, so every run exercises one reconnect,
    and close() is called twice because the second call is the proof that it is idempotent.

    Returns:
        0 if the driver was still polling at the end, 1 if it never connected or ended up FAULTED.
    """
    instrument = await startFakeInstrument()
    port = int(instrument.sockets[0].getsockname()[1])

    try:
        if not await connect(FAKE_INSTRUMENT_HOST, port):
            LOG.error('device_unavailable', extra={'host': FAKE_INSTRUMENT_HOST, 'port': port})
            return 1

        startPolling()

        for _ in range(OBSERVATION_COUNT):
            await asyncio.sleep(POLL_INTERVAL_S)
            state = currentState()
            reading = latestReading()
            LOG.info('device_observed', extra={'device_state': state.value, 'reading': reading})
            print(f'{state.value} {reading}')

        return 1 if currentState() is DeviceState.FAULTED else 0
    finally:
        await close()
        await close()

        instrument.close()
        await instrument.wait_closed()


async def connect(host: str, port: int) -> bool:
    """Open a session, retrying with exponential backoff.

    Args:
        host: instrument host, remembered so the poll loop can reconnect without being told again.
        port: instrument port, remembered for the same reason.

    Returns:
        True once the handshake has succeeded. False after MAX_CONNECT_ATTEMPTS failures, in which
        case the driver is left FAULTED.
    """
    global DEVICE_HOST, DEVICE_PORT
    DEVICE_HOST = host
    DEVICE_PORT = port

    transitionTo(DeviceState.CONNECTING)
    delay_s = BACKOFF_BASE_S

    for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
        try:
            await openSession()
        except LinkError as exc:
            LOG.warning('connect_attempt_failed', extra={'attempt': attempt, 'error': str(exc)})
        except ProtocolError as exc:
            LOG.warning('connect_attempt_rejected', extra={'attempt': attempt, 'error': str(exc)})
        else:
            transitionTo(DeviceState.READY)
            return True

        if attempt == MAX_CONNECT_ATTEMPTS:
            break
        # A requested shutdown abandons the remaining attempts: close() is waiting on this task.
        if await shutdownRequested(delay_s):
            break
        delay_s = min(delay_s * BACKOFF_FACTOR, BACKOFF_CAP_S)

    transitionTo(DeviceState.FAULTED)
    return False


async def openSession() -> None:
    """Open a connection and complete the HELLO/READY handshake.

    Raises:
        LinkError: the connection could not be opened, or the instrument went away mid-handshake.
        ProtocolError: the instrument answered HELLO with something other than the READY banner.
    """
    global READER, WRITER
    reader, writer = await openStreams()

    try:
        await sendRequest(writer, HELLO_REQUEST)
        banner = await readReply(reader)
    except SessionError:
        await closeStream(writer)
        raise

    if banner != READY_BANNER:
        await closeStream(writer)
        LOG.warning('handshake_rejected', extra={'banner': banner.decode(errors='replace').strip()})
        raise ProtocolError('the instrument did not answer HELLO with the READY banner')

    READER = reader
    WRITER = writer


async def openStreams() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Open a connection to the remembered endpoint, with a deadline.

    Returns:
        the reader and the writer of the new connection.

    Raises:
        LinkError: the instrument did not accept a connection within REPLY_TIMEOUT_S, or the
            operating system refused the connection outright.
    """
    # DEVICE_HOST and DEVICE_PORT are read, not written, so no `global` here. asyncio.TimeoutError
    # rather than the builtin: the two are only the same class from 3.11 on, and the floor is 3.10.
    try:
        return await asyncio.wait_for(asyncio.open_connection(DEVICE_HOST, DEVICE_PORT), REPLY_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        LOG.warning('connect_timed_out', extra={'host': DEVICE_HOST, 'port': DEVICE_PORT})
        raise LinkError('the instrument did not accept a connection before the deadline') from exc
    except OSError as exc:
        LOG.warning('connect_refused', extra={'host': DEVICE_HOST, 'port': DEVICE_PORT, 'error': str(exc)})
        raise LinkError('could not open a connection to the instrument') from exc


async def shutdownRequested(timeout_s: float) -> bool:
    # asyncio.Event.wait() carries no timeout of its own, and timing out is the ordinary case here.
    try:
        await asyncio.wait_for(SHUTDOWN.wait(), timeout_s)
    except asyncio.TimeoutError:
        return False

    return True


def transitionTo(new_state: DeviceState) -> None:
    """Move the state machine on, and refuse a move the transition table does not allow.

    Args:
        new_state: where to go. It has to be one of legalTargetsFrom() the state held now.

    Raises:
        IllegalTransitionError: no edge runs from the current state to new_state. That is always a
            bug in the caller, never something the instrument can cause.
    """
    global DEVICE_STATE
    if new_state not in legalTargetsFrom(DEVICE_STATE):
        LOG.error('illegal_transition', extra={'from_state': DEVICE_STATE.value, 'to_state': new_state.value})
        raise IllegalTransitionError(f'{DEVICE_STATE.value} -> {new_state.value} is not a legal transition')

    LOG.info('state_changed', extra={'from_state': DEVICE_STATE.value, 'to_state': new_state.value})
    DEVICE_STATE = new_state


def startPolling() -> None:
    global POLL_TASK
    # create_task needs a running loop, which every caller of this driver is already inside.
    transitionTo(DeviceState.POLLING)
    POLL_TASK = asyncio.create_task(pollLoop(), name='device-poll')


async def pollLoop() -> None:
    """Poll every POLL_INTERVAL_S until shutdown, reconnecting after repeated failures.

    MAX_POLL_FAILURES consecutive failures tear the session down and re-run the connect sequence;
    a failed reconnect leaves the driver FAULTED and ends the loop, because there is nothing left
    to poll. Any single success resets the counter.
    """
    global LATEST_READING
    failures = 0

    while not await shutdownRequested(POLL_INTERVAL_S):
        try:
            reading = await pollOnce()
        except SessionError as exc:
            failures += 1
            LOG.warning('poll_failed', extra={'failures': failures, 'limit': MAX_POLL_FAILURES, 'error': str(exc)})
            if failures < MAX_POLL_FAILURES:
                continue

            await teardownSession()
            if not await connect(DEVICE_HOST, DEVICE_PORT):
                LOG.error('reconnect_failed', extra={'failures': failures})
                return

            transitionTo(DeviceState.POLLING)
        else:
            LATEST_READING = reading

        failures = 0


async def pollOnce() -> Reading:
    """Send one STATUS request and turn the reply into a reading.

    Returns:
        what the instrument reported, stamped with the monotonic time of the parse.

    Raises:
        LinkError: there is no open session, the request could not go out, or no reply arrived
            before the deadline.
        ProtocolError: the instrument answered, but not with a well-formed status line.
    """
    # LBYL: the session is torn down before every reconnect, so no session here means a real bug.
    if READER is None or WRITER is None:
        LOG.error('poll_without_session', extra={'device_state': DEVICE_STATE.value})
        raise LinkError('polled with no open session')

    await sendRequest(WRITER, STATUS_REQUEST)
    return parseStatus(await readReply(READER))


async def teardownSession() -> None:
    global READER, WRITER
    if WRITER is not None:
        await closeStream(WRITER)

    READER = None
    WRITER = None


async def close() -> None:
    """Stop polling, drop the session and return to DISCONNECTED.

    Safe to call twice: the second call finds DISCONNECTED and returns without touching anything.
    """
    global POLL_TASK, SHUTDOWN
    if currentState() is DeviceState.DISCONNECTED:
        return

    SHUTDOWN.set()
    if POLL_TASK is not None:
        # Awaiting the task before touching the streams is what keeps the single-owner rule true.
        await POLL_TASK
        POLL_TASK = None

    await teardownSession()
    transitionTo(DeviceState.DISCONNECTED)


def currentState() -> DeviceState:
    return DEVICE_STATE


def latestReading() -> Reading | None:
    return LATEST_READING


async def startFakeInstrument() -> asyncio.Server:
    EPHEMERAL_PORT = 0
    NEVER_DROP = -1

    # A real server on loopback rather than a fake transport: the driver exercises the same asyncio
    # stream code it would use against hardware, framing and short reads included.
    sessions = itertools.count()

    async def handleSession(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        first_session = next(sessions) == 0
        await serveInstrument(reader, writer, DROP_AFTER_STATUS if first_session else NEVER_DROP)

    return await asyncio.start_server(handleSession, FAKE_INSTRUMENT_HOST, EPHEMERAL_PORT)


async def serveInstrument(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, drop_after: int) -> None:
    """Answer HELLO and STATUS until the client goes away or the link is deliberately dropped.

    Args:
        reader: request side of the accepted connection.
        writer: reply side of the accepted connection.
        drop_after: how many STATUS replies to send before hanging up, or any negative count to
            stay up, since the reply counter starts at zero and only ever climbs.
    """
    BASE_TEMPERATURE_C = 20.0
    FIXED_PRESSURE_KPA = 101.3
    TEMPERATURE_DRIFT_PER_REPLY_C = 0.1

    replies = 0

    try:
        while request := await reader.readline():
            if request == HELLO_REQUEST:
                writer.write(READY_BANNER)
            elif request == STATUS_REQUEST:
                if replies == drop_after:
                    break

                replies += 1
                temperature_c = BASE_TEMPERATURE_C + replies * TEMPERATURE_DRIFT_PER_REPLY_C
                writer.write(f'OK {temperature_c:.1f} {FIXED_PRESSURE_KPA}\n'.encode())

            await writer.drain()
    except OSError as exc:
        # The driver hanging up is how most sessions end here, so it ends the session and no more.
        LOG.warning('instrument_client_lost', extra={'error': str(exc)})
    finally:
        await closeStream(writer)


async def sendRequest(writer: asyncio.StreamWriter, request: bytes) -> None:
    """Send one request and wait until it has left for the instrument.

    Args:
        writer: the open session's writer.
        request: one whole request, its trailing newline included.

    Raises:
        LinkError: the link failed while the request was going out.
    """
    # Every request in this protocol is one line, so a write plus a drain is the whole of sending.
    try:
        writer.write(request)
        await writer.drain()
    except OSError as exc:
        LOG.warning('request_send_failed', extra={'request': request.decode().strip(), 'error': str(exc)})
        raise LinkError('could not send a request to the instrument') from exc


async def readReply(reader: asyncio.StreamReader) -> bytes:
    r"""Read one newline-terminated reply.

    Args:
        reader: the open session's reader.

    Returns:
        One line including its trailing newline, the rest left buffered: b'OK 20.4 101.3\nERR 1\n'
        on the wire returns b'OK 20.4 101.3\n'. A final line the instrument never terminated comes
        back as it stands, b'OK 20.4 101.3', because asyncio's readline() hands over what it has
        when the peer closes; b'' is the empty read that follows, and that one raises.

    Raises:
        LinkError: nothing arrived within REPLY_TIMEOUT_S, or the instrument closed the link.
    """
    try:
        line = await asyncio.wait_for(reader.readline(), REPLY_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        LOG.warning('reply_timed_out', extra={'timeout_s': REPLY_TIMEOUT_S})
        raise LinkError('no reply from the instrument before the deadline') from exc
    except OSError as exc:
        LOG.warning('reply_read_failed', extra={'error': str(exc)})
        raise LinkError('the link failed while a reply was outstanding') from exc

    if not line:
        LOG.warning('link_closed_by_instrument')
        raise LinkError('the instrument closed the connection')

    return line


async def closeStream(writer: asyncio.StreamWriter) -> None:
    # The peer is usually gone already by the time anything closes, and that must not stop teardown.
    writer.close()
    try:
        await writer.wait_closed()
    except OSError as exc:
        LOG.warning('stream_close_failed', extra={'error': str(exc)})


def legalTargetsFrom(state: DeviceState) -> frozenset[DeviceState]:
    # The whole transition table, as a dispatch rather than a dict. There is deliberately no
    # fallback arm: adding a state to the Enum then makes this a `Missing return statement`
    # type error, which a dict of edges would not catch.
    match state:
        case DeviceState.DISCONNECTED:
            return frozenset({DeviceState.CONNECTING})
        case DeviceState.CONNECTING:
            return frozenset({DeviceState.READY, DeviceState.FAULTED, DeviceState.DISCONNECTED})
        case DeviceState.READY:
            return frozenset({DeviceState.POLLING, DeviceState.DISCONNECTED})
        case DeviceState.POLLING:
            return frozenset({DeviceState.CONNECTING, DeviceState.DISCONNECTED})
        case DeviceState.FAULTED:
            return frozenset({DeviceState.DISCONNECTED})


def parseStatus(reply: bytes) -> Reading:
    r"""Parse one status line into a Reading. The single gate where the instrument's bytes are trusted.

    Args:
        reply: a raw reply line, expected to be `OK <temp_c> <pressure_kpa>` plus a newline.

    Returns:
        The parsed reading, stamped with the monotonic time it was parsed. b'OK 20.4 101.3\n' gives
        Reading(temperature_c=20.4, pressure_kpa=101.3, observed_at=<time.monotonic() at the parse>).

    Raises:
        ProtocolError: the line was not three fields, did not start with OK, or carried a
            non-numeric measurement. b'OK 20.4\n' and b'ERR 20.4 101.3\n' both raise, and so does
            b'OK +20.4 101.3\n' -- a leading + is not a sign this parser accepts, though a leading
            - is.
    """
    NUMERIC_FIELD = re.compile(rb'-?\d+(\.\d+)?')
    STATUS_FIELD_COUNT = 3
    STATUS_OK = b'OK'

    fields = reply.split()
    if len(fields) != STATUS_FIELD_COUNT or fields[0] != STATUS_OK:
        LOG.warning('status_reply_malformed', extra={'reply': reply.decode(errors='replace').strip()})
        raise ProtocolError('a status reply must be OK followed by two measurements')

    temperature, pressure = fields[1], fields[2]
    if not NUMERIC_FIELD.fullmatch(temperature) or not NUMERIC_FIELD.fullmatch(pressure):
        LOG.warning('status_reply_not_numeric', extra={'reply': reply.decode(errors='replace').strip()})
        raise ProtocolError('a status reply must carry two numeric measurements')

    return Reading(
        temperature_c=Celsius(float(temperature)),
        pressure_kpa=Kilopascals(float(pressure)),
        observed_at=MonotonicSeconds(time.monotonic()),
    )


### vocabulary #########################################################################################################

Celsius = NewType('Celsius', float)
Kilopascals = NewType('Kilopascals', float)
MonotonicSeconds = NewType('MonotonicSeconds', float)


class DeviceState(Enum):
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    READY = 'ready'
    POLLING = 'polling'
    FAULTED = 'faulted'


class DeviceError(RuntimeError):
    """Anything this driver refuses to do or cannot do."""


class SessionError(DeviceError):
    """A failure of the current session that a reconnect may well fix."""


class LinkError(SessionError):
    """The connection could not be opened, or died while a reply was outstanding."""


class ProtocolError(SessionError):
    """The instrument answered, but not with something this driver understands."""


class IllegalTransitionError(DeviceError):
    """A state change the state machine does not allow. Always a bug in the caller."""


@dataclass(frozen=True)
class Reading:
    temperature_c: Celsius
    pressure_kpa: Kilopascals
    observed_at: MonotonicSeconds


# Runtime state. Every function that CHANGES one of these declares `global`; readers do not, because
# the declaration marks a side effect and not a dependency. asyncio removes the lock the threaded
# version needed: the poll task and its caller are the only two touchers and they never run at once.
# It sits below the vocabulary rather than above main() because DeviceState.DISCONNECTED is a value
# evaluated at import time, and `from __future__ import annotations` defers only the annotations.
DEVICE_HOST: str = ''
DEVICE_PORT: int = 0
DEVICE_STATE: DeviceState = DeviceState.DISCONNECTED
LATEST_READING: Reading | None = None
POLL_TASK: asyncio.Task[None] | None = None
READER: asyncio.StreamReader | None = None
SHUTDOWN: asyncio.Event = asyncio.Event()
WRITER: asyncio.StreamWriter | None = None


if __name__ == '__main__':
    sys.exit(main())
