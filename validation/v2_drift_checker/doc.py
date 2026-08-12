from __future__ import annotations

#        (shared inside the org) before this is merged to master.

### IMPORTS ###########################################################################################################
import argparse
import json
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Sequence


### GLOBALS ###########################################################################################################

LOG = logging.getLogger('drift_checker')

DEFAULT_TABLE_NAME = 'calibration_readings'
DEFAULT_WINDOW_SIZE = 10
DEFAULT_TOLERANCE = 1.0
DEFAULT_WARN_FRACTION = 0.8

# sqlite3 cannot bind an identifier (table name) as a query parameter, so it has to be interpolated into the SQL
# text. Rejecting anything that is not a bare identifier is what makes that interpolation safe.
TABLE_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

EXIT_OK = 0
EXIT_DRIFT_DETECTED = 1
EXIT_BAD_INPUT = 2


### TYPES / CLASSES ###################################################################################################

class DriftStatus(Enum):
    OK = 'OK'
    WARN = 'WARN'
    FAIL = 'FAIL'


@dataclass(frozen=True)
class Reading:
    taken_at: str
    reference_value: float
    measured_value: float


    def signedError(self) -> float:
        return self.measured_value - self.reference_value


@dataclass(frozen=True)
class DriftConfig:
    window_size: int
    warn_fraction: float
    default_tolerance: float
    device_tolerances: dict[str, float]


    def toleranceFor(self, device_id: str) -> float:
        return self.device_tolerances.get(device_id, self.default_tolerance)


@dataclass(frozen=True)
class DeviceReport:
    device_id: str
    reading_count: int
    window_size: int
    rolling_mean_error: float
    peak_abs_rolling_error: float
    tolerance: float
    status: DriftStatus
    last_taken_at: str
    partial_window: bool


class JsonlFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'context': record.name,
            'message': record.getMessage(),
        }

        # Traceback text is folded into the same JSON object so that one exception stays one log line
        if record.exc_info is not None:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


### FUNCTIONS #########################################################################################################

def configureLogging(verbose: bool) -> None:
    global LOG

    # Logs go to stderr rather than a jsonl_logs directory: this tool is a CI/cron style check whose stdout is the
    # summary report, so the caller owns log persistence and we never write files next to the database.
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.handlers.clear()
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)
    LOG.propagate = False


def loadConfig(config_path: Path) -> DriftConfig:
    global DEFAULT_TOLERANCE, DEFAULT_WARN_FRACTION, DEFAULT_WINDOW_SIZE

    with config_path.open('r', encoding='utf-8') as config_file:
        raw_config = json.load(config_file)
    if not isinstance(raw_config, dict):
        raise ValueError(f'Config root must be a JSON object: {config_path}')

    window_size = int(raw_config.get('window_size', DEFAULT_WINDOW_SIZE))
    warn_fraction = float(raw_config.get('warn_fraction', DEFAULT_WARN_FRACTION))
    default_tolerance = float(raw_config.get('default_tolerance', DEFAULT_TOLERANCE))
    if window_size < 1:
        raise ValueError(f'window_size must be >= 1, got {window_size}')
    if not 0.0 < warn_fraction <= 1.0:
        raise ValueError(f'warn_fraction must be in (0.0, 1.0], got {warn_fraction}')
    if default_tolerance <= 0.0:
        raise ValueError(f'default_tolerance must be > 0.0, got {default_tolerance}')

    # Per-device entries are objects rather than bare numbers so that future per-device knobs (eg its own window
    # size) can be added without breaking existing config files
    raw_devices = raw_config.get('devices', {})
    if not isinstance(raw_devices, dict):
        raise ValueError(f'Config key "devices" must be a JSON object: {config_path}')
    device_tolerances: dict[str, float] = {}
    for device_id, device_config in raw_devices.items():
        if not isinstance(device_config, dict) or 'tolerance' not in device_config:
            raise ValueError(f'Device "{device_id}" must be an object containing a "tolerance" key')
        tolerance = float(device_config['tolerance'])
        if tolerance <= 0.0:
            raise ValueError(f'Device "{device_id}" tolerance must be > 0.0, got {tolerance}')
        device_tolerances[device_id] = tolerance

    return DriftConfig(
            window_size=window_size,
            warn_fraction=warn_fraction,
            default_tolerance=default_tolerance,
            device_tolerances=device_tolerances,
        )


def readReadingsByDevice(connection: sqlite3.Connection, table_name: str) -> dict[str, list[Reading]]:
    global LOG, TABLE_NAME_PATTERN

    if TABLE_NAME_PATTERN.match(table_name) is None:
        raise ValueError(f'Table name is not a bare SQL identifier: {table_name!r}')

    query = (
        f'SELECT device_id, taken_at, reference_value, measured_value FROM {table_name} '
        'ORDER BY device_id ASC, taken_at ASC'
    )
    readings_by_device: dict[str, list[Reading]] = {}
    skipped_row_count = 0
    for device_id, taken_at, reference_value, measured_value in connection.execute(query):
        # A NULL on either side makes the error undefined; dropping the row is preferred over poisoning the mean
        if reference_value is None or measured_value is None or device_id is None:
            skipped_row_count += 1
            continue
        readings_by_device.setdefault(str(device_id), []).append(Reading(
                taken_at=str(taken_at),
                reference_value=float(reference_value),
                measured_value=float(measured_value),
            ))

    if skipped_row_count > 0:
        LOG.warning(f'Skipped {skipped_row_count} row(s) with a NULL device_id, reference_value or measured_value')
    return readings_by_device


def rollingMeans(errors: Sequence[float], window_size: int) -> list[float]:
    effective_window = min(window_size, len(errors))
    if effective_window < 1:
        return []

    window_sum = sum(errors[:effective_window])
    means = [window_sum / effective_window]
    for index in range(effective_window, len(errors)):
        window_sum += errors[index] - errors[index - effective_window]
        means.append(window_sum / effective_window)
    return means


def buildDeviceReport(device_id: str, readings: Sequence[Reading], config: DriftConfig) -> DeviceReport:
    errors = [reading.signedError() for reading in readings]
    means = rollingMeans(errors, config.window_size)
    if not means:
        raise ValueError(f'Device "{device_id}" has no usable readings')

    # The newest window decides the status; the peak is carried alongside it because a device that drifted out and
    # then wandered back inside tolerance is still worth a human look
    latest_mean = means[-1]
    peak_abs_mean = max(abs(mean) for mean in means)
    tolerance = config.toleranceFor(device_id)
    if abs(latest_mean) > tolerance:
        status = DriftStatus.FAIL
    elif abs(latest_mean) > tolerance * config.warn_fraction:
        status = DriftStatus.WARN
    else:
        status = DriftStatus.OK

    return DeviceReport(
            device_id=device_id,
            reading_count=len(readings),
            window_size=min(config.window_size, len(readings)),
            rolling_mean_error=latest_mean,
            peak_abs_rolling_error=peak_abs_mean,
            tolerance=tolerance,
            status=status,
            last_taken_at=readings[-1].taken_at,
            partial_window=len(readings) < config.window_size,
        )


def checkAllDevices(readings_by_device: dict[str, list[Reading]], config: DriftConfig) -> list[DeviceReport]:
    global LOG

    # A device that is configured but absent from the data is a data pipeline problem, not a drift problem, so it is
    # logged and left out of the summary instead of being scored
    for configured_device in sorted(config.device_tolerances):
        if configured_device not in readings_by_device:
            LOG.warning(f'Configured device "{configured_device}" has no readings in the database')

    reports: list[DeviceReport] = []
    for device_id in sorted(readings_by_device):
        report = buildDeviceReport(device_id, readings_by_device[device_id], config)
        LOG.debug(
            f'{report.device_id}: mean_error={report.rolling_mean_error:+.6f} '
            f'tolerance={report.tolerance:.6f} status={report.status.value}'
        )
        reports.append(report)
    return reports


def formatTextSummary(reports: Sequence[DeviceReport]) -> str:
    header = f'{"DEVICE":<16}{"READINGS":>9}{"WINDOW":>8}{"MEAN ERR":>12}{"PEAK |ERR|":>12}{"TOLERANCE":>11}  STATUS'
    lines = [header, '-' * len(header)]
    for report in reports:
        window_text = f'{report.window_size}*' if report.partial_window else str(report.window_size)
        lines.append(
            f'{report.device_id:<16}{report.reading_count:>9}{window_text:>8}'
            f'{report.rolling_mean_error:>+12.4f}{report.peak_abs_rolling_error:>12.4f}'
            f'{report.tolerance:>11.4f}  {report.status.value}'
        )

    status_counts = {status: 0 for status in DriftStatus}
    for report in reports:
        status_counts[report.status] += 1
    count_text = ', '.join(f'{count} {status.value}' for status, count in status_counts.items())
    lines.append('')
    lines.append(f'{len(reports)} device(s) checked: {count_text}')
    if any(report.partial_window for report in reports):
        lines.append('* window shorter than configured window_size (device has too few readings)')
    return '\n'.join(lines)


def formatJsonlSummary(reports: Sequence[DeviceReport]) -> str:
    lines = []
    for report in reports:
        lines.append(json.dumps({
            'device_id': report.device_id,
            'reading_count': report.reading_count,
            'window_size': report.window_size,
            'partial_window': report.partial_window,
            'rolling_mean_error': round(report.rolling_mean_error, 6),
            'peak_abs_rolling_error': round(report.peak_abs_rolling_error, 6),
            'tolerance': report.tolerance,
            'status': report.status.value,
            'last_taken_at': report.last_taken_at,
        }))
    return '\n'.join(lines)


def parseArgs(argv: Sequence[str] | None = None) -> argparse.Namespace:
    global DEFAULT_TABLE_NAME

    parser = argparse.ArgumentParser(description='Flag calibration devices whose measurement error has drifted.')
    parser.add_argument('database', type=Path, help='Path to the SQLite database of calibration readings')
    parser.add_argument('config', type=Path, help='Path to the JSON tolerance config')
    parser.add_argument('--table', default=DEFAULT_TABLE_NAME, help=f'Readings table (default: {DEFAULT_TABLE_NAME})')
    parser.add_argument('--format', choices=('text', 'jsonl'), default='text', help='Summary format on stdout')
    parser.add_argument('--verbose', action='store_true', help='Emit per-device debug logs on stderr')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    global EXIT_BAD_INPUT, EXIT_DRIFT_DETECTED, EXIT_OK, LOG

    args = parseArgs(argv)
    configureLogging(args.verbose)

    try:
        config = loadConfig(args.config)

        # Opened read-only so a typo in the path fails loudly instead of sqlite3 creating an empty database, and so
        # no journal/WAL files are ever left next to the caller's data
        if not args.database.is_file():
            raise FileNotFoundError(f'Database not found: {args.database}')
        connection = sqlite3.connect(f'file:{args.database}?mode=ro', uri=True)
        try:
            readings_by_device = readReadingsByDevice(connection, args.table)
        finally:
            connection.close()
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as error:
        LOG.error(f'{type(error).__name__}: {error}')
        return EXIT_BAD_INPUT

    # An empty table almost always means the ingest side is broken; passing silently would hide that
    if not readings_by_device:
        LOG.error(f'No usable readings found in table "{args.table}"')
        return EXIT_BAD_INPUT

    reports = checkAllDevices(readings_by_device, config)
    print(formatTextSummary(reports) if args.format == 'text' else formatJsonlSummary(reports))

    failed_devices = [report.device_id for report in reports if report.status is DriftStatus.FAIL]
    if failed_devices:
        LOG.error(f'Drift beyond tolerance on {len(failed_devices)} device(s): {", ".join(failed_devices)}')
        return EXIT_DRIFT_DETECTED
    return EXIT_OK


### MAIN ##############################################################################################################

if __name__ == '__main__':
    sys.exit(main())
