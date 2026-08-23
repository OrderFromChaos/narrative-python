# Round 7 — architecture forced choices

**Answer as if you had infinite time and effort.** Not "what would I type under deadline" — what is
the *best possible* version. These two answers are known to differ; only the second is being
measured.

Every pair is behaviourally identical. Only one dimension varies per question — if you find yourself
weighing two things at once, say so, that is a bug in the question.

This round is about **arrangement between files**, not about what a line looks like. House style is
held constant across every option so it is not a confound. Imports, `from __future__ import
annotations` and module docstrings are elided except where the question is about them. Multi-file
options use `# --- collector/store.py ---` separators. Where a file is an outline, `...` stands for a
body and a trailing comment gives its real size.

"Depends" is a real answer. Give the condition in one line and it gets recorded as a conditional
rule rather than a flat one.

**Answer block M first.** Its two questions set the exchange rate the other five blocks trade in.
**Answer one block per sitting.** Six blocks sit at six altitudes, and answering all of them at once drifts
the later answers toward consistency with the earlier ones.

Do not read `key.md` until you have answered. It names what each question probes.

## The repository

```
scanlib/       importable library: the scan wire format, its types, its errors
collector/     long-running service: polls instruments over TCP, writes readings to SQLite
drift_check/   batch program: reads the database, reports calibration drift
tools/         fixture generators
```

Three programs, one shared library, one repository. Nothing here is a one-shot CLI — that shape is
already covered, and it is the shape that hides every question below.

---

# Block M — the measure

Two questions, no code. They decide how every later question is scored.

## R7-M01

Two designs of the collector service. Both work, both pass the whole toolchain, neither has a bug.

```
# A
# Support a new instrument model — touches ONE file:
#     collector/models/acme_x200.py            new, 60 lines
#
# Follow one reading from socket to database — touches FOUR:
#     collector/service.py
#       -> collector/poller.py
#         -> collector/models/acme_x200.py
#           -> collector/store.py

# B
# Support a new instrument model — touches FOUR files:
#     collector/protocol.py      a new branch in the frame parser
#     collector/vocabulary.py    a new Enum member
#     collector/poller.py        a new match arm
#     collector/store.py         one new column
#
# Follow one reading from socket to database — touches ONE:
#     collector/poller.py
```

Which is the better design? If the answer is "depends", name the condition that decides it.

## R7-M02

Three ways of paying for the same clarity. **Order them most expensive to least**, where the cost is
what it takes from a reader who is trying to understand the program.

```python
# A — one more file
# scanlib/checksum.py, 22 lines, one function, imported by scanlib/frame.py and by drift_check

# B — one more parameter, threaded through three functions, two of which never use it
def runRound(connection: sqlite3.Connection, devices: DeviceTable, clock: Clock) -> RoundReport: ...
def pollAll(devices: DeviceTable, clock: Clock) -> list[Reading]: ...
def readOne(device: Device, clock: Clock) -> Reading:
    return Reading(device.device_id, celsius=parseCelsius(device.read()), observed_at=clock())


# C — one more named type
@dataclass(frozen=True, slots=True)
class Reading:
    device_id: DeviceId
    celsius: float
    observed_at: MonotonicSeconds


# it replaces tuple[str, float, float] in six signatures
```

---

# Block A — which module imports which

## R7-A01

```python
# A
# --- collector/store.py ---
from collector.config import DEVICE_CONFIG


def insertReading(connection: sqlite3.Connection, reading: Reading) -> None:
    device = DEVICE_CONFIG[reading.device_id]
    connection.execute(
        'INSERT INTO readings VALUES (?, ?, ?, ?)',
        (reading.device_id, device.site_code, reading.celsius, reading.observed_at),
    )


# --- collector/poller.py ---
from collector.store import insertReading


def recordOne(connection: sqlite3.Connection, reading: Reading) -> None:
    insertReading(connection, reading)


# B
# --- collector/store.py ---
def insertReading(connection: sqlite3.Connection, reading: Reading, device: DeviceEntry) -> None:
    connection.execute(
        'INSERT INTO readings VALUES (?, ?, ?, ?)',
        (reading.device_id, device.site_code, reading.celsius, reading.observed_at),
    )


# --- collector/poller.py ---
from collector.config import DEVICE_CONFIG
from collector.store import insertReading


def recordOne(connection: sqlite3.Connection, reading: Reading) -> None:
    insertReading(connection, reading, DEVICE_CONFIG[reading.device_id])
```

## R7-A02

`collector/store.py` needs `PollOutcome`. `collector/poller.py` defines it and calls `store`. That is
a cycle.

```python
# A
# --- collector/store.py ---
if TYPE_CHECKING:
    from collector.poller import PollOutcome


def recordOutcome(connection: sqlite3.Connection, outcome: PollOutcome) -> None: ...


# --- collector/poller.py ---
from collector.store import recordOutcome


@dataclass(frozen=True, slots=True)
class PollOutcome:
    device_id: DeviceId
    reading: Reading | None
    refusal: str | None


# B
# --- collector/vocabulary.py ---
@dataclass(frozen=True, slots=True)
class PollOutcome:
    device_id: DeviceId
    reading: Reading | None
    refusal: str | None


# --- collector/store.py ---
from collector.vocabulary import PollOutcome


def recordOutcome(connection: sqlite3.Connection, outcome: PollOutcome) -> None: ...


# --- collector/poller.py ---
from collector.store import recordOutcome
from collector.vocabulary import PollOutcome


# C
# --- collector/store.py ---
def recordOutcome(connection: sqlite3.Connection, device_id: DeviceId, celsius: float | None) -> None: ...


# --- collector/poller.py ---
from collector.store import recordOutcome


@dataclass(frozen=True, slots=True)
class PollOutcome:
    device_id: DeviceId
    reading: Reading | None
    refusal: str | None


def finishOne(connection: sqlite3.Connection, outcome: PollOutcome) -> None:
    celsius = outcome.reading.celsius if outcome.reading is not None else None
    recordOutcome(connection, outcome.device_id, celsius)
```

## R7-A03

```python
# A — the workflow owns the database lifetime
# --- collector/service.py ---
from collector.poller import pollForever


def runService(config: ServiceConfig) -> int:
    return asyncio.run(pollForever(config))


# --- collector/poller.py ---
from collector.store import openDatabase


async def pollForever(config: ServiceConfig) -> int:
    with closing(openDatabase(config.database)) as connection:
        while not stopRequested():
            await pollRound(connection, config.devices)
            await asyncio.sleep(config.interval_s)

    return EXIT_SUCCESS


# B — the entry point owns it and passes it down
# --- collector/service.py ---
from collector.poller import pollForever
from collector.store import openDatabase


def runService(config: ServiceConfig) -> int:
    with closing(openDatabase(config.database)) as connection:
        return asyncio.run(pollForever(connection, config))


# --- collector/poller.py ---
async def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    while not stopRequested():
        await pollRound(connection, config.devices)
        await asyncio.sleep(config.interval_s)

    return EXIT_SUCCESS
```

## R7-A04

```python
# A
# --- collector/errors.py ---
class CollectorError(RuntimeError):
    """Anything this service refuses to read or cannot reach."""


class UnreachableDeviceError(CollectorError): ...
class CorruptFrameError(CollectorError): ...
class UnknownDeviceError(CollectorError): ...
class StoreError(CollectorError): ...


# --- collector/protocol.py ---
from collector.errors import CorruptFrameError

# --- collector/config.py ---
from collector.errors import UnknownDeviceError


# B
# --- collector/errors.py ---
class CollectorError(RuntimeError):
    """Anything this service refuses to read or cannot reach."""


# --- collector/protocol.py ---
from collector.errors import CollectorError


def parseFrame(raw: bytes) -> Frame: ...


### vocabulary #########################################################################

class CorruptFrameError(CollectorError): ...


# --- collector/config.py ---
from collector.errors import CollectorError


def deviceFor(device_id: DeviceId) -> DeviceEntry: ...


### vocabulary #########################################################################

class UnknownDeviceError(CollectorError): ...
```

## R7-A05

`scanlib/frame.py` reads the wire format. `tools/make_fixture.py` writes it. They must agree.

```python
# A — a third module owns the format
# --- scanlib/protocol.py ---
FRAME_FORMAT = '<4sHIH12sIHI'
FRAME_BYTES = struct.calcsize(FRAME_FORMAT)
MAGIC = b'ISCN'

# --- scanlib/frame.py ---
from scanlib.protocol import FRAME_BYTES, FRAME_FORMAT, MAGIC

# --- tools/make_fixture.py ---
from scanlib.protocol import FRAME_FORMAT, MAGIC


# B — each side carries its own copy
# --- scanlib/frame.py ---
FRAME_FORMAT = '<4sHIH12sIHI'   # must match tools/make_fixture.py
FRAME_BYTES = struct.calcsize(FRAME_FORMAT)
MAGIC = b'ISCN'

# --- tools/make_fixture.py ---
FRAME_FORMAT = '<4sHIH12sIHI'   # must match scanlib/frame.py
MAGIC = b'ISCN'


# C — the writer imports from the reader; no third module
# --- scanlib/frame.py ---
FRAME_FORMAT = '<4sHIH12sIHI'
FRAME_BYTES = struct.calcsize(FRAME_FORMAT)
MAGIC = b'ISCN'

# --- tools/make_fixture.py ---
from scanlib.frame import FRAME_FORMAT, MAGIC
```

## R7-A06

Two instrument models today, a third expected.

```python
# A — each model module registers itself at import
# --- collector/dispatch.py ---
READERS: dict[str, Callable[[bytes], Reading]] = {}


def register(model: str, reader: Callable[[bytes], Reading]) -> None:
    global READERS
    READERS[model] = reader


def readFrame(model: str, raw: bytes) -> Reading:
    reader = READERS.get(model)
    if reader is None:
        raise UnknownDeviceError(f'no reader for model {model}')

    return reader(raw)


# --- collector/models/acme_x200.py ---
from collector.dispatch import register


def readAcmeX200(raw: bytes) -> Reading: ...


register('acme-x200', readAcmeX200)


# B — one place names every model
# --- collector/dispatch.py ---
from collector.models.acme_x200 import readAcmeX200
from collector.models.tesla_t9 import readTeslaT9


def readFrame(model: DeviceModel, raw: bytes) -> Reading:
    match model:
        case DeviceModel.ACME_X200:
            return readAcmeX200(raw)
        case DeviceModel.TESLA_T9:
            return readTeslaT9(raw)


# --- collector/models/acme_x200.py ---
def readAcmeX200(raw: bytes) -> Reading: ...
```

## R7-A07

```python
# A — leaf modules import the constants they need
# --- collector/store.py ---
from collector.settings import DATABASE_PATH, RETENTION_DAYS


def pruneOldReadings(connection: sqlite3.Connection) -> int:
    cutoff = time.time() - RETENTION_DAYS * SECONDS_PER_DAY
    return connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,)).rowcount


# B — one frozen config, built at startup, threaded down
# --- collector/store.py ---
def pruneOldReadings(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    cutoff = time.time() - config.retention_days * SECONDS_PER_DAY
    return connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,)).rowcount


# C — one module-level config object, set once at startup
# --- collector/settings.py ---
CONFIG: ServiceConfig = ServiceConfig()


def loadSettings(path: Path) -> None:
    global CONFIG
    CONFIG = parseSettings(path.read_text())


# --- collector/store.py ---
from collector.settings import CONFIG


def pruneOldReadings(connection: sqlite3.Connection) -> int:
    cutoff = time.time() - CONFIG.retention_days * SECONDS_PER_DAY
    return connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,)).rowcount
```

## R7-A08

A poll round covers 40 devices. Three are unreachable.

```python
# A
# --- collector/poller.py ---
async def pollRound(connection: sqlite3.Connection, devices: DeviceTable) -> RoundReport:
    outcomes: list[PollOutcome] = []
    for device in devices.entries:
        try:
            outcomes.append(await pollOne(connection, device))
        except CollectorError as exc:
            LOG.debug('device_failed', extra={'device_id': device.device_id, 'error': str(exc)})
            outcomes.append(PollOutcome(device.device_id, None, str(exc)))

    return RoundReport(tuple(outcomes))


# --- collector/service.py ---
async def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    while not stopRequested():
        report = await pollRound(connection, config.devices)
        LOG.warning('round_complete', extra={'read': report.read, 'refused': report.refused})
        await asyncio.sleep(config.interval_s)

    return EXIT_SUCCESS


# B
# --- collector/poller.py ---
async def pollRound(connection: sqlite3.Connection, devices: DeviceTable) -> RoundReport:
    outcomes = [await pollOne(connection, device) for device in devices.entries]
    return RoundReport(tuple(outcomes))


# --- collector/service.py ---
async def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    while not stopRequested():
        try:
            report = await pollRound(connection, config.devices)
        except CollectorError as exc:
            LOG.error('round_aborted', extra={'error': str(exc)})
            return EXIT_FAILURE

        LOG.info('round_complete', extra={'read': report.read})
        await asyncio.sleep(config.interval_s)

    return EXIT_SUCCESS
```

---

# Block B — where the cuts go

## R7-B01

One service. Same functions, same behaviour, three arrangements.

```python
# A — one file, 340 lines
# --- collector.py ---
def main() -> int: ...
def runService(config: ServiceConfig) -> int: ...
def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int: ...
def pollRound(connection: sqlite3.Connection, devices: DeviceTable) -> RoundReport: ...
def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome: ...
def parseFrame(raw: bytes) -> Frame: ...
def verifyChecksum(raw: bytes, frame: Frame) -> bool: ...
def openDatabase(path: Path) -> sqlite3.Connection: ...
def insertReading(connection: sqlite3.Connection, reading: Reading) -> None: ...
def pruneOldReadings(connection: sqlite3.Connection, config: ServiceConfig) -> int: ...
def renderRound(report: RoundReport) -> str: ...
### vocabulary — Reading, DeviceEntry, PollOutcome, RoundReport, ServiceConfig, 4 error types


# B — six modules, 40 to 90 lines each
# --- collector/__main__.py ---    main, parseArguments
# --- collector/service.py ---     runService, pollForever
# --- collector/poller.py ---      pollRound, pollOne
# --- collector/protocol.py ---    parseFrame, verifyChecksum
# --- collector/store.py ---       openDatabase, insertReading, pruneOldReadings
# --- collector/report.py ---      renderRound
# --- collector/vocabulary.py ---  the dataclasses, the Enum, the error types


# C — two files, split only where drift_check already needs the same code
# --- collector.py ---        main, runService, pollForever, pollRound, pollOne,
#                             openDatabase, insertReading, pruneOldReadings,
#                             renderRound                                       (280 lines)
# --- scanlib/frame.py ---    parseFrame, verifyChecksum, Frame                  (60 lines)
#                             drift_check imports scanlib.frame and nothing else
```

## R7-B02

The same 340 lines, cut two ways.

```python
# A — by technical layer
# --- collector/protocol.py ---  parseFrame, verifyChecksum, parseDeviceTable
# --- collector/store.py ---     openDatabase, insertReading, pruneOldReadings, readingSeen
# --- collector/report.py ---    renderRound, writeStatusFile
# --- collector/poller.py ---    pollForever, pollRound, pollOne     (imports all three)


# B — by vertical slice
# --- collector/polling.py ---   parseFrame, verifyChecksum, pollOne, insertReading
# --- collector/service.py ---   pollForever, pollRound, openDatabase, pruneOldReadings,
#                                renderRound, writeStatusFile        (imports polling)
```

## R7-B03

```python
# A — retention.py exists, 28 lines
# --- collector/retention.py ---
RETENTION_DAYS = 90
PRUNE_BATCH = 5_000


def cutoffFor(now: EpochSeconds, retention_days: int) -> EpochSeconds:
    return EpochSeconds(now - retention_days * SECONDS_PER_DAY)


def pruneOldReadings(connection: sqlite3.Connection, cutoff: EpochSeconds) -> int:
    deleted = connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,))
    return deleted.rowcount


# --- collector/store.py ---   (150 lines)
from collector.retention import cutoffFor, pruneOldReadings


# B — the same four names live in store.py, which is 28 lines longer
# --- collector/store.py ---   (178 lines)
RETENTION_DAYS = 90
PRUNE_BATCH = 5_000


def openDatabase(path: Path) -> sqlite3.Connection: ...
def insertReading(connection: sqlite3.Connection, reading: Reading) -> None: ...
def cutoffFor(now: EpochSeconds, retention_days: int) -> EpochSeconds: ...
def pruneOldReadings(connection: sqlite3.Connection, cutoff: EpochSeconds) -> int: ...
```

## R7-B04

Three helpers. `crc32Of` is also called by `drift_check`; the other two are not.

```python
# A
# --- collector/utils.py ---
def humanBytes(count: int) -> str: ...
def chunked(readings: Sequence[Reading], size: int) -> Iterator[Sequence[Reading]]: ...
def crc32Of(payload: bytes) -> int: ...


# B — each helper sits in its only caller
# --- collector/report.py ---    humanBytes, renderRound
# --- collector/store.py ---     chunked, insertReadings
# --- scanlib/frame.py ---       crc32Of, parseFrame, verifyChecksum
#                                drift_check imports crc32Of from scanlib.frame


# C — one cohesive named module for the shared one; the other two stay local
# --- scanlib/checksum.py ---    crc32Of, verifyChecksum
#                                imported by scanlib/frame.py and by drift_check
# --- collector/report.py ---    humanBytes, renderRound
# --- collector/store.py ---     chunked, insertReadings
```

## R7-B05

```python
# A
# --- scanlib/__init__.py ---
# empty


# --- collector/poller.py ---
from scanlib.frame import parseFrame
from scanlib.vocabulary import Frame


# B
# --- scanlib/__init__.py ---
"""Read and write the instrument scan wire format."""

from scanlib.frame import parseFrame, verifyChecksum
from scanlib.vocabulary import Frame

__all__ = ['Frame', 'parseFrame', 'verifyChecksum']


# --- collector/poller.py ---
from scanlib import Frame, parseFrame


# C
# --- scanlib/__init__.py ---
"""Read and write the instrument scan wire format."""

import logging

from scanlib.frame import parseFrame, verifyChecksum
from scanlib.vocabulary import Frame

FRAME_BYTES = 32

LOG = logging.getLogger('scanlib')

__all__ = ['FRAME_BYTES', 'LOG', 'Frame', 'parseFrame', 'verifyChecksum']


# --- collector/poller.py ---
from scanlib import FRAME_BYTES, Frame, parseFrame
```

## R7-B06

```python
# A
from collector.store import insertReading, readingSeen


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome:
    reading = await readDevice(device)
    if readingSeen(connection, reading.device_id, reading.observed_at):
        return PollOutcome(device.device_id, reading, 'duplicate')

    insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)


# B
from collector import store


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome:
    reading = await readDevice(device)
    if store.readingSeen(connection, reading.device_id, reading.observed_at):
        return PollOutcome(device.device_id, reading, 'duplicate')

    store.insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)
```

## R7-B07

`Reading` crosses: `protocol` builds it, `store` writes it, `report` prints it. `FrameHeader` does
not: only `protocol.py` ever constructs or reads one. Where does `FrameHeader` go?

```python
# A — the package glossary holds every type, crossing or not
# --- collector/vocabulary.py ---
DeviceId = NewType('DeviceId', str)


@dataclass(frozen=True, slots=True)
class FrameHeader:
    magic: bytes
    version: int
    payload_len: int


@dataclass(frozen=True, slots=True)
class Reading:
    device_id: DeviceId
    celsius: float


# --- collector/protocol.py ---
from collector.vocabulary import DeviceId, FrameHeader, Reading


def readHeader(raw: bytes) -> FrameHeader: ...
def parseFrame(raw: bytes) -> Reading: ...


# B — the glossary holds what crosses; a single-module type stays with its module
# --- collector/vocabulary.py ---
DeviceId = NewType('DeviceId', str)


@dataclass(frozen=True, slots=True)
class Reading:
    device_id: DeviceId
    celsius: float


# --- collector/protocol.py ---
from collector.vocabulary import DeviceId, Reading


def readHeader(raw: bytes) -> FrameHeader: ...
def parseFrame(raw: bytes) -> Reading: ...


### vocabulary #########################################################################


@dataclass(frozen=True, slots=True)
class FrameHeader:
    magic: bytes
    version: int
    payload_len: int
```

The day something else needs `FrameHeader` — a fixture generator, a diagnostic that dumps a raw
frame — B moves it and every import of it changes. A never moves anything.

## R7-B08

```python
# A — internals carry a leading underscore
# --- scanlib/frame.py ---
def parseFrame(raw: bytes) -> Frame: ...
def _unpackFields(raw: bytes) -> tuple[object, ...]: ...
def _verifyMagic(magic: bytes) -> None: ...


# B — every name is spelled the same way; each module declares its surface
# --- scanlib/frame.py ---
__all__ = ['parseFrame']


def parseFrame(raw: bytes) -> Frame: ...
def unpackFields(raw: bytes) -> tuple[object, ...]: ...
def verifyMagic(magic: bytes) -> None: ...


# C — nothing is marked; the import graph is the documentation
# --- scanlib/frame.py ---
def parseFrame(raw: bytes) -> Frame: ...
def unpackFields(raw: bytes) -> tuple[object, ...]: ...
def verifyMagic(magic: bytes) -> None: ...
```

## R7-B09

```python
# A
# --- collector/__main__.py ---
"""Poll instruments over TCP and write readings to SQLite.

Usage:
    $ python3 -m collector --settings /etc/collector.toml
"""


def main() -> int:
    ...


if __name__ == '__main__':
    sys.exit(main())


# B
# --- collector/service.py ---
"""Poll instruments over TCP and write readings to SQLite.

Usage:
    $ python3 -m collector --settings /etc/collector.toml
"""


def main() -> int:
    ...


# --- collector/__main__.py ---
"""Entry point for `python3 -m collector`."""

import sys

from collector.service import main

sys.exit(main())
```

## R7-B10

An internal module of the library. Nothing runs it directly.

```python
# A
# --- scanlib/frame.py ---
"""Read the fixed 32-byte frame header of an instrument reply.

The header is little-endian and fixed-width. A reply whose magic, version or checksum does not
match raises CorruptFrameError, which the caller turns into a refusal.
"""

from __future__ import annotations

import struct


def parseFrame(raw: bytes) -> Frame:
    """Parse the header of one reply frame.

    Raises:
        CorruptFrameError: the magic, the version or the length is wrong.
    """


# B
# --- scanlib/frame.py ---
from __future__ import annotations

import struct


def parseFrame(raw: bytes) -> Frame:
    """Parse the fixed 32-byte little-endian header of one reply frame.

    Raises:
        CorruptFrameError: the magic, the version or the length is wrong.
    """
```

---

# Block C — the abstraction budget

## R7-C01

`SqliteReadingStore` is the only implementation in the repository, and the tests use a real temporary
database.

```python
# A
class ReadingStore(Protocol):

    def insert(self, reading: Reading) -> None: ...

    def seen(self, device_id: DeviceId, observed_at: MonotonicSeconds) -> bool: ...


class SqliteReadingStore:

    def insert(self, reading: Reading) -> None: ...

    def seen(self, device_id: DeviceId, observed_at: MonotonicSeconds) -> bool: ...


async def pollOne(store: ReadingStore, device: DeviceEntry) -> PollOutcome: ...


# B
class SqliteReadingStore:

    def insert(self, reading: Reading) -> None: ...

    def seen(self, device_id: DeviceId, observed_at: MonotonicSeconds) -> bool: ...


async def pollOne(store: SqliteReadingStore, device: DeviceEntry) -> PollOutcome: ...
```

## R7-C02

```python
# A — the store is an object, built at startup and passed down
class SqliteReadingStore:

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def insert(self, reading: Reading) -> None:
        self.connection.execute('INSERT INTO readings VALUES (?, ?)', (reading.device_id, reading.celsius))

    def seen(self, device_id: DeviceId, observed_at: MonotonicSeconds) -> bool:
        row = self.connection.execute(
            'SELECT 1 FROM readings WHERE device_id = ? AND observed_at = ?',
            (device_id, observed_at),
        )

        return row.fetchone() is not None


async def pollOne(store: SqliteReadingStore, device: DeviceEntry) -> PollOutcome:
    reading = await readDevice(device)
    if store.seen(reading.device_id, reading.observed_at):
        return PollOutcome(device.device_id, reading, 'duplicate')

    store.insert(reading)
    return PollOutcome(device.device_id, reading, None)


# B — the store is a module of functions; the connection is the only thing passed
# --- collector/store.py ---
def insertReading(connection: sqlite3.Connection, reading: Reading) -> None:
    connection.execute('INSERT INTO readings VALUES (?, ?)', (reading.device_id, reading.celsius))


def readingSeen(connection: sqlite3.Connection, device_id: DeviceId, observed_at: MonotonicSeconds) -> bool:
    row = connection.execute(
        'SELECT 1 FROM readings WHERE device_id = ? AND observed_at = ?',
        (device_id, observed_at),
    )

    return row.fetchone() is not None


# --- collector/poller.py ---
from collector import store


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome:
    reading = await readDevice(device)
    if store.readingSeen(connection, reading.device_id, reading.observed_at):
        return PollOutcome(device.device_id, reading, 'duplicate')

    store.insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)
```

## R7-C03

```python
# A — each stage decides and calls the next
async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome:
    return verifyAndStore(connection, device, await readDevice(device))


def verifyAndStore(connection: sqlite3.Connection, device: DeviceEntry, raw: bytes) -> PollOutcome:
    frame = parseFrame(raw)
    if not verifyChecksum(raw, frame):
        return PollOutcome(device.device_id, None, 'bad checksum')

    return storeAndReport(connection, device, frame)


def storeAndReport(connection: sqlite3.Connection, device: DeviceEntry, frame: Frame) -> PollOutcome:
    reading = Reading(device.device_id, frame.celsius, frame.observed_at)
    insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)


# B — one coordinator calls each stage in turn and holds the intermediates
async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome:
    raw = await readDevice(device)
    frame = parseFrame(raw)
    if not verifyChecksum(raw, frame):
        return PollOutcome(device.device_id, None, 'bad checksum')

    reading = Reading(device.device_id, frame.celsius, frame.observed_at)
    insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)
```

## R7-C04

The service runs with `--read-only` during a maintenance window: poll and report, write nothing.

```python
# A — the flag reaches the leaves
async def pollRound(connection: sqlite3.Connection, devices: DeviceTable, *, read_only: bool) -> RoundReport: ...


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry, *, read_only: bool) -> PollOutcome:
    reading = parseReading(await readDevice(device))
    insertReading(connection, reading, read_only=read_only)
    return PollOutcome(device.device_id, reading, None)


def insertReading(connection: sqlite3.Connection, reading: Reading, *, read_only: bool) -> None:
    if read_only:
        return

    connection.execute('INSERT INTO readings VALUES (?, ?)', (reading.device_id, reading.celsius))


# B — the flag stops at the level that can act on it
async def pollRound(connection: sqlite3.Connection, devices: DeviceTable, *, read_only: bool) -> RoundReport: ...


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry, *, read_only: bool) -> PollOutcome:
    reading = parseReading(await readDevice(device))
    if read_only:
        return PollOutcome(device.device_id, reading, None)

    insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)


def insertReading(connection: sqlite3.Connection, reading: Reading) -> None:
    connection.execute('INSERT INTO readings VALUES (?, ?)', (reading.device_id, reading.celsius))
```

## R7-C05

```python
# A
async def pollOne(
    connection: sqlite3.Connection,
    devices: Mapping[DeviceId, DeviceEntry],
    status_path: Path,
    device: DeviceEntry,
) -> PollOutcome:
    reading = parseReading(await readDevice(device))
    entry = devices[reading.device_id]
    insertReading(connection, reading, entry)
    return writeStatus(status_path, reading)


# B
@dataclass(frozen=True, slots=True)
class Collection:
    connection: sqlite3.Connection
    devices: Mapping[DeviceId, DeviceEntry]
    status_path: Path


async def pollOne(collection: Collection, device: DeviceEntry) -> PollOutcome:
    reading = parseReading(await readDevice(device))
    entry = collection.devices[reading.device_id]
    insertReading(collection.connection, reading, entry)
    return writeStatus(collection.status_path, reading)
```

## R7-C06

Four routing rules, three effects: a row, a status file, a log record. `logPlan` emits exactly the
records A emits, at the same levels, so the two are behaviourally identical.

```python
# A — decide and act together
def recordReading(connection: sqlite3.Connection, reading: Reading, devices: DeviceTable) -> PollOutcome:
    entry = devices.entries.get(reading.device_id)

    if entry is None:
        writeStatus(STATUS_PATH, reading.device_id, 'unknown device')
        LOG.warning('reading_refused', extra={'device_id': reading.device_id, 'reason': 'unknown device'})
        return PollOutcome(reading.device_id, None, 'unknown device')

    if not entry.calibration_valid:
        writeStatus(STATUS_PATH, reading.device_id, 'calibration expired')
        LOG.warning('reading_refused', extra={'device_id': reading.device_id, 'reason': 'calibration expired'})
        return PollOutcome(reading.device_id, None, 'calibration expired')

    connection.execute('INSERT INTO readings VALUES (?, ?, ?)', (reading.device_id, entry.site_code, reading.celsius))
    writeStatus(STATUS_PATH, reading.device_id, 'ok')
    LOG.info('reading_stored', extra={'device_id': reading.device_id})
    return PollOutcome(reading.device_id, reading, None)


# B — a pure decision, then one executor
# RecordPlan(outcome, status, row, refusal) is a frozen slotted dataclass.
def planRecord(reading: Reading, devices: DeviceTable) -> RecordPlan:
    entry = devices.entries.get(reading.device_id)
    if entry is None:
        return RecordPlan(Outcome.REFUSED, 'unknown device', None, 'unknown device')
    if not entry.calibration_valid:
        return RecordPlan(Outcome.REFUSED, 'calibration expired', None, 'calibration expired')

    return RecordPlan(Outcome.STORED, 'ok', ReadingRow(reading.device_id, entry.site_code, reading.celsius), None)


def applyPlan(connection: sqlite3.Connection, reading: Reading, plan: RecordPlan) -> PollOutcome:
    if plan.row is not None:
        connection.execute('INSERT INTO readings VALUES (?, ?, ?)', astuple(plan.row))

    writeStatus(STATUS_PATH, reading.device_id, plan.status)
    logPlan(reading.device_id, plan)
    return PollOutcome(reading.device_id, reading if plan.row is not None else None, plan.refusal)


def recordReading(connection: sqlite3.Connection, reading: Reading, devices: DeviceTable) -> PollOutcome:
    return applyPlan(connection, reading, planRecord(reading, devices))
```

## R7-C07

Both emit exactly one log record, with the same fields and the same text.

```python
# A
def renderRound(report: RoundReport) -> str:
    return f'{report.read} read, {report.refused} refused'


def logRound(report: RoundReport) -> None:
    LOG.info('round_complete', extra={'summary': renderRound(report)})


# B
def logRound(report: RoundReport) -> None:
    LOG.info('round_complete', extra={'summary': f'{report.read} read, {report.refused} refused'})
```

## R7-C08

```python
# A
def testPollOneInsertsARow(tmp_path: Path) -> None:
    connection = openDatabase(tmp_path / 'readings.db')
    device = fakeDeviceServing(FRAME_FIXTURE)

    assert pollOne(connection, device).refusal is None
    assert connection.execute('SELECT 1 FROM readings WHERE device_id = ?', (DEVICE_ID,)).fetchone() is not None


# B
class FakeReadingStore:

    def __init__(self) -> None:
        self.inserted: list[Reading] = []

    def insert(self, reading: Reading) -> None:
        self.inserted.append(reading)

    def seen(self, device_id: DeviceId, observed_at: MonotonicSeconds) -> bool:
        return any(reading.device_id == device_id for reading in self.inserted)


def testPollOneInsertsARow() -> None:
    store = FakeReadingStore()
    device = fakeDeviceServing(FRAME_FIXTURE)

    assert pollOne(store, device).refusal is None
    assert [reading.device_id for reading in store.inserted] == [DEVICE_ID]
```

---

# Block D — third-party code

## R7-D01

```python
# A — the handle travels
# --- collector/store.py ---
def openDatabase(path: Path) -> sqlite3.Connection: ...
def insertReading(connection: sqlite3.Connection, reading: Reading) -> None: ...


# --- collector/poller.py ---
async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome: ...


# --- collector/service.py ---
async def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int: ...


# --- collector/retention.py ---
def pruneOldReadings(connection: sqlite3.Connection, cutoff: EpochSeconds) -> int: ...


# B — sqlite3 appears in exactly one module
# --- collector/store.py ---
class ReadingStore:

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def insert(self, reading: Reading) -> None: ...

    def pruneBefore(self, cutoff: EpochSeconds) -> int: ...


def openStore(path: Path) -> ReadingStore:
    return ReadingStore(sqlite3.connect(path))


# --- collector/poller.py ---
async def pollOne(store: ReadingStore, device: DeviceEntry) -> PollOutcome: ...


# --- collector/service.py ---
async def pollForever(store: ReadingStore, config: ServiceConfig) -> int: ...


# --- collector/retention.py ---
def pruneOldReadings(store: ReadingStore, cutoff: EpochSeconds) -> int: ...
```

## R7-D02

The collector must POST a health record to an internal endpoint every round.

**Not behaviourally identical, and the differences are inherent to the choice, not added:** B
raises its own `HealthReportError` where A lets `httpx` raise, and B needs `asyncio.to_thread`
because `urllib` blocks and `R2-04` makes this program async. Judge the choice with those costs
attached rather than discounting B for carrying them.

```python
# A — the dependency
import httpx


async def reportHealth(client: httpx.AsyncClient, report: RoundReport) -> None:
    payload = {'read': report.read, 'refused': report.refused}
    response = await client.post(HEALTH_URL, json=payload, timeout=HEALTH_TIMEOUT_S)
    response.raise_for_status()


# B — the standard library
async def reportHealth(report: RoundReport) -> None:
    body = json.dumps({'read': report.read, 'refused': report.refused}).encode()
    request = urllib.request.Request(HEALTH_URL, data=body, headers={'Content-Type': 'application/json'})

    def send() -> None:
        with urllib.request.urlopen(request, timeout=HEALTH_TIMEOUT_S) as response:
            if response.status >= HTTP_BAD_REQUEST:
                raise HealthReportError(f'health endpoint returned {response.status}')

    await asyncio.to_thread(send)
```

## R7-D03

`httpx` has been chosen. Two ways to use it.

```python
# A — call it where it is needed
# --- collector/health.py ---
import httpx


async def reportHealth(client: httpx.AsyncClient, report: RoundReport) -> None:
    response = await client.post(HEALTH_URL, json=asdict(report), timeout=HEALTH_TIMEOUT_S)
    response.raise_for_status()


# --- collector/service.py ---
import httpx


async def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    async with httpx.AsyncClient() as client:
        ...
        await reportHealth(client, report)


# B — one adapter module owns it
# --- collector/http.py ---
import httpx


class HealthClient:

    def __init__(self, client: httpx.AsyncClient, url: str) -> None:
        self._client = client
        self._url = url

    async def post(self, payload: Mapping[str, object]) -> None:
        response = await self._client.post(self._url, json=payload, timeout=HEALTH_TIMEOUT_S)
        response.raise_for_status()


@asynccontextmanager
async def openHealthClient(url: str) -> AsyncIterator[HealthClient]:
    async with httpx.AsyncClient() as client:
        yield HealthClient(client, url)


# --- collector/health.py ---
async def reportHealth(client: HealthClient, report: RoundReport) -> None:
    await client.post(asdict(report))
```

## R7-D04

The ORM ban (`TID251`) is lifted for code that is not a request handler. How does that generalise?

```toml
# A — by directory, as today
[tool.ruff.lint.per-file-ignores]
'**/maintenance/**' = ['TID251']
'**/scripts/**' = ['TID251']
'**/migrations/**' = ['TID251']

# B — no central list; the exception is a property of the module and is declared there.
#     collector/maintenance/backfill_site_codes.py opens with:
#
#     """Backfill site codes for readings ingested before 2026-06.
#
#     Uses SQLAlchemy. This runs once, by hand, over a table nothing is reading, so
#     developer time outweighs the per-row validation cost the ban exists to prevent
#     (Q17, R6-03).
#     """
#     # ruff: noqa: TID251

# C — no per-path exception; a module that needs an ORM is a separate program
#     with its own pyproject.toml, and the shared code between them is a library
#     that uses neither
```

## R7-D05

`drift_check` needs a Theil-Sen slope estimator. A maintained package provides it in one import; the
algorithm is about 40 lines.

```python
# A — depend
from robuststats import theilSen


def calibrationDrift(readings: Sequence[Reading]) -> float:
    return theilSen([reading.observed_at for reading in readings], [reading.celsius for reading in readings])


# B — vendor the one file, with its licence header and its origin
# --- drift_check/vendor/theil_sen.py ---   42 lines, copied at v2.1.0, unmodified
"""Theil-Sen slope estimator.

Vendored from robuststats 2.1.0 (BSD-3-Clause). Do not edit; re-copy to update.
"""


# C — write it
def theilSen(times: Sequence[float], values: Sequence[float]) -> float:
    """Return the median pairwise slope, which no single outlier can move."""
    slopes = sorted(
        (values[j] - values[i]) / (times[j] - times[i])
        for i in range(len(times))
        for j in range(i + 1, len(times))
        if times[j] != times[i]
    )

    return median(slopes)
```

## R7-D06

`scanlib` is imported by `collector` and by `drift_check`, and one day by something outside this
repository.

```
# A — scanlib pins what it was tested against
#     pyproject.toml:  dependencies = ['httpx==0.28.1']
#     A consumer that needs httpx 0.29 cannot install scanlib.

# B — scanlib states a floor and no ceiling
#     pyproject.toml:  dependencies = ['httpx>=0.28']
#     A consumer resolves whatever it likes. scanlib is tested against one version and
#     runs against any later one.

# C — scanlib states a floor, and the repository pins the exact set in one lock file
#     that every program in it installs from. The pin is a property of the deployment,
#     never of the library.
```

---

# Block E — service, library, repository

## R7-E01

`LOG = logging.getLogger('collector')` at module level is uncontroversial. `DB` at module level is
not — `R7-A03`, `R7-C02` and `R7-D01` all put the connection in the entry point and passed it down.
What separates them?

```python
# A — nothing; the logger should be passed too
# --- collector/service.py ---
def runService(config: ServiceConfig) -> int:
    log = configureLogging(verbose=config.verbose)
    with closing(openDatabase(config.database)) as connection:
        return pollForever(connection, log, config)


# --- collector/store.py ---
def insertReading(connection: sqlite3.Connection, log: logging.Logger, reading: Reading) -> None: ...


# B — a module-level singleton is fine for anything that never needs closing
# --- collector/logs.py ---
LOG = logging.getLogger('collector')          # nothing to close, so it may be a global


# --- collector/store.py ---
from collector.logs import LOG


def insertReading(connection: sqlite3.Connection, reading: Reading) -> None:   # but the handle is passed
    ...


# C — a module-level singleton is fine for anything built without runtime input
# --- collector/logs.py ---
LOG = logging.getLogger('collector')          # needs only a literal name


# --- collector/store.py ---
DB_PATH_DEFAULT = Path('readings.db')         # a literal, so a global
                                              # the connection needs config.database, so it is not


def insertReading(connection: sqlite3.Connection, reading: Reading) -> None: ...
```

## R7-E02

```python
# A
# --- collector/protocol.py ---
LOG = logging.getLogger(__name__)


def parseFrame(raw: bytes) -> Frame:
    ...
    LOG.debug('frame_parsed', extra={'device_id': frame.device_id})


# --- collector/store.py ---
LOG = logging.getLogger(__name__)


# B
# --- collector/logs.py ---
LOG = logging.getLogger('collector')


def configureLogging(*, verbose: bool) -> None: ...


# --- collector/protocol.py ---
from collector.logs import LOG


def parseFrame(raw: bytes) -> Frame:
    ...
    LOG.debug('frame_parsed', extra={'device_id': frame.device_id})


# --- collector/store.py ---
from collector.logs import LOG
```

The emitted record's `name` field differs — `collector.protocol` against `collector`. That is
inherent to the dimension, not a second variable.

## R7-E03

```python
# A — one config object reaches every module
@dataclass(frozen=True, slots=True)
class ServiceConfig:
    devices: Mapping[DeviceId, DeviceEntry]
    database: Path
    status_path: Path
    interval_s: float
    retention_days: int
    health_url: str


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry, config: ServiceConfig) -> PollOutcome: ...


def pruneOldReadings(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    cutoff = EpochSeconds(time.time() - config.retention_days * SECONDS_PER_DAY)
    return connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,)).rowcount


# B — each module takes the slice it uses
@dataclass(frozen=True, slots=True)
class RetentionConfig:
    retention_days: int


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry, config: ServiceConfig) -> PollOutcome: ...


def pruneOldReadings(connection: sqlite3.Connection, config: RetentionConfig) -> int:
    cutoff = EpochSeconds(time.time() - config.retention_days * SECONDS_PER_DAY)
    return connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,)).rowcount
```

## R7-E04

```python
# A
def parseReading(reply: bytes) -> Reading:
    device_id, celsius = replyFields(reply)
    return Reading(
        device_id=DeviceId(device_id),
        celsius=celsius,
        observed_at=MonotonicSeconds(time.monotonic()),
    )


async def pollOne(device: DeviceEntry) -> Reading:
    await sendRequest(device.writer, STATUS_REQUEST)
    return parseReading(await readReply(device.reader))


# B
def parseReading(reply: bytes, observed_at: MonotonicSeconds) -> Reading:
    device_id, celsius = replyFields(reply)
    return Reading(
        device_id=DeviceId(device_id),
        celsius=celsius,
        observed_at=observed_at,
    )


async def pollOne(device: DeviceEntry) -> Reading:
    await sendRequest(device.writer, STATUS_REQUEST)
    reply = await readReply(device.reader)
    return parseReading(reply, MonotonicSeconds(time.monotonic()))
```

## R7-E05

`scanlib` has no `main()`. The style says `main()` comes first because it is the thesis and the
reader goes there first. What takes its place?

```python
# A — the public entry function takes the position main() holds
# --- scanlib/frame.py ---
def parseFrame(raw: bytes) -> Frame:        # FIRST: the one function a consumer calls
    ...


def unpackFields(raw: bytes) -> tuple[object, ...]:      # callees, in first-call order
def verifyMagic(magic: bytes) -> None:


### vocabulary #########################################################################

@dataclass(frozen=True, slots=True)
class Frame: ...


# B — a library has no thesis; the module docstring carries it and the order is by dependency
# --- scanlib/frame.py ---
"""Read the fixed 32-byte frame header of an instrument reply.

parseFrame is the entry point. It calls verifyMagic and unpackFields, in that order.
"""


def verifyMagic(magic: bytes) -> None:      # leaves first, nothing forward-referenced
def unpackFields(raw: bytes) -> tuple[object, ...]:
def parseFrame(raw: bytes) -> Frame:        # the public one, last, above the vocabulary


### vocabulary #########################################################################

@dataclass(frozen=True, slots=True)
class Frame: ...
```

## R7-E06

`collector` flags a drifting device in its round report. `drift_check` reports drift over 90 days.
Both need the same slope calculation and the same threshold.

```python
# A — a shared module in the library both already import
# --- scanlib/drift.py ---
DRIFT_THRESHOLD_C_PER_DAY = 0.05


def driftSlope(readings: Sequence[Reading]) -> float: ...
def drifting(readings: Sequence[Reading]) -> bool: ...


# --- collector/poller.py ---
from scanlib.drift import drifting

# --- drift_check/report.py ---
from scanlib.drift import driftSlope, drifting


# B — each program keeps its own copy
# --- collector/drift.py ---     driftSlope, drifting, DRIFT_THRESHOLD_C_PER_DAY
# --- drift_check/drift.py ---   driftSlope, drifting, DRIFT_THRESHOLD_C_PER_DAY
#                                the two copies are identical today


# C — one owner, and the other program calls it
# --- drift_check/drift.py ---   driftSlope, drifting, DRIFT_THRESHOLD_C_PER_DAY
# --- collector/poller.py ---
from drift_check.drift import drifting
```

## R7-E07

Forty instruments. Each pushes a frame when its own reading changes, and also answers a status
request at any time. Both options read every instrument and write every change.

```python
# A — the service asks
async def pollForever(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    while not stopRequested():
        await pollRound(connection, config.devices)
        await asyncio.sleep(config.interval_s)

    return EXIT_SUCCESS


async def pollRound(connection: sqlite3.Connection, devices: DeviceTable) -> RoundReport:
    outcomes = await asyncio.gather(*(pollOne(connection, device) for device in devices.entries))
    return RoundReport(tuple(outcomes))


async def pollOne(connection: sqlite3.Connection, device: DeviceEntry) -> PollOutcome:
    await sendRequest(device.writer, STATUS_REQUEST)
    return recordReading(connection, parseReading(await readReply(device.reader)))


# B — the instrument tells
async def serveForever(connection: sqlite3.Connection, config: ServiceConfig) -> int:
    async with asyncio.TaskGroup() as group:
        for device in config.devices.entries:
            group.create_task(followOne(connection, device))

    return EXIT_SUCCESS


async def followOne(connection: sqlite3.Connection, device: DeviceEntry) -> None:
    while not stopRequested():
        reply = await asyncio.wait_for(readReply(device.reader), timeout=device.silence_timeout_s)
        recordReading(connection, parseReading(reply))
```

Option B reacts as soon as a reading changes and sends nothing when nothing changes. It also has no
round, so `RoundReport` has no natural boundary and the aggregate log record of `Q24` has nothing to
aggregate over. Say what replaces it.
