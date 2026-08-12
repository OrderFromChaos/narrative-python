#!/usr/bin/env python3
"""Calibration drift checker.

Reads calibration readings from a SQLite table, computes each device's rolling
mean error over its most recent readings, compares that against a per-device
tolerance loaded from a JSON config, and prints a classified summary.

Error is defined as ``measured_value - reference_value``, so a positive mean
error means the device reads high. Classification uses the *absolute* mean
error against the device's tolerance:

    |mean error| <= tolerance * warn_ratio   -> OK
    |mean error| <= tolerance                -> WARN
    |mean error| >  tolerance                -> FAIL

Exit codes:
    0  every device is OK or WARN
    1  at least one device is FAIL
    2  bad usage, unreadable database, or invalid config

Config format (JSON)::

    {
      "window": 5,              # readings per rolling window (default 5)
      "warn_ratio": 0.8,        # fraction of tolerance that still counts as OK
      "tolerance": 1.0,         # default tolerance for unlisted devices
      "min_readings": 1,        # below this a device cannot be judged
      "devices": {
        "pump-01": {"tolerance": 0.5},
        "pump-02": {"tolerance": 2.0, "min_readings": 3}
      }
    }

``window`` and ``warn_ratio`` are global; ``tolerance`` and ``min_readings``
are defaults that any device may override.

Devices named in ``devices`` are always reported even when the database holds
no usable readings for them; such a device is reported as WARN, never FAIL,
since missing data is an observability problem rather than measured drift.

Usage::

    python base.py readings.db --config config.json [--table readings]
                               [--format text|json] [--window N]
    python base.py --self-test [-v]
"""

from __future__ import annotations

import argparse
import io
import json
import sqlite3
import sys
import tempfile
import unittest  # the tool ships as one file, so its tests live in it (--self-test)
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, replace
from enum import Enum
from functools import partial
from pathlib import Path
from statistics import fmean
from typing import Any, Final, TextIO

__all__ = [
    "Config",
    "DeviceReport",
    "DeviceRule",
    "DriftCheckerError",
    "Status",
    "evaluate",
    "load_config",
    "load_error_samples",
    "main",
]

EXIT_OK: Final = 0
EXIT_FAIL: Final = 1
EXIT_ERROR: Final = 2

DEFAULT_TABLE: Final = "readings"
REQUIRED_COLUMNS: Final = ("device_id", "taken_at", "reference_value", "measured_value")


class DriftCheckerError(Exception):
    """Any condition that should abort the run with a readable message."""


class ConfigError(DriftCheckerError):
    """The config file is missing, malformed, or semantically invalid."""


class DataError(DriftCheckerError):
    """The database cannot supply the readings we need."""


class Status(Enum):
    """Drift classification, ordered from healthy to broken."""

    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"

    @property
    def severity(self) -> int:
        return _SEVERITY[self]


_SEVERITY: Final[dict[Status, int]] = {Status.OK: 0, Status.WARN: 1, Status.FAIL: 2}


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class DeviceRule:
    """Thresholds applied to a single device."""

    tolerance: float
    min_readings: int

    def warn_threshold(self, warn_ratio: float) -> float:
        return self.tolerance * warn_ratio


@dataclass(frozen=True, slots=True)
class Config:
    """Global settings plus per-device threshold overrides."""

    window: int
    warn_ratio: float
    defaults: DeviceRule
    overrides: Mapping[str, DeviceRule]

    def rule_for(self, device_id: str) -> DeviceRule:
        return self.overrides.get(device_id, self.defaults)

    @property
    def named_devices(self) -> tuple[str, ...]:
        return tuple(self.overrides)


_RULE_KEYS: Final = frozenset({"tolerance", "min_readings"})
_TOP_LEVEL_KEYS: Final = _RULE_KEYS | {"window", "warn_ratio", "devices"}


def _positive_number(raw: Any, *, where: str, key: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ConfigError(f"{where}: {key!r} must be a number, got {type(raw).__name__}")
    value = float(raw)
    if value <= 0:
        raise ConfigError(f"{where}: {key!r} must be greater than 0, got {value:g}")
    return value


def _positive_int(raw: Any, *, where: str, key: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ConfigError(f"{where}: {key!r} must be an integer, got {type(raw).__name__}")
    if raw <= 0:
        raise ConfigError(f"{where}: {key!r} must be greater than 0, got {raw}")
    return raw


def _reject_unknown(mapping: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ConfigError(
            f"{where}: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"allowed keys are {', '.join(repr(k) for k in sorted(allowed))}"
        )


def _parse_rule(raw: Mapping[str, Any], base: DeviceRule, where: str) -> DeviceRule:
    _reject_unknown(raw, _RULE_KEYS, where)
    return DeviceRule(
        tolerance=(
            _positive_number(raw["tolerance"], where=where, key="tolerance")
            if "tolerance" in raw
            else base.tolerance
        ),
        min_readings=(
            _positive_int(raw["min_readings"], where=where, key="min_readings")
            if "min_readings" in raw
            else base.min_readings
        ),
    )


def parse_config(raw: Any, source: str = "<config>") -> Config:
    """Validate a decoded config document and build a :class:`Config`."""
    if not isinstance(raw, Mapping):
        raise ConfigError(f"{source}: top level must be an object, got {type(raw).__name__}")
    _reject_unknown(raw, _TOP_LEVEL_KEYS, source)

    seed = DeviceRule(tolerance=1.0, min_readings=1)
    defaults = _parse_rule(
        {key: raw[key] for key in _RULE_KEYS if key in raw}, seed, f"{source}: defaults"
    )

    window = 5
    if "window" in raw:
        window = _positive_int(raw["window"], where=source, key="window")

    warn_ratio = 0.8
    if "warn_ratio" in raw:
        warn_ratio = _positive_number(raw["warn_ratio"], where=source, key="warn_ratio")
        if warn_ratio > 1:
            raise ConfigError(f"{source}: 'warn_ratio' must be <= 1, got {warn_ratio:g}")

    devices_raw = raw.get("devices", {})
    if not isinstance(devices_raw, Mapping):
        raise ConfigError(
            f"{source}: 'devices' must be an object mapping device_id -> settings, "
            f"got {type(devices_raw).__name__}"
        )

    overrides: dict[str, DeviceRule] = {}
    for device_id, device_raw in devices_raw.items():
        where = f"{source}: devices[{device_id!r}]"
        if not isinstance(device_raw, Mapping):
            raise ConfigError(f"{where}: must be an object, got {type(device_raw).__name__}")
        overrides[str(device_id)] = _parse_rule(device_raw, defaults, where)

    return Config(
        window=window, warn_ratio=warn_ratio, defaults=defaults, overrides=overrides
    )


def load_config(path: Path) -> Config:
    """Read and validate a JSON config file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config {path}: {exc.strerror or exc}") from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    return parse_config(document, source=str(path))


# --------------------------------------------------------------------------- #
# Data access
# --------------------------------------------------------------------------- #


def _quote_identifier(name: str) -> str:
    """Quote a SQL identifier. The table name comes from the CLI, not the data."""
    if not name or "\x00" in name:
        raise DataError(f"invalid table name: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def _check_table(conn: sqlite3.Connection, table: str) -> None:
    try:
        rows = conn.execute(f"PRAGMA table_info({_quote_identifier(table)})")
        columns = {row[1] for row in rows}
    except sqlite3.DatabaseError as exc:  # pragma: no cover - corrupt file
        raise DataError(f"cannot inspect table {table!r}: {exc}") from exc
    if not columns:
        raise DataError(f"table {table!r} does not exist in the database")
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise DataError(f"table {table!r} is missing column(s): {', '.join(missing)}")


def load_error_samples(
    conn: sqlite3.Connection, table: str, window: int
) -> dict[str, list[float]]:
    """Return the most recent ``window`` errors per device, newest first.

    Rows whose reference or measured value is NULL or non-numeric are ignored;
    SQLite columns are dynamically typed, so a stray text value would otherwise
    silently coerce to 0.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    _check_table(conn, table)

    sql = f"""
        WITH usable AS (
            SELECT device_id,
                   measured_value - reference_value AS error,
                   ROW_NUMBER() OVER (
                       PARTITION BY device_id
                       ORDER BY taken_at DESC, rowid DESC
                   ) AS recency
            FROM {_quote_identifier(table)}
            WHERE typeof(reference_value) IN ('integer', 'real')
              AND typeof(measured_value) IN ('integer', 'real')
        )
        SELECT device_id, error
        FROM usable
        WHERE recency <= ?
        ORDER BY device_id, recency
    """
    try:
        rows = conn.execute(sql, (window,)).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DataError(f"query against table {table!r} failed: {exc}") from exc

    samples: dict[str, list[float]] = {}
    for device_id, error in rows:
        samples.setdefault(str(device_id), []).append(float(error))
    return samples


def count_unusable_rows(conn: sqlite3.Connection, table: str) -> int:
    """Count rows skipped because a value was NULL or non-numeric."""
    sql = f"""
        SELECT COUNT(*) FROM {_quote_identifier(table)}
        WHERE typeof(reference_value) NOT IN ('integer', 'real')
           OR typeof(measured_value) NOT IN ('integer', 'real')
    """
    try:
        return int(conn.execute(sql).fetchone()[0])
    except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
        raise DataError(f"query against table {table!r} failed: {exc}") from exc


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class DeviceReport:
    """The verdict for one device."""

    device_id: str
    status: Status
    sample_count: int
    mean_error: float | None
    rule: DeviceRule
    window: int
    warn_threshold: float
    note: str = ""

    @property
    def tolerance_used(self) -> float | None:
        """Absolute mean error as a fraction of tolerance."""
        if self.mean_error is None:
            return None
        return abs(self.mean_error) / self.rule.tolerance

    def as_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "sample_count": self.sample_count,
            "mean_error": self.mean_error,
            "tolerance": self.rule.tolerance,
            "warn_threshold": self.warn_threshold,
            "window": self.window,
            "tolerance_used": self.tolerance_used,
            "note": self.note,
        }


def classify(mean_error: float, rule: DeviceRule, warn_ratio: float) -> Status:
    """Classify a mean error against a device's thresholds."""
    magnitude = abs(mean_error)
    if magnitude > rule.tolerance:
        return Status.FAIL
    if magnitude > rule.warn_threshold(warn_ratio):
        return Status.WARN
    return Status.OK


def evaluate(samples: Mapping[str, Sequence[float]], config: Config) -> list[DeviceReport]:
    """Turn per-device error samples into reports, sorted worst-first."""
    device_ids = sorted(set(samples) | set(config.named_devices))
    reports = [
        _evaluate_device(device_id, samples.get(device_id, ()), config)
        for device_id in device_ids
    ]
    reports.sort(key=lambda report: (-report.status.severity, report.device_id))
    return reports


def _evaluate_device(
    device_id: str, all_samples: Sequence[float], config: Config
) -> DeviceReport:
    rule = config.rule_for(device_id)
    recent = list(all_samples[: config.window])
    report = partial(
        DeviceReport,
        device_id=device_id,
        sample_count=len(recent),
        rule=rule,
        window=config.window,
        warn_threshold=rule.warn_threshold(config.warn_ratio),
    )

    if len(recent) < rule.min_readings:
        return report(
            status=Status.WARN,
            mean_error=None,
            note=(
                "no usable readings"
                if not recent
                else f"only {len(recent)} of {rule.min_readings} required readings"
            ),
        )

    mean_error = fmean(recent)
    return report(
        status=classify(mean_error, rule, config.warn_ratio),
        mean_error=mean_error,
        note=(
            ""
            if len(recent) == config.window
            else f"short window ({len(recent)}/{config.window})"
        ),
    )


def tally(reports: Sequence[DeviceReport]) -> dict[Status, int]:
    counts = dict.fromkeys(Status, 0)
    for report in reports:
        counts[report.status] += 1
    return counts


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_HEADERS: Final = ("DEVICE", "STATUS", "N", "MEAN ERROR", "TOLERANCE", "USED", "NOTE")


def _text_rows(reports: Sequence[DeviceReport]) -> Iterator[tuple[str, ...]]:
    for report in reports:
        used = report.tolerance_used
        yield (
            report.device_id,
            report.status.value,
            str(report.sample_count),
            "-" if report.mean_error is None else f"{report.mean_error:+.4f}",
            f"{report.rule.tolerance:.4f}",
            "-" if used is None else f"{used * 100:.0f}%",
            report.note,
        )


def render_text(reports: Sequence[DeviceReport], stream: TextIO) -> None:
    """Print an aligned table followed by a one-line summary."""
    rows = [_HEADERS, *_text_rows(reports)]
    widths = [max(len(row[i]) for row in rows) for i in range(len(_HEADERS))]

    for row in rows:
        # The trailing note column is free-form, so it is not padded.
        cells = [cell.ljust(widths[i]) for i, cell in enumerate(row[:-1])]
        print("  ".join([*cells, row[-1]]).rstrip(), file=stream)

    counts = tally(reports)
    total = len(reports)
    print(
        f"\n{total} device(s): "
        + ", ".join(f"{counts[status]} {status.value}" for status in Status),
        file=stream,
    )


def render_json(reports: Sequence[DeviceReport], stream: TextIO) -> None:
    counts = tally(reports)
    payload = {
        "devices": [report.as_dict() for report in reports],
        "summary": {
            "total": len(reports),
            **{status.value.lower(): counts[status] for status in Status},
        },
    }
    json.dump(payload, stream, indent=2)
    print(file=stream)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drift-checker",
        description="Flag calibration devices whose measurement error has drifted.",
        epilog="Run 'base.py --self-test' to execute the built-in test suite. "
        "Exits 1 if any device is FAIL, 2 on a usage, database, or config error.",
    )
    parser.add_argument("database", type=Path, help="path to the SQLite database")
    parser.add_argument(
        "-c", "--config", type=Path, required=True, help="path to the JSON config file"
    )
    parser.add_argument(
        "-t",
        "--table",
        default=DEFAULT_TABLE,
        help=f"readings table (default: {DEFAULT_TABLE})",
    )
    parser.add_argument(
        "-f", "--format", choices=("text", "json"), default="text", help="output format"
    )
    parser.add_argument(
        "--window",
        type=int,
        help="override the default rolling window size from the config",
    )
    return parser


def _connect(database: Path) -> sqlite3.Connection:
    if not database.exists():
        raise DataError(f"database not found: {database}")
    try:
        # Read-only: this tool must never mutate the readings it audits.
        return sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise DataError(f"cannot open database {database}: {exc}") from exc


def run(args: argparse.Namespace, stdout: TextIO, stderr: TextIO) -> int:
    config = load_config(args.config)
    if args.window is not None:
        if args.window <= 0:
            raise DriftCheckerError(f"--window must be greater than 0, got {args.window}")
        config = replace(config, window=args.window)

    with closing(_connect(args.database)) as conn:
        samples = load_error_samples(conn, args.table, config.window)
        skipped = count_unusable_rows(conn, args.table)

    if skipped:
        print(
            f"warning: ignored {skipped} row(s) with missing or non-numeric values",
            file=stderr,
        )

    reports = evaluate(samples, config)
    if not reports:
        print("warning: no devices found in the database or config", file=stderr)

    if args.format == "json":
        render_json(reports, stdout)
    else:
        render_text(reports, stdout)

    return EXIT_FAIL if any(r.status is Status.FAIL for r in reports) else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Intercepted before argparse so the self test does not need a database
    # argument; the tool ships as one file, so its tests live in it too.
    if argv and argv[0] == "--self-test":
        return _run_self_test(argv[1:])

    args = build_parser().parse_args(argv)
    try:
        return run(args, sys.stdout, sys.stderr)
    except DriftCheckerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:  # pragma: no cover - piping into head, etc.
        return EXIT_ERROR


# --------------------------------------------------------------------------- #
# Self test: python base.py --self-test [-v]
# --------------------------------------------------------------------------- #


def _run_self_test(argv: Sequence[str]) -> int:
    suite = unittest.defaultTestLoader.loadTestsFromName(__name__)
    verbosity = 2 if "-v" in argv else 1
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return EXIT_OK if result.wasSuccessful() else EXIT_FAIL


def _test_config(**overrides: Any) -> Config:
    document = {"tolerance": 1.0, "window": 3, "warn_ratio": 0.8, **overrides}
    return parse_config(document, source="test")


def _memory_db(rows: Sequence[tuple[str, str, Any, Any]]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE readings (device_id TEXT, taken_at TEXT,"
        " reference_value REAL, measured_value REAL)"
    )
    conn.executemany("INSERT INTO readings VALUES (?, ?, ?, ?)", rows)
    return conn


class ClassifyTests(unittest.TestCase):
    RULE = DeviceRule(tolerance=2.0, min_readings=1)

    def test_boundaries_are_inclusive_on_the_healthier_side(self) -> None:
        cases = [
            (1.6, Status.OK),  # exactly the warn threshold
            (1.61, Status.WARN),
            (2.0, Status.WARN),  # exactly the tolerance
            (2.01, Status.FAIL),
        ]
        for magnitude, expected in cases:
            with self.subTest(magnitude=magnitude):
                self.assertIs(classify(magnitude, self.RULE, 0.8), expected)

    def test_sign_is_ignored(self) -> None:
        self.assertIs(classify(-2.5, self.RULE, 0.8), Status.FAIL)
        self.assertIs(classify(-0.5, self.RULE, 0.8), Status.OK)


class ConfigTests(unittest.TestCase):
    def test_devices_inherit_unset_defaults(self) -> None:
        config = _test_config(devices={"a": {"tolerance": 0.5}, "b": {}})
        self.assertEqual(config.rule_for("a"), DeviceRule(0.5, 1))
        self.assertEqual(config.rule_for("b"), config.defaults)
        self.assertEqual(config.rule_for("unlisted"), config.defaults)

    def test_window_is_global(self) -> None:
        self.assertEqual(_test_config(window=9).window, 9)

    def test_rejects_invalid_documents(self) -> None:
        bad = [
            [],
            {"tolerance": 0},
            {"tolerance": "1.0"},
            {"window": 1.5},
            {"warn_ratio": 1.5},
            {"typo": 1},
            {"devices": []},
            {"devices": {"a": 3}},
            {"devices": {"a": {"tolerance": -1}}},
            {"devices": {"a": {"window": 3}}},  # window is global, not per-device
        ]
        for document in bad:
            with self.subTest(document=document):
                with self.assertRaises(ConfigError):
                    parse_config(document, source="test")

    def test_missing_file_is_a_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(Path("/nonexistent/drift-checker-config.json"))


class SampleLoadingTests(unittest.TestCase):
    ROWS = [
        ("a", "2026-01-01", 10.0, 11.0),
        ("a", "2026-01-03", 10.0, 13.0),
        ("a", "2026-01-02", 10.0, 12.0),
        ("b", "2026-01-01", 10.0, None),
        ("b", "2026-01-02", 10.0, "n/a"),
    ]

    def test_returns_newest_first_and_trims_to_window(self) -> None:
        with closing(_memory_db(self.ROWS)) as conn:
            self.assertEqual(load_error_samples(conn, "readings", 2), {"a": [3.0, 2.0]})

    def test_skips_null_and_non_numeric_rows(self) -> None:
        with closing(_memory_db(self.ROWS)) as conn:
            self.assertNotIn("b", load_error_samples(conn, "readings", 5))
            self.assertEqual(count_unusable_rows(conn, "readings"), 2)

    def test_reports_missing_table_and_columns(self) -> None:
        with closing(_memory_db(self.ROWS)) as conn:
            with self.assertRaisesRegex(DataError, "does not exist"):
                load_error_samples(conn, "absent", 5)
            conn.execute("CREATE TABLE partial (device_id TEXT, taken_at TEXT)")
            with self.assertRaisesRegex(DataError, "missing column"):
                load_error_samples(conn, "partial", 5)

    def test_table_name_with_quotes_is_escaped_not_injected(self) -> None:
        with closing(_memory_db(self.ROWS)) as conn:
            with self.assertRaisesRegex(DataError, "does not exist"):
                load_error_samples(conn, 'readings" --', 5)


class EvaluateTests(unittest.TestCase):
    def test_classifies_and_sorts_worst_first(self) -> None:
        config = _test_config(devices={"tight": {"tolerance": 0.1}})
        reports = evaluate({"tight": [1.0, 1.0, 1.0], "loose": [0.0, 0.0, 0.0]}, config)
        self.assertEqual([r.device_id for r in reports], ["tight", "loose"])
        self.assertEqual([r.status for r in reports], [Status.FAIL, Status.OK])
        self.assertAlmostEqual(reports[0].tolerance_used or 0.0, 10.0)

    def test_configured_device_without_data_warns_but_never_fails(self) -> None:
        (report,) = evaluate({}, _test_config(devices={"ghost": {}}))
        self.assertIs(report.status, Status.WARN)
        self.assertIsNone(report.mean_error)
        self.assertEqual(report.note, "no usable readings")

    def test_min_readings_blocks_a_verdict(self) -> None:
        config = _test_config(devices={"a": {"min_readings": 3}})
        (report,) = evaluate({"a": [9.0, 9.0]}, config)
        self.assertIs(report.status, Status.WARN)
        self.assertIn("2 of 3", report.note)

    def test_short_window_still_judged_but_annotated(self) -> None:
        (report,) = evaluate({"a": [0.0]}, _test_config())
        self.assertIs(report.status, Status.OK)
        self.assertEqual(report.note, "short window (1/3)")

    def test_only_the_window_is_averaged(self) -> None:
        # Newest three readings are clean; the older outliers must not count.
        (report,) = evaluate({"a": [0.0, 0.0, 0.0, 50.0, -50.0]}, _test_config())
        self.assertEqual(report.mean_error, 0.0)
        self.assertEqual(report.sample_count, 3)


class WindowOverrideTests(unittest.TestCase):
    def test_cli_override_replaces_the_config_window_only(self) -> None:
        original = _test_config(devices={"a": {"tolerance": 0.5}})
        overridden = replace(original, window=2)
        self.assertEqual(overridden.window, 2)
        self.assertEqual(overridden.overrides, original.overrides)
        self.assertEqual(overridden.warn_ratio, original.warn_ratio)


class EndToEndTests(unittest.TestCase):
    def test_exit_codes_and_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database, config_path = root / "cal.db", root / "config.json"
            with closing(sqlite3.connect(database)) as conn:
                conn.execute(
                    "CREATE TABLE readings (device_id TEXT, taken_at TEXT,"
                    " reference_value REAL, measured_value REAL)"
                )
                conn.executemany(
                    "INSERT INTO readings VALUES (?, ?, ?, ?)",
                    [("drifter", f"2026-01-0{i}", 10.0, 12.0) for i in range(1, 4)]
                    + [("steady", f"2026-01-0{i}", 10.0, 10.0) for i in range(1, 4)],
                )
                conn.commit()
            config_path.write_text(json.dumps({"tolerance": 1.0, "window": 3}))

            args = build_parser().parse_args([str(database), "-c", str(config_path)])
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(run(args, out, err), EXIT_FAIL)
            self.assertIn("drifter", out.getvalue())
            self.assertIn("1 OK, 0 WARN, 1 FAIL", out.getvalue())

            args.format = "json"
            out = io.StringIO()
            run(args, out, err)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["summary"], {"total": 2, "ok": 1, "warn": 0, "fail": 1})
            self.assertEqual(payload["devices"][0]["status"], "FAIL")

    def test_missing_database_exits_with_error_code(self) -> None:
        self.assertEqual(main(["/nonexistent.db", "-c", "/nonexistent.json"]), EXIT_ERROR)


if __name__ == "__main__":
    raise SystemExit(main())
