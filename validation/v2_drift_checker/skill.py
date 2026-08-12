from __future__ import annotations

import json
import math
import sqlite3
import sys
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NewType

from hypothesis import given
from hypothesis import strategies as st


LOG_PATH = Path('jsonl_logs/drift_check.jsonl')
DEFAULT_CONFIG_PATH = Path('drift_tolerances.json')
WARN_FRACTION_OF_TOLERANCE = 0.8
EXIT_SUCCESS = 0
EXIT_DEVICE_FAILED = 1
EXIT_RUN_IMPOSSIBLE = 2
EXIT_RUN_INCOMPLETE = 3


def main() -> int:
    """Classify every device in the calibration database and print the summary on stdout.

    Each stage that can stop the run is caught separately, so the log names the stage rather than a
    tuple of unrelated causes.

    Returns:
        0 when every device was judged OK or WARN, 1 when at least one device is FAIL, 2 when the
        config or the database stopped the run before it could start, 3 when nothing failed but
        some device or some row could not be judged at all.
    """
    parser = ArgumentParser(description='Classify calibration drift per device.')
    parser.add_argument('db_path', type=Path)
    parser.add_argument('--config', dest='config_path', type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    try:
        config = loadConfig(args.config_path)
    except ConfigError as exc:
        logEvent(LogLevel.ERROR, 'run_abandoned', stage='load_config', error=str(exc))
        return EXIT_RUN_IMPOSSIBLE

    try:
        batch = loadReadings(args.db_path)
    except DatabaseError as exc:
        logEvent(LogLevel.ERROR, 'run_abandoned', stage='load_readings', error=str(exc))
        return EXIT_RUN_IMPOSSIBLE

    report = assessDrift(batch, config)
    printReport(report)

    if any(assessment.classification is Classification.FAIL for assessment in report.assessments):
        return EXIT_DEVICE_FAILED
    # A device nobody could judge is not a pass: it leaves the fleet unchecked, so the run is
    # incomplete rather than clean, and the caller can tell the two apart by the code.
    return EXIT_RUN_INCOMPLETE if (report.skipped or report.malformed_rows) else EXIT_SUCCESS


def loadConfig(config_path: Path) -> DriftConfig:
    """Read the drift config into a frozen value, once, at the process boundary.

    The file is a JSON object with `window`, how many of the most recent readings the rolling mean
    covers, and `tolerances`, mapping a device id to the largest mean error that is still
    acceptable for it, in the unit the readings are recorded in.

    Args:
        config_path: JSON file holding window and tolerances.

    Returns:
        The parsed config. Nothing downstream re-checks it.

    Raises:
        ConfigError: The file is missing, unreadable, not JSON, not an object, has no usable window
            or tolerances, or gives a device a tolerance that is not a positive number.
    """
    SMALLEST_USABLE_WINDOW = 2

    if not config_path.is_file():
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='missing')
        raise ConfigError(f'config file does not exist: {config_path}')

    try:
        text = config_path.read_text(encoding='utf-8')
    except OSError as exc:
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='unreadable')
        raise ConfigError(f'config file could not be read: {config_path}') from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='not_json')
        raise ConfigError(f'config file is not valid JSON: {config_path}') from exc

    if not isinstance(raw, dict):
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='not_an_object')
        raise ConfigError(f'config root must be a JSON object: {config_path}')

    window = raw.get('window')
    # A window of one is a single reading, which is a spot check and not a trend, so it is rejected
    # here rather than quietly producing an assessment nobody should act on.
    if not isinstance(window, int) or window < SMALLEST_USABLE_WINDOW:
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='bad_window')
        raise ConfigError(f'window must be an integer of at least {SMALLEST_USABLE_WINDOW}, got {window!r}')

    tolerances = raw.get('tolerances')
    if not isinstance(tolerances, dict):
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='bad_tolerances')
        raise ConfigError(f'tolerances must be a JSON object of device id to tolerance: {config_path}')

    tolerance_by_device: dict[DeviceId, float] = {}
    for device_id, tolerance in tolerances.items():
        if not isinstance(tolerance, (int, float)) or tolerance <= 0:
            logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='bad_tolerance')
            raise ConfigError(f'tolerance for {device_id} must be a positive number, got {tolerance!r}')

        tolerance_by_device[DeviceId(str(device_id))] = float(tolerance)

    logEvent(
        LogLevel.INFO,
        'config_loaded',
        config_path=str(config_path),
        window=window,
        devices=len(tolerance_by_device),
    )

    return DriftConfig(window=window, tolerance_by_device=tolerance_by_device)


def loadReadings(db_path: Path) -> ReadingBatch:
    """Read every calibration row and group it by device, oldest reading first.

    Args:
        db_path: SQLite file holding the calibration_readings table.

    Returns:
        The readings per device plus how many rows were unusable. A row that cannot be parsed is
        counted and dropped, because one bad row must not cost the whole fleet its check.

    Raises:
        DatabaseError: The file is not there, SQLite would not open it, or the query failed -- in
            which case no device has a trustworthy history and there is nothing to report.
    """
    SELECT_SQL = (
        'SELECT device_id, taken_at, reference_value, measured_value'
        ' FROM calibration_readings'
        ' ORDER BY device_id, taken_at'
    )

    if not db_path.is_file():
        logEvent(LogLevel.ERROR, 'database_unusable', db_path=str(db_path), problem='missing')
        raise DatabaseError(f'calibration database does not exist: {db_path}')

    try:
        # Read-only: a checker that can write is a checker that can corrupt the evidence it reads.
        connection = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    except sqlite3.Error as exc:
        logEvent(LogLevel.ERROR, 'database_unusable', db_path=str(db_path), problem='unopenable')
        raise DatabaseError(f'could not open the calibration database at {db_path}') from exc

    try:
        rows = connection.execute(SELECT_SQL).fetchall()
    except sqlite3.Error as exc:
        logEvent(LogLevel.ERROR, 'database_unusable', db_path=str(db_path), problem='query_failed')
        raise DatabaseError(f'could not read calibration_readings from {db_path}') from exc
    finally:
        connection.close()

    by_device: dict[DeviceId, list[Reading]] = {}
    malformed_count = 0
    for row in rows:
        match parseRow(row):
            case Reading() as reading:
                by_device.setdefault(reading.device_id, []).append(reading)
            case MalformedRow() as malformed:
                malformed_count += 1
                logEvent(LogLevel.WARNING, 'row_malformed', problem=malformed.problem.value, detail=malformed.detail)

    logEvent(LogLevel.INFO, 'readings_loaded', db_path=str(db_path), rows=len(rows), devices=len(by_device))

    return ReadingBatch(by_device=by_device, malformed_rows=malformed_count)


def parseRow(row: tuple[object, ...]) -> RowResult:
    """Turn one row of the calibration table into a Reading or a MalformedRow.

    Pure and total: every way a row can be unusable comes back as a value, so the loader needs no
    try around it. SQLite columns are typeless -- a text value in a REAL column is legal and arrives
    as a str -- so the types are checked here rather than assumed from the schema.

    Args:
        row: device_id, taken_at, reference_value, measured_value, straight off the cursor.

    Returns:
        A Reading whose timestamp is already a datetime, or a MalformedRow naming the column that
        was wrong and showing what was in it.
    """
    device_id, taken_at, reference_value, measured_value = row

    if not isinstance(device_id, str) or not device_id:
        return MalformedRow(RowProblem.BAD_DEVICE_ID, repr(device_id))
    if not isinstance(taken_at, str):
        return MalformedRow(RowProblem.BAD_TIMESTAMP, repr(taken_at))
    if not isinstance(reference_value, (int, float)) or not isinstance(measured_value, (int, float)):
        return MalformedRow(RowProblem.BAD_VALUE, f'{reference_value!r}, {measured_value!r}')

    try:
        # On 3.10 fromisoformat only reads what isoformat() writes -- no trailing 'Z', no
        # abbreviated forms. The pipeline writes isoformat, so anything else is not our row.
        parsed_at = datetime.fromisoformat(taken_at)
    except ValueError:
        return MalformedRow(RowProblem.BAD_TIMESTAMP, taken_at)

    return Reading(
        device_id=DeviceId(device_id),
        taken_at=parsed_at,
        reference_value=float(reference_value),
        measured_value=float(measured_value),
    )


def assessDrift(batch: ReadingBatch, config: DriftConfig) -> DriftReport:
    """Classify each device against its own tolerance, keeping going past the ones it cannot judge.

    A device with no tolerance in the config and a device with fewer readings than the window are
    both reported as skipped rather than guessed at: the first is a config gap someone has to
    close, the second makes the rolling mean a measure of noise rather than of drift.

    Args:
        batch: Readings grouped by device, oldest first within each device.
        config: Window length and per-device tolerance, already parsed.

    Returns:
        One assessment per judged device and one entry per skipped device, both ordered by device
        id, carrying the batch's malformed row count through to the summary.
    """
    assessments: list[DeviceAssessment] = []
    skipped: list[SkippedDevice] = []

    for device_id in sorted(batch.by_device):
        readings = batch.by_device[device_id]
        tolerance = config.tolerance_by_device.get(device_id)
        # One skip path, not one per reason: the two differ in a single token, and mypy still
        # narrows tolerance to float below because the `or` can only be false with both sides false.
        if tolerance is None or len(readings) < config.window:
            reason = SkipReason.NO_TOLERANCE_CONFIGURED if tolerance is None else SkipReason.INSUFFICIENT_READINGS
            skipped.append(SkippedDevice(device_id, reason))
            logEvent(LogLevel.WARNING, 'device_skipped', device_id=device_id, reason=reason.value)
            continue

        mean_error = rollingMeanError(readings, config.window)
        classification = classify(mean_error, tolerance)
        assessments.append(
            DeviceAssessment(
                device_id=device_id,
                reading_count=len(readings),
                mean_error=mean_error,
                tolerance=tolerance,
                classification=classification,
                latest_taken_at=readings[-1].taken_at,
            )
        )

        logEvent(
            severityFor(classification),
            'device_assessed',
            device_id=device_id,
            classification=classification.value,
            mean_error=mean_error,
            tolerance=tolerance,
            window=config.window,
            latest_taken_at=readings[-1].taken_at.isoformat(),
        )

    logEvent(
        LogLevel.INFO,
        'run_complete',
        assessed=len(assessments),
        skipped=len(skipped),
        malformed_rows=batch.malformed_rows,
    )

    return DriftReport(assessments=assessments, skipped=skipped, malformed_rows=batch.malformed_rows)


def rollingMeanError(readings: Sequence[Reading], window: int) -> float:
    # Signed, not absolute: a bias drifting one way is what a calibration check is looking for, and
    # averaging the magnitudes would hide the sign while making pure noise look like drift.
    # fsum, not sum: the errors are small differences of large values, where naive addition loses
    # exactly the digits being measured. Callers pass a non-empty sequence.
    recent = readings[-window:]

    return math.fsum(reading.error for reading in recent) / len(recent)


def classify(mean_error: float, tolerance: float) -> Classification:
    # WARN is a leading indicator, not a smaller failure: the device is still inside tolerance but
    # close enough that the next service visit should recalibrate it before it goes out.
    magnitude = abs(mean_error)

    if magnitude > tolerance:
        return Classification.FAIL
    if magnitude >= tolerance * WARN_FRACTION_OF_TOLERANCE:
        return Classification.WARN
    return Classification.OK


def printReport(report: DriftReport) -> None:
    # One format string for the heading and every row, so a column can only move in both at once.
    ROW_FORMAT = '{:<16}{:>10}{:>14}{:>12}  {}'

    print(ROW_FORMAT.format('device', 'readings', 'mean error', 'tolerance', 'status'))
    for assessment in report.assessments:
        mean_error = f'{assessment.mean_error:+.4f}'
        tolerance = f'{assessment.tolerance:.4f}'
        status = assessment.classification.value

        print(ROW_FORMAT.format(assessment.device_id, assessment.reading_count, mean_error, tolerance, status))

    for skip in report.skipped:
        print(ROW_FORMAT.format(skip.device_id, '-', '-', '-', skip.reason.value))

    counts = Counter(assessment.classification for assessment in report.assessments)
    tallies = ', '.join(f'{classification.value}={counts[classification]}' for classification in Classification)
    print(
        f'{len(report.assessments)} devices assessed: {tallies}; '
        f'{len(report.skipped)} skipped, {report.malformed_rows} malformed rows'
    )


def logEvent(level: LogLevel, event: str, **fields: object) -> None:
    record: dict[str, object] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': level.value,
        'event': event,
    }

    record.update(fields)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Reopened per record: a run killed mid-fleet still leaves a complete, parseable log behind.
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')


def severityFor(classification: Classification) -> LogLevel:
    # A WARN is still inside tolerance, so it is work to schedule; a FAIL is a device whose readings
    # cannot be trusted until someone touches it.
    match classification:
        case Classification.OK:
            return LogLevel.INFO
        case Classification.WARN:
            return LogLevel.WARNING
        case Classification.FAIL:
            return LogLevel.ERROR


### property tests #####################################################################################################

MAX_WINDOW = 8
ERROR_VALUES = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
ERROR_SERIES = st.lists(ERROR_VALUES, min_size=1, max_size=40)
FULL_ERROR_SERIES = st.lists(ERROR_VALUES, min_size=MAX_WINDOW, max_size=40)
WINDOW_SIZES = st.integers(min_value=1, max_value=MAX_WINDOW)


def readingsWithErrors(errors: Sequence[float]) -> list[Reading]:
    # Only the difference matters to the rolling mean, so the reference is fixed and the measured
    # value carries the whole error.
    REFERENCE_VALUE = 100.0
    TAKEN_AT = datetime(2024, 1, 1, tzinfo=timezone.utc)

    return [Reading(DeviceId('DEV-TEST'), TAKEN_AT, REFERENCE_VALUE, REFERENCE_VALUE + error) for error in errors]


@given(errors=ERROR_SERIES, window=WINDOW_SIZES)
def testRollingMeanErrorStaysInsideTheObservedRange(errors: list[float], window: int) -> None:
    # A mean outside the range of its own inputs is the classic sign of the window being taken from
    # the wrong end or of a divisor that does not match the count summed.
    EPSILON = 1e-6

    readings = readingsWithErrors(errors)
    observed = [reading.error for reading in readings[-window:]]

    assert min(observed) - EPSILON <= rollingMeanError(readings, window) <= max(observed) + EPSILON


@given(older=ERROR_SERIES, recent=FULL_ERROR_SERIES, window=WINDOW_SIZES)
def testRollingMeanErrorIgnoresReadingsBeforeTheWindow(older: list[float], recent: list[float], window: int) -> None:
    # The whole point of a rolling window is that history older than it cannot move the answer --
    # otherwise a device that drifted years ago never comes back to OK.
    with_history = rollingMeanError(readingsWithErrors([*older, *recent]), window)

    assert with_history == rollingMeanError(readingsWithErrors(recent), window)


@given(
    magnitude=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    growth=st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    tolerance=st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def testClassificationNeverImprovesAsTheErrorGrows(magnitude: float, growth: float, tolerance: float) -> None:
    # Monotonicity is the invariant that survives any retuning of WARN_FRACTION_OF_TOLERANCE, which
    # asserting the thresholds themselves would not.
    SEVERITY = (Classification.OK, Classification.WARN, Classification.FAIL)

    assert SEVERITY.index(classify(magnitude + growth, tolerance)) >= SEVERITY.index(classify(magnitude, tolerance))


### vocabulary #########################################################################################################

DeviceId = NewType('DeviceId', str)


class LogLevel(Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


class Classification(Enum):
    OK = 'OK'
    WARN = 'WARN'
    FAIL = 'FAIL'


class SkipReason(Enum):
    NO_TOLERANCE_CONFIGURED = 'no_tolerance_configured'
    INSUFFICIENT_READINGS = 'insufficient_readings'


class RowProblem(Enum):
    BAD_DEVICE_ID = 'bad_device_id'
    BAD_TIMESTAMP = 'bad_timestamp'
    BAD_VALUE = 'bad_value'


class ConfigError(RuntimeError):
    """The drift config could not be turned into a usable set of tolerances."""


class DatabaseError(RuntimeError):
    """SQLite refused an operation the run cannot continue without."""


@dataclass(frozen=True)
class Reading:
    device_id: DeviceId
    taken_at: datetime
    reference_value: float
    measured_value: float

    @property
    def error(self) -> float:
        # Signed: positive means the device reads high against the reference.
        return self.measured_value - self.reference_value


@dataclass(frozen=True)
class MalformedRow:
    problem: RowProblem
    detail: str


# Everything downstream of parseRow takes one of these two and nothing else; there is no third state
# where a row is half-checked, and no Reading can exist whose columns were the wrong type.
RowResult = Reading | MalformedRow


@dataclass(frozen=True)
class DriftConfig:
    window: int
    tolerance_by_device: Mapping[DeviceId, float]


@dataclass(frozen=True)
class ReadingBatch:
    by_device: Mapping[DeviceId, Sequence[Reading]]
    malformed_rows: int


@dataclass(frozen=True)
class DeviceAssessment:
    device_id: DeviceId
    reading_count: int
    mean_error: float
    tolerance: float
    classification: Classification
    latest_taken_at: datetime


@dataclass(frozen=True)
class SkippedDevice:
    device_id: DeviceId
    reason: SkipReason


@dataclass(frozen=True)
class DriftReport:
    assessments: Sequence[DeviceAssessment]
    skipped: Sequence[SkippedDevice]
    malformed_rows: int


if __name__ == '__main__':
    sys.exit(main())
