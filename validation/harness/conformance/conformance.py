#!/usr/bin/env python3
"""Spec-conformance suite for Task V5, the billing reconciler.

Usage:

    python3 conformance.py <arm-directory> <package-name>

The suite drives the program only as a subprocess, through the entry point that
the specification documents:

    python3 -m <package-name> <input-directory>

with the working directory set to the arm directory. The behaviour tests never
import the package, and they assume no module name, function name, class or
file layout. An implementation that reorganises completely still passes.

Each test builds a temporary input directory, runs the program against it, and
asserts on the two artifacts that the specification fixes: the process exit
code, and the content of the JSON report. The human-readable table is not
parsed, because the specification does not fix its format.

Where the specification is silent, this suite does not assert. The file
UNDERSPECIFIED.md, next to this script, lists the questions that were left
untested and quotes the spec text that leaves them open.

Outcomes are PASS, FAIL or SKIP. A SKIP means the suite could not find an
artifact whose location the specification does not fix (the JSON report, or the
SQLite database), or that a best-effort discovery step found nothing. The exit
status is 0 when no test failed, and 1 when one test or more failed.
"""

import argparse
import itertools
import json
import os
import random
import re
import shutil
import sqlite3
import string
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

KINDS: tuple[str, ...] = ("billed_not_found", "found_not_billed", "region_mismatch")
RUN_TIMEOUT_SECONDS: int = 120
REPORT_FLAGS: tuple[str, ...] = ("--report", "--json-report", "--report-path", "--output")
SQLITE_MAGIC: bytes = b"SQLite format 3\x00"
RESULT_MARKER: str = "###CONFORMANCE-RESULT###"
IGNORED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
    }
)

TESTS: list[tuple[str, Callable[["Harness"], None]]] = []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="conformance.py",
        description=(
            "Run the Task V5 billing-reconciler spec-conformance suite against one "
            "implementation. The implementation is driven only as a subprocess, "
            "through 'python3 -m <package> <input-dir>' with the working directory "
            "set to the arm directory."
        ),
        epilog=(
            "Outcomes are PASS, FAIL and SKIP. The exit status is 0 when no test "
            "failed. See UNDERSPECIFIED.md for the questions this suite does not ask."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("arm", nargs="?", help="directory that contains the package to test")
    parser.add_argument("package", nargs="?", help="importable package name, as used by 'python3 -m'")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="NAME",
        help="run only the named test. Repeatable.",
    )
    parser.add_argument("--list", action="store_true", help="print the test names and exit")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="print the command line, exit code, stdout and stderr of every failed run",
    )
    args = parser.parse_args(argv)

    if args.list:
        for name, _ in TESTS:
            print(name)
        return 0

    if not args.arm or not args.package:
        parser.error("both <arm-directory> and <package-name> are required")

    armDir = Path(args.arm).expanduser().resolve()
    if not armDir.is_dir():
        print(f"error: arm directory not found: {armDir}", file=sys.stderr)
        return 1

    selected = [entry for entry in TESTS if not args.only or entry[0] in set(args.only)]
    if not selected:
        print(f"error: no test matched {args.only}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="v5-conformance-") as tempRoot:
        harness = Harness(armDir=armDir, package=args.package, tempRoot=Path(tempRoot), verbose=args.verbose)
        try:
            problem = harness.preflight()
            if problem:
                print(f"error: {problem}", file=sys.stderr)
                return 1
            harness.probe()
            outcomes = [harness.execute(name, body) for name, body in selected]
        finally:
            harness.restoreArmRules()

    return summarise(outcomes, harness)


# ---------------------------------------------------------------------------
# result types
# ---------------------------------------------------------------------------


class TestFailure(Exception):
    """A conformance requirement was not met."""


class TestSkipped(Exception):
    """The suite could not obtain an artifact whose location the spec leaves open."""


@dataclass(slots=True)
class RunResult:
    argv: list[str]
    exitCode: int
    stdout: str
    stderr: str
    report: Any | None
    reportPath: Path | None
    changedFiles: list[Path]

    def combinedOutput(self) -> str:
        return self.stdout + "\n" + self.stderr

    def describe(self) -> str:
        lines = [
            "    argv: " + " ".join(self.argv),
            f"    exit: {self.exitCode}",
            f"    report: {self.reportPath}",
            "    stdout: " + tail(self.stdout),
            "    stderr: " + tail(self.stderr),
        ]
        return "\n".join(lines)


@dataclass(slots=True)
class Finding:
    kind: str
    record: Any


@dataclass(slots=True)
class Outcome:
    name: str
    status: str
    reason: str = ""
    detail: str = ""


# ---------------------------------------------------------------------------
# JSON report reading
# ---------------------------------------------------------------------------


def normaliseToken(text: str) -> str:
    """Fold a label to snake_case, so 'billedNotFound' and 'BILLED-NOT-FOUND' agree.

    The spec names the three mismatch kinds but does not fix their spelling in
    the report, so the reader accepts the usual spellings of the same name.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    return re.sub(r"[^a-z0-9]+", "_", spaced.lower()).strip("_")


def kindOfRecord(record: dict[str, Any]) -> str | None:
    for value in record.values():
        if isinstance(value, str) and normaliseToken(value) in KINDS:
            return normaliseToken(value)
    return None


def collectFindings(node: Any, out: list[Finding]) -> None:
    if isinstance(node, dict):
        kind = kindOfRecord(node)
        if kind is not None:
            out.append(Finding(kind=kind, record=node))
            return
        for key, value in node.items():
            keyKind = normaliseToken(str(key))
            if keyKind in KINDS and isinstance(value, list):
                for item in value:
                    out.append(Finding(kind=keyKind, record=item))
            elif keyKind in KINDS and isinstance(value, dict) and value and all(
                isinstance(item, dict) for item in value.values()
            ):
                # a kind mapped to records keyed by resource id
                for subKey, subValue in value.items():
                    out.append(Finding(kind=keyKind, record={subKey: subValue}))
            else:
                collectFindings(value, out)
    elif isinstance(node, list):
        for item in node:
            collectFindings(item, out)


def extractFindings(report: Any) -> list[Finding]:
    """Pull finding records out of a report whose schema the spec does not fix.

    Two shapes are understood, in document order: a record that carries one of
    the three kind names as a value, and a mapping from a kind name to a list of
    records. Exact duplicates are dropped.
    """
    collected: list[Finding] = []
    collectFindings(report, collected)
    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []
    for finding in collected:
        key = (finding.kind, json.dumps(finding.record, sort_keys=True, default=repr))
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def leaves(node: Any) -> Iterator[Any]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from leaves(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from leaves(item)
    else:
        yield node


def recordMentions(record: Any, token: str) -> bool:
    for leaf in leaves(record):
        text = str(leaf)
        if text == token or token in text:
            return True
    return False


def findingsOfKind(findings: list[Finding], kind: str) -> list[Finding]:
    return [finding for finding in findings if finding.kind == kind]


def kindsMentioning(findings: list[Finding], token: str) -> list[str]:
    return [finding.kind for finding in findings if recordMentions(finding.record, token)]


def orderedIdsForKind(findings: list[Finding], kind: str, knownIds: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for finding in findingsOfKind(findings, kind):
        for identifier in knownIds:
            if recordMentions(finding.record, identifier):
                if identifier not in seen:
                    seen.add(identifier)
                    ordered.append(identifier)
                break
    return ordered


# ---------------------------------------------------------------------------
# file-system helpers
# ---------------------------------------------------------------------------


def snapshot(roots: list[Path]) -> dict[Path, tuple[int, int]]:
    state: dict[Path, tuple[int, int]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if any(part in IGNORED_DIR_NAMES for part in path.parts):
                continue
            try:
                if not path.is_file():
                    continue
                stat = path.stat()
            except OSError:
                continue
            state[path] = (stat.st_mtime_ns, stat.st_size)
    return state


def changedSince(before: dict[Path, tuple[int, int]], after: dict[Path, tuple[int, int]]) -> list[Path]:
    return sorted(path for path, value in after.items() if before.get(path) != value)


def readJson(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


def isSqliteFile(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(16) == SQLITE_MAGIC
    except OSError:
        return False


def tail(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if not text:
        return "<empty>"
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


def childEnv() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("PYTHONSTARTUP", None)
    return env


def randomToken(length: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------


@dataclass
class Harness:
    armDir: Path
    package: str
    tempRoot: Path
    verbose: bool = False
    reportFlag: str | None = None
    reportDiscovery: bool = False
    findingsExtractable: bool | None = None
    rulesPlacement: str = "input"
    probeNotes: list[str] = field(default_factory=list)
    counter: Iterator[int] = field(default_factory=lambda: itertools.count(1))
    armRulesBackedUp: bool = False
    armRulesOriginal: bytes | None = None

    # -- fixtures ----------------------------------------------------------

    def newInputDir(self, label: str) -> Path:
        path = self.tempRoot / f"in-{label}-{next(self.counter)}"
        path.mkdir(parents=True)
        return path

    def writeBilling(self, inputDir: Path, filename: str, rows: list[tuple[str, str, int, str]]) -> Path:
        lines = ["resource_id,sku,monthly_cents,region"]
        for resourceId, sku, cents, region in rows:
            lines.append(f"{resourceId},{sku},{cents},{region}")
        path = inputDir / filename
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def writeScan(
        self,
        inputDir: Path,
        filename: str,
        resources: list[tuple[str, str, str, str]],
        scannedAt: str = "2026-01-15T00:00:00Z",
    ) -> Path:
        payload = {
            "scanned_at": scannedAt,
            "resources": [
                {"id": resourceId, "sku": sku, "team": team, "region": region}
                for resourceId, sku, team, region in resources
            ],
        }
        path = inputDir / filename
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def writeRules(
        self,
        inputDir: Path,
        ignoredSkus: list[str] | None = None,
        regionAliases: dict[str, str] | None = None,
        graceCents: int = 500,
    ) -> Path:
        payload = {
            "ignored_skus": list(ignoredSkus if ignoredSkus is not None else ["support-plan"]),
            "region_aliases": dict(regionAliases if regionAliases is not None else {"us-east-1": "use1"}),
            "grace_cents": graceCents,
        }
        text = json.dumps(payload, indent=2) + "\n"
        path = inputDir / "reconcile.json"
        path.write_text(text, encoding="utf-8")
        if self.rulesPlacement == "both":
            self.installArmRules(text)
        return path

    def writeRaw(self, inputDir: Path, filename: str, text: str) -> Path:
        path = inputDir / filename
        path.write_text(text, encoding="utf-8")
        return path

    def installArmRules(self, text: str) -> None:
        target = self.armDir / "reconcile.json"
        if not self.armRulesBackedUp:
            self.armRulesBackedUp = True
            self.armRulesOriginal = target.read_bytes() if target.exists() else None
        target.write_text(text, encoding="utf-8")

    def restoreArmRules(self) -> None:
        if not self.armRulesBackedUp:
            return
        target = self.armDir / "reconcile.json"
        if self.armRulesOriginal is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(self.armRulesOriginal)
        self.armRulesBackedUp = False
        self.armRulesOriginal = None

    # -- running -----------------------------------------------------------

    def invoke(self, inputDir: Path, reportFlag: str | None, extraArgs: tuple[str, ...] = ()) -> RunResult:
        roots = [self.armDir, inputDir]
        before = snapshot(roots)
        argv = [sys.executable, "-m", self.package, str(inputDir)]
        reportTarget: Path | None = None
        if reportFlag:
            reportTarget = self.tempRoot / f"report-{next(self.counter)}.json"
            argv += [reportFlag, str(reportTarget)]
        argv += list(extraArgs)
        try:
            completed = subprocess.run(
                argv,
                cwd=str(self.armDir),
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
                env=childEnv(),
            )
        except subprocess.TimeoutExpired as exc:
            raise TestFailure(f"the program did not finish within {RUN_TIMEOUT_SECONDS}s: {' '.join(argv)}") from exc
        after = snapshot(roots)
        changed = changedSince(before, after)
        report, reportPath = self.locateReport(reportTarget, changed)
        return RunResult(
            argv=argv,
            exitCode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            report=report,
            reportPath=reportPath,
            changedFiles=changed,
        )

    def run(self, inputDir: Path, extraArgs: tuple[str, ...] = ()) -> RunResult:
        return self.invoke(inputDir, self.reportFlag, extraArgs)

    def locateReport(self, reportTarget: Path | None, changed: list[Path]) -> tuple[Any | None, Path | None]:
        if reportTarget is not None and reportTarget.is_file():
            parsed = readJson(reportTarget)
            if parsed is not None:
                return parsed, reportTarget
        best: tuple[int, int, Path, Any] | None = None
        for path in changed:
            if path.suffix.lower() != ".json":
                continue
            if path.name == "reconcile.json":
                continue
            parsed = readJson(path)
            if parsed is None:
                continue
            score = 2 if extractFindings(parsed) else 1
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                mtime = 0
            if best is None or (score, mtime) > (best[0], best[1]):
                best = (score, mtime, path, parsed)
        if best is None:
            return None, None
        return best[3], best[2]

    # -- requirements on artifacts the spec does not locate -----------------

    def requireReport(self, result: RunResult) -> Any:
        if result.report is None:
            raise TestSkipped(
                "no JSON report was found. The spec says 'write a JSON report' but does not "
                "name it or say where it goes, and no --report style flag was accepted"
            )
        return result.report

    def requireFindings(self, result: RunResult) -> list[Finding]:
        report = self.requireReport(result)
        if self.findingsExtractable is False:
            raise TestSkipped(
                "the JSON report was found but no finding records could be read from it. "
                "The spec does not fix the report schema"
            )
        return extractFindings(report)

    # -- probing -----------------------------------------------------------

    def preflight(self) -> str | None:
        """Check that 'python3 -m <package> <input-dir>' starts at all."""
        inputDir = self.probeFixture("preflight")
        try:
            result = self.invoke(inputDir, None)
        except TestFailure as exc:
            return str(exc)
        root = self.package.split(".")[0]
        missing = ("No module named " + root) in result.stderr or ("No module named " + repr(root)) in result.stderr
        if missing:
            return (
                f"'{sys.executable} -m {self.package}' cannot find the package with the working "
                f"directory set to {self.armDir}:\n{tail(result.stderr)}"
            )
        return None

    def probe(self) -> None:
        try:
            self.probeReportAccess()
            self.probeRulesPlacement()
        except Exception as exc:  # a probe failure must not look like a spec violation
            self.probeNotes.append(f"probing stopped early: {exc!r}")

    def probeFixture(self, label: str) -> Path:
        inputDir = self.newInputDir(label)
        self.writeBilling(inputDir, "probe.billing.csv", [("probe-billed-only", "vm-small", 9000, "us-east-1")])
        self.writeScan(inputDir, "probe.scan.json", [("probe-scan-only", "vm-small", "core", "us-east-1")])
        self.writeRules(inputDir)
        return inputDir

    def probeReportAccess(self) -> None:
        for flag in REPORT_FLAGS:
            inputDir = self.probeFixture("probe-flag")
            try:
                result = self.invoke(inputDir, flag)
            except TestFailure:
                continue
            if result.reportPath is not None and result.reportPath.parent == self.tempRoot:
                self.reportFlag = flag
                self.findingsExtractable = bool(extractFindings(result.report))
                self.probeNotes.append(f"report obtained through the '{flag}' flag")
                if not self.findingsExtractable:
                    self.probeNotes.append("no finding records could be read from the probe report")
                return
        inputDir = self.probeFixture("probe-discovery")
        try:
            result = self.invoke(inputDir, None)
        except TestFailure:
            result = None  # type: ignore[assignment]
        if result is not None and result.report is not None:
            self.reportDiscovery = True
            self.findingsExtractable = bool(extractFindings(result.report))
            self.probeNotes.append(f"report discovered as a written JSON file: {result.reportPath}")
            if not self.findingsExtractable:
                self.probeNotes.append("no finding records could be read from the probe report")
            return
        self.probeNotes.append("no JSON report could be located; report-content tests will be skipped")

    def probeRulesPlacement(self) -> None:
        """Find out where this implementation expects reconcile.json.

        The spec names the rules file but does not say whether it sits in the
        input directory or beside the program. The probe puts it in the input
        directory first, which is the reading that 'read from the input
        directory' supports, and falls back to also placing a copy in the arm
        directory.
        """
        marker = "probe-ignored-sku"

        def ignoredSkuWasApplied() -> bool | None:
            inputDir = self.newInputDir("probe-rules")
            self.writeBilling(inputDir, "probe.billing.csv", [(marker, "support-plan", 9000, "us-east-1")])
            self.writeScan(inputDir, "probe.scan.json", [("probe-rules-scan", "vm-small", "core", "us-east-1")])
            self.writeRules(inputDir)
            try:
                result = self.run(inputDir)
            except TestFailure:
                return None
            if result.report is None:
                return None
            findings = extractFindings(result.report)
            if not findings:
                return None
            return not kindsMentioning(findings, marker)

        applied = ignoredSkuWasApplied()
        if applied is not False:
            self.probeNotes.append("reconcile.json placed in the input directory")
            return
        self.rulesPlacement = "both"
        applied = ignoredSkuWasApplied()
        if applied:
            self.probeNotes.append("reconcile.json placed in the input directory and in the arm directory")
            return
        self.rulesPlacement = "input"
        self.restoreArmRules()
        self.probeNotes.append(
            "reconcile.json placed in the input directory; the ignored_skus probe had no effect in either placement"
        )

    # -- execution ---------------------------------------------------------

    def execute(self, name: str, body: Callable[["Harness"], None]) -> Outcome:
        try:
            body(self)
        except TestSkipped as exc:
            outcome = Outcome(name=name, status="SKIP", reason=str(exc))
        except TestFailure as exc:
            outcome = Outcome(name=name, status="FAIL", reason=str(exc), detail=getattr(exc, "detail", ""))
        except Exception as exc:  # a harness bug should not look like a spec violation
            outcome = Outcome(name=name, status="FAIL", reason=f"harness error: {exc!r}")
        else:
            outcome = Outcome(name=name, status="PASS")
        line = f"{outcome.status}  {outcome.name}"
        if outcome.reason:
            line += f": {outcome.reason}"
        print(line, flush=True)
        if self.verbose and outcome.detail:
            print(outcome.detail, flush=True)
        return outcome


def summarise(outcomes: list[Outcome], harness: Harness) -> int:
    passed = sum(1 for outcome in outcomes if outcome.status == "PASS")
    skipped = sum(1 for outcome in outcomes if outcome.status == "SKIP")
    failed = sum(1 for outcome in outcomes if outcome.status == "FAIL")
    print("")
    for note in harness.probeNotes:
        print(f"note: {note}")
    print(f"{passed} of {len(outcomes)} passed" + (f" ({skipped} skipped)" if skipped else ""))
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# assertion helpers
# ---------------------------------------------------------------------------


def fail(message: str, result: RunResult | None = None) -> None:
    error = TestFailure(message)
    if result is not None:
        error.detail = result.describe()  # type: ignore[attr-defined]
    raise error


def requireKind(findings: list[Finding], token: str, kind: str, result: RunResult) -> None:
    kinds = kindsMentioning(findings, token)
    if kind not in kinds:
        fail(
            f"expected a {kind} finding for {token}; findings for it were {kinds or 'none'} "
            f"({len(findings)} findings in the report)",
            result,
        )


def requireNoFinding(findings: list[Finding], token: str, result: RunResult) -> None:
    kinds = kindsMentioning(findings, token)
    if kinds:
        fail(f"expected no finding for {token}, but the report has {kinds}", result)


def requireExit(result: RunResult, expected: str) -> None:
    if expected == "zero" and result.exitCode != 0:
        fail(f"expected exit code 0, got {result.exitCode}", result)
    if expected == "nonzero" and result.exitCode == 0:
        fail("expected a non-zero exit code, got 0", result)


def conformanceTest(name: str) -> Callable[[Callable[[Harness], None]], Callable[[Harness], None]]:
    def register(body: Callable[[Harness], None]) -> Callable[[Harness], None]:
        TESTS.append((name, body))
        return body

    return register


# ---------------------------------------------------------------------------
# tests: requirement 1, both formats and every file
# ---------------------------------------------------------------------------


@conformanceTest("both_formats_are_read")
def testBothFormatsAreRead(harness: Harness) -> None:
    """Spec 1 and Inputs: both '*.billing.csv' and '*.scan.json' must be read."""
    inputDir = harness.newInputDir("formats")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t01-bill-only", "vm-small", 1200, "us-east-1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t01-scan-only", "vm-small", "core", "us-east-1")])
    harness.writeRules(inputDir)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t01-bill-only", "billed_not_found", result)
    requireKind(findings, "t01-scan-only", "found_not_billed", result)


@conformanceTest("every_file_in_the_directory_is_read")
def testEveryFileIsRead(harness: Harness) -> None:
    """Spec 1: 'Read every inventory file in an input directory'."""
    inputDir = harness.newInputDir("many-files")
    harness.writeBilling(inputDir, "one.billing.csv", [("t02-bill-one", "vm-small", 2000, "us-east-1")])
    harness.writeBilling(inputDir, "two.billing.csv", [("t02-bill-two", "vm-small", 3000, "us-east-1")])
    harness.writeScan(inputDir, "one.scan.json", [("t02-scan-one", "vm-small", "core", "us-east-1")])
    harness.writeScan(inputDir, "two.scan.json", [("t02-scan-two", "vm-small", "core", "us-east-1")])
    harness.writeRules(inputDir, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t02-bill-one", "billed_not_found", result)
    requireKind(findings, "t02-bill-two", "billed_not_found", result)
    requireKind(findings, "t02-scan-one", "found_not_billed", result)
    requireKind(findings, "t02-scan-two", "found_not_billed", result)


# ---------------------------------------------------------------------------
# tests: requirements 2 and 3, the join and the three finding kinds
# ---------------------------------------------------------------------------


@conformanceTest("matched_pair_produces_no_finding")
def testMatchedPairIsSilent(harness: Harness) -> None:
    """Spec 2 and 3: a resource on both sides, with the same region, is not a mismatch."""
    inputDir = harness.newInputDir("join")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [("t03-match", "vm-small", 1500, "us-east-1"), ("t03-decoy", "vm-small", 1500, "us-east-1")],
    )
    harness.writeScan(inputDir, "assets.scan.json", [("t03-match", "vm-small", "core", "us-east-1")])
    harness.writeRules(inputDir, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t03-decoy", "billed_not_found", result)
    requireNoFinding(findings, "t03-match", result)


@conformanceTest("billed_not_found_is_reported")
def testBilledNotFound(harness: Harness) -> None:
    """Spec 3: 'a billing line with no scanned resource'."""
    inputDir = harness.newInputDir("bnf")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [("t04-bnf", "vm-large", 9000, "us-east-1"), ("t04-pair", "vm-small", 100, "us-east-1")],
    )
    harness.writeScan(inputDir, "assets.scan.json", [("t04-pair", "vm-small", "core", "us-east-1")])
    harness.writeRules(inputDir, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t04-bnf", "billed_not_found", result)


@conformanceTest("found_not_billed_is_reported")
def testFoundNotBilled(harness: Harness) -> None:
    """Spec 3: 'a scanned resource with no billing line'."""
    inputDir = harness.newInputDir("fnb")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t05-pair", "vm-small", 100, "us-east-1")])
    harness.writeScan(
        inputDir,
        "assets.scan.json",
        [("t05-pair", "vm-small", "core", "us-east-1"), ("t05-fnb", "vm-small", "core", "us-east-1")],
    )
    harness.writeRules(inputDir, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t05-fnb", "found_not_billed", result)


@conformanceTest("region_mismatch_is_reported")
def testRegionMismatch(harness: Harness) -> None:
    """Spec 3: 'both sides matched, but the regions differ after region_aliases is applied'."""
    inputDir = harness.newInputDir("region")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t06-rm", "vm-small", 700, "us-east-1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t06-rm", "vm-small", "core", "eu-west-1")])
    harness.writeRules(inputDir, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t06-rm", "region_mismatch", result)
    kinds = set(kindsMentioning(findings, "t06-rm"))
    unmatchedKinds = kinds & {"billed_not_found", "found_not_billed"}
    if unmatchedKinds:
        fail(
            f"t06-rm is on both sides, so it is matched, yet it is also reported as {sorted(unmatchedKinds)}",
            result,
        )


@conformanceTest("ignored_skus_removed_from_the_join")
def testIgnoredSkus(harness: Harness) -> None:
    """Spec 2: an ignored sku 'takes part in no join and appears in no finding'."""
    inputDir = harness.newInputDir("ignored")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [
            ("t07-ign-bill", "support-plan", 9000, "us-east-1"),
            ("t07-ign-pair", "support-plan", 4000, "us-east-1"),
            ("t07-visible", "vm-small", 3000, "us-east-1"),
        ],
    )
    harness.writeScan(
        inputDir,
        "assets.scan.json",
        [
            ("t07-ign-scan", "support-plan", "core", "us-east-1"),
            ("t07-ign-pair", "support-plan", "core", "eu-west-1"),
        ],
    )
    harness.writeRules(inputDir, ignoredSkus=["support-plan"], graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t07-visible", "billed_not_found", result)
    requireNoFinding(findings, "t07-ign-bill", result)
    requireNoFinding(findings, "t07-ign-scan", result)
    requireNoFinding(findings, "t07-ign-pair", result)


@conformanceTest("region_alias_long_to_short")
def testRegionAliasForward(harness: Harness) -> None:
    """Spec 3 and Notes: 'us-east-1' billed against 'use1' scanned is not a mismatch."""
    inputDir = harness.newInputDir("alias-fwd")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [("t08-alias", "vm-small", 600, "us-east-1"), ("t08-differs", "vm-small", 600, "us-east-1")],
    )
    harness.writeScan(
        inputDir,
        "assets.scan.json",
        [("t08-alias", "vm-small", "core", "use1"), ("t08-differs", "vm-small", "core", "eu-west-1")],
    )
    harness.writeRules(inputDir, regionAliases={"us-east-1": "use1"}, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t08-differs", "region_mismatch", result)
    requireNoFinding(findings, "t08-alias", result)


@conformanceTest("region_alias_short_to_long")
def testRegionAliasReverse(harness: Harness) -> None:
    """Notes: 'The mapping is not symmetric in the file, and both directions must compare equal'."""
    inputDir = harness.newInputDir("alias-rev")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [("t09-alias", "vm-small", 600, "use1"), ("t09-differs", "vm-small", 600, "use1")],
    )
    harness.writeScan(
        inputDir,
        "assets.scan.json",
        [("t09-alias", "vm-small", "core", "us-east-1"), ("t09-differs", "vm-small", "core", "eu-west-1")],
    )
    harness.writeRules(inputDir, regionAliases={"us-east-1": "use1"}, graceCents=100000)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t09-differs", "region_mismatch", result)
    requireNoFinding(findings, "t09-alias", result)


# ---------------------------------------------------------------------------
# tests: requirement 4, ranking and the grace boundary
# ---------------------------------------------------------------------------


@conformanceTest("billed_not_found_ranked_by_cost")
def testRanking(harness: Harness) -> None:
    """Spec 4: 'Rank billed_not_found by monthly_cents, largest first'."""
    inputDir = harness.newInputDir("rank")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [
            ("t10-low", "vm-small", 100, "use1"),
            ("t10-high", "vm-huge", 9000, "use1"),
            ("t10-mid", "vm-med", 4200, "use1"),
            ("t10-tiny", "vm-nano", 10, "use1"),
        ],
    )
    harness.writeScan(inputDir, "assets.scan.json", [("t10-scan", "vm-small", "core", "use1")])
    harness.writeRules(inputDir, graceCents=0)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    expected = ["t10-high", "t10-mid", "t10-low", "t10-tiny"]
    observed = orderedIdsForKind(findings, "billed_not_found", expected)
    if sorted(observed) != sorted(expected):
        fail(f"expected billed_not_found findings for {expected}, saw {observed}", result)
    if observed != expected:
        fail(
            f"billed_not_found order in the JSON report was {observed}, expected {expected} "
            "(9000, 4200, 100, 10 cents). The spec does not say which artifact carries the rank",
            result,
        )


@conformanceTest("grace_boundary_cost_equal_to_grace")
def testGraceEqual(harness: Harness) -> None:
    """Spec 4 and 8: 'at or below grace_cents is recorded but does not affect the exit code'."""
    inputDir = harness.newInputDir("grace-eq")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t11-equal", "vm-small", 500, "use1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t11-scan", "vm-small", "core", "use1")])
    harness.writeRules(inputDir, graceCents=500)
    result = harness.run(inputDir)
    requireExit(result, "zero")
    findings = harness.requireFindings(result)
    requireKind(findings, "t11-equal", "billed_not_found", result)


@conformanceTest("grace_boundary_one_cent_below_grace")
def testGraceBelow(harness: Harness) -> None:
    """Spec 4 and 8: one cent below the grace is recorded and does not change the exit code."""
    inputDir = harness.newInputDir("grace-below")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t12-below", "vm-small", 499, "use1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t12-scan", "vm-small", "core", "use1")])
    harness.writeRules(inputDir, graceCents=500)
    result = harness.run(inputDir)
    requireExit(result, "zero")
    findings = harness.requireFindings(result)
    requireKind(findings, "t12-below", "billed_not_found", result)


@conformanceTest("grace_boundary_one_cent_above_grace")
def testGraceAbove(harness: Harness) -> None:
    """Spec 8: 'Exit non-zero when any billed_not_found finding is above grace_cents'."""
    inputDir = harness.newInputDir("grace-above")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t13-above", "vm-small", 501, "use1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t13-scan", "vm-small", "core", "use1")])
    harness.writeRules(inputDir, graceCents=500)
    result = harness.run(inputDir)
    requireExit(result, "nonzero")
    findings = harness.requireFindings(result)
    requireKind(findings, "t13-above", "billed_not_found", result)


@conformanceTest("exit_zero_without_a_billed_not_found_above_grace")
def testExitZero(harness: Harness) -> None:
    """Spec 8: the other two kinds do not make the exit code non-zero."""
    inputDir = harness.newInputDir("exit-zero")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t14-rm", "vm-small", 700, "us-east-1")])
    harness.writeScan(
        inputDir,
        "assets.scan.json",
        [("t14-rm", "vm-small", "core", "eu-west-1"), ("t14-fnb", "vm-small", "core", "us-east-1")],
    )
    harness.writeRules(inputDir, graceCents=500)
    result = harness.run(inputDir)
    requireExit(result, "zero")
    findings = harness.requireFindings(result)
    requireKind(findings, "t14-rm", "region_mismatch", result)
    requireKind(findings, "t14-fnb", "found_not_billed", result)


# ---------------------------------------------------------------------------
# tests: requirement 5, the SQLite store
# ---------------------------------------------------------------------------


def sqliteRowsMentioning(dbPath: Path, token: str, workDir: Path) -> int:
    """Count rows in every user table whose text mentions the token.

    The spec fixes no table name or schema, so the count is taken over every
    table and restricted to the rows that name this run's fixture resources.
    """
    copyPath = workDir / f"{dbPath.name}.{randomToken()}.copy"
    try:
        shutil.copy2(dbPath, copyPath)
        for suffix in ("-wal", "-shm"):
            sidecar = dbPath.with_name(dbPath.name + suffix)
            if sidecar.exists():
                shutil.copy2(sidecar, copyPath.with_name(copyPath.name + suffix))
    except OSError as exc:
        raise TestSkipped(f"the SQLite database at {dbPath} could not be copied for reading: {exc}") from exc
    try:
        connection = sqlite3.connect(str(copyPath))
    except sqlite3.Error as exc:
        raise TestSkipped(f"the SQLite database at {dbPath} could not be opened: {exc}") from exc
    try:
        tables = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            if not str(row[0]).startswith("sqlite_")
        ]
        total = 0
        for table in tables:
            try:
                rows = connection.execute(f'SELECT * FROM "{table}"').fetchall()
            except sqlite3.DatabaseError:
                continue
            for row in rows:
                if any(token in str(cell) for cell in row):
                    total += 1
        return total
    except sqlite3.DatabaseError as exc:
        raise TestSkipped(f"the SQLite database at {dbPath} could not be read: {exc}") from exc
    finally:
        connection.close()


@conformanceTest("sqlite_rerun_over_unchanged_input_adds_no_row")
def testSqliteIdempotence(harness: Harness) -> None:
    """Spec 5: 'keyed so a re-run over unchanged inputs does not double-insert'."""
    token = randomToken()
    inputDir = harness.newInputDir("sqlite")
    harness.writeBilling(
        inputDir,
        "finance.billing.csv",
        [(f"t15-{token}-bnf", "vm-small", 100, "us-east-1"), (f"t15-{token}-rm", "vm-small", 100, "us-east-1")],
    )
    harness.writeScan(
        inputDir,
        "assets.scan.json",
        [
            (f"t15-{token}-rm", "vm-small", "core", "eu-west-1"),
            (f"t15-{token}-fnb", "vm-small", "core", "us-east-1"),
        ],
    )
    harness.writeRules(inputDir, graceCents=100000)

    firstRun = harness.run(inputDir)
    databases = [path for path in firstRun.changedFiles if isSqliteFile(path)]
    if not databases:
        raise TestSkipped(
            "no SQLite database was written or changed by the run. The spec says 'Record every "
            "finding in SQLite' but does not name the file or say where it goes"
        )
    afterFirst = {path: sqliteRowsMentioning(path, token, harness.tempRoot) for path in databases}
    if not any(afterFirst.values()):
        raise TestSkipped(
            f"a SQLite database was found ({', '.join(str(p) for p in databases)}) but no row "
            "mentions the fixture resource ids, so the store could not be checked"
        )

    secondRun = harness.run(inputDir)
    afterSecond = {path: sqliteRowsMentioning(path, token, harness.tempRoot) for path in databases}
    for path in databases:
        if afterFirst[path] and afterSecond[path] != afterFirst[path]:
            fail(
                f"{path.name} held {afterFirst[path]} rows for this input after the first run and "
                f"{afterSecond[path]} after an identical second run",
                secondRun,
            )


# ---------------------------------------------------------------------------
# tests: requirement 7, malformed input
# ---------------------------------------------------------------------------


def malformedFixture(harness: Harness) -> tuple[Path, list[str]]:
    inputDir = harness.newInputDir("malformed")
    harness.writeBilling(inputDir, "good.billing.csv", [("t16-bnf", "vm-small", 120, "use1")])
    harness.writeScan(inputDir, "good.scan.json", [("t16-fnb", "vm-small", "core", "use1")])
    harness.writeRaw(inputDir, "broken.scan.json", '{"scanned_at": "2026-01-15T00:00:00Z", "resources": [\n')
    harness.writeRules(inputDir, graceCents=100000)
    return inputDir, ["good.billing.csv", "good.scan.json", "broken.scan.json"]


@conformanceTest("malformed_file_does_not_stop_the_others")
def testMalformedDoesNotStop(harness: Harness) -> None:
    """Spec 7: 'One malformed input file must not stop the others'."""
    inputDir, _ = malformedFixture(harness)
    result = harness.run(inputDir)
    findings = harness.requireFindings(result)
    requireKind(findings, "t16-bnf", "billed_not_found", result)
    requireKind(findings, "t16-fnb", "found_not_billed", result)


@conformanceTest("per_file_outcomes_are_reported")
def testPerFileOutcomes(harness: Harness) -> None:
    """Spec 7: 'Report per-file outcomes at the end'."""
    inputDir, filenames = malformedFixture(harness)
    result = harness.run(inputDir)
    haystack = result.combinedOutput()
    if result.report is not None:
        haystack += "\n" + json.dumps(result.report, default=repr)
    missing = [name for name in filenames if name not in haystack]
    if missing:
        fail(
            f"no per-file outcome names {missing} in the printed output or the JSON report; "
            f"the input held {filenames}",
            result,
        )


# ---------------------------------------------------------------------------
# tests: requirement 6, the printed summary
# ---------------------------------------------------------------------------


@conformanceTest("summary_is_printed")
def testSummaryPrinted(harness: Harness) -> None:
    """Spec 6: 'Print a summary table'. The format is not fixed, so only presence is checked."""
    inputDir = harness.newInputDir("summary")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t20-bnf", "vm-small", 100, "use1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t20-fnb", "vm-small", "core", "use1")])
    harness.writeRules(inputDir, graceCents=100000)
    result = harness.run(inputDir)
    if not result.combinedOutput().strip():
        fail("the run printed nothing, but the spec requires a printed summary table", result)


# ---------------------------------------------------------------------------
# tests: the importability constraint
# ---------------------------------------------------------------------------


IMPORT_PROBE_SOURCE = '''
import importlib
import json
import os
import pkgutil
import sys
import traceback

sys.path.insert(0, os.getcwd())
MARKER = "%(marker)s"
name = sys.argv[1]
outcome = {"ok": False, "modules": [], "error": None}
try:
    package = importlib.import_module(name)
    outcome["modules"].append(name)
    if hasattr(package, "__path__"):
        for info in pkgutil.walk_packages(package.__path__, name + "."):
            if info.name.rsplit(".", 1)[-1] == "__main__":
                continue
            importlib.import_module(info.name)
            outcome["modules"].append(info.name)
    outcome["ok"] = True
except SystemExit as exc:
    outcome["error"] = "SystemExit(%%r) was raised while importing" %% (exc.code,)
except BaseException:
    outcome["error"] = traceback.format_exc(limit=8)
sys.stderr.write("\\n" + MARKER + json.dumps(outcome))
''' % {"marker": RESULT_MARKER}


IMPORT_CALL_SOURCE = '''
import importlib
import inspect
import itertools
import json
import os
import pkgutil
import sys
import traceback
from pathlib import Path

sys.path.insert(0, os.getcwd())
MARKER = "%(marker)s"
name, inputDir, rulesPath, needleA, needleB = sys.argv[1:6]
sys.argv = [name]
outcome = {"matched": None, "tried": [], "error": None}
EXCLUDED = {"main", "cli", "console_main", "run_cli", "entrypoint"}


def emit():
    sys.stderr.write("\\n" + MARKER + json.dumps(outcome))
    raise SystemExit(0)


def loadModules(root):
    modules = []
    package = importlib.import_module(root)
    modules.append(package)
    if hasattr(package, "__path__"):
        for info in pkgutil.walk_packages(package.__path__, root + "."):
            if info.name.rsplit(".", 1)[-1] == "__main__":
                continue
            try:
                modules.append(importlib.import_module(info.name))
            except BaseException:
                pass
    return modules


try:
    modules = loadModules(name)
except BaseException:
    outcome["error"] = traceback.format_exc(limit=8)
    emit()

ownNames = {module.__name__ for module in modules}
candidates = []
for module in modules:
    for attrName in sorted(vars(module)):
        if attrName.startswith("_") or attrName in EXCLUDED:
            continue
        attr = getattr(module, attrName)
        if not callable(attr):
            continue
        if getattr(attr, "__module__", None) not in ownNames:
            continue
        candidates.append((module.__name__ + "." + attrName, attrName, attr))


def rank(entry):
    lowered = entry[1].lower()
    if "reconcile" in lowered:
        return 0
    if "run" in lowered or "report" in lowered:
        return 1
    if "join" in lowered or "compare" in lowered:
        return 2
    return 3


candidates.sort(key=rank)
outcome["tried"] = [entry[0] for entry in candidates[:60]]


def textOf(value, depth=0, budget=None):
    if budget is None:
        budget = [40000]
    if budget[0] <= 0 or depth > 3:
        return ""
    chunks = []
    try:
        text = repr(value)
    except BaseException:
        text = ""
    budget[0] -= len(text)
    chunks.append(text)
    if inspect.isgenerator(value):
        try:
            value = list(itertools.islice(value, 500))
        except BaseException:
            value = None
    if isinstance(value, (list, tuple, set, frozenset)):
        for item in list(value)[:300]:
            chunks.append(textOf(item, depth + 1, budget))
    elif isinstance(value, dict):
        for item in list(value.values())[:300]:
            chunks.append(textOf(item, depth + 1, budget))
    else:
        try:
            members = vars(value)
        except TypeError:
            members = None
        if isinstance(members, dict):
            for item in list(members.values())[:60]:
                chunks.append(textOf(item, depth + 1, budget))
    return " ".join(chunks)


def looksRight(value):
    if value is None:
        return False
    text = textOf(value)
    return needleA in text and needleB in text


rulesObjects = []
for label, attrName, function in candidates:
    lowered = attrName.lower()
    if "rule" not in lowered and "config" not in lowered:
        continue
    for args in ((rulesPath,), (Path(rulesPath),), (Path(inputDir),), (inputDir,)):
        try:
            produced = function(*args)
        except BaseException:
            continue
        if produced is not None:
            rulesObjects.append(produced)
            break
    if len(rulesObjects) >= 3:
        break

budget = 500
for label, attrName, function in candidates:
    argSets = [(inputDir,), (Path(inputDir),), (Path(inputDir), Path(rulesPath)), (inputDir, rulesPath)]
    for rules in rulesObjects:
        argSets.append((inputDir, rules))
        argSets.append((Path(inputDir), rules))
    for args in argSets:
        budget -= 1
        if budget <= 0:
            emit()
        try:
            produced = function(*args)
        except BaseException:
            continue
        if looksRight(produced):
            outcome["matched"] = label + " called with " + str(len(args)) + " argument(s)"
            emit()
        for methodName in sorted(dir(produced)):
            if methodName.startswith("_"):
                continue
            lowered = methodName.lower()
            if not any(word in lowered for word in ("run", "reconcile", "report", "result", "finding")):
                continue
            method = getattr(produced, methodName, None)
            if not callable(method):
                continue
            for inner in ((), (inputDir,), (Path(inputDir),)):
                budget -= 1
                if budget <= 0:
                    emit()
                try:
                    value = method(*inner)
                except BaseException:
                    continue
                if looksRight(value):
                    outcome["matched"] = label + "()." + methodName + "()"
                    emit()
emit()
''' % {"marker": RESULT_MARKER}


def runHelperScript(harness: Harness, source: str, args: list[str]) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
    scriptPath = harness.tempRoot / f"helper-{randomToken()}.py"
    scriptPath.write_text(source, encoding="utf-8")
    env = childEnv()
    env["PYTHONPATH"] = os.pathsep.join([str(harness.armDir), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    try:
        completed = subprocess.run(
            [sys.executable, str(scriptPath), *args],
            cwd=str(harness.armDir),
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise TestSkipped(f"the import probe did not finish within {RUN_TIMEOUT_SECONDS}s") from exc
    payload: dict[str, Any] | None = None
    if RESULT_MARKER in completed.stderr:
        try:
            payload = json.loads(completed.stderr.rsplit(RESULT_MARKER, 1)[-1])
        except ValueError:
            payload = None
    return completed, payload


@conformanceTest("package_imports_without_running_the_cli")
def testImportable(harness: Harness) -> None:
    """Constraint: 'It must also be importable'. Importing must not run the tool."""
    before = snapshot([harness.armDir])
    completed, payload = runHelperScript(harness, IMPORT_PROBE_SOURCE, [harness.package])
    after = snapshot([harness.armDir])
    if payload is None:
        fail(
            f"the import probe produced no result. exit={completed.returncode} stderr={tail(completed.stderr)}"
        )
    if not payload.get("ok"):
        fail(f"importing {harness.package} and its submodules failed: {payload.get('error')}")
    produced = [
        path
        for path in changedSince(before, after)
        if path.suffix.lower() == ".json" or isSqliteFile(path)
    ]
    if produced:
        fail(
            "importing the package wrote "
            + ", ".join(path.name for path in produced)
            + ", so the reconciliation runs at import time rather than on demand"
        )


@conformanceTest("reconciliation_is_callable_without_the_cli")
def testImportableEntryPoint(harness: Harness) -> None:
    """Constraint: 'another program should be able to run the reconciliation without running the
    command-line tool'. The spec fixes no name or signature, so this is a best-effort search."""
    inputDir = harness.newInputDir("api")
    harness.writeBilling(inputDir, "finance.billing.csv", [("t19-billed-only", "vm-small", 4321, "us-east-1")])
    harness.writeScan(inputDir, "assets.scan.json", [("t19-scan-only", "vm-small", "core", "us-east-1")])
    rulesPath = harness.writeRules(inputDir, graceCents=100000)
    completed, payload = runHelperScript(
        harness,
        IMPORT_CALL_SOURCE,
        [harness.package, str(inputDir), str(rulesPath), "t19-billed-only", "t19-scan-only"],
    )
    if payload is None:
        raise TestSkipped(
            f"the callable probe produced no result. exit={completed.returncode} stderr={tail(completed.stderr)}"
        )
    if payload.get("error"):
        fail(f"importing {harness.package} for the callable probe failed: {payload['error']}")
    if payload.get("matched"):
        return
    tried = payload.get("tried") or []
    raise TestSkipped(
        "no public callable returned a result that mentions both fixture resources. "
        "The spec fixes no name or signature for the importable entry point, so this is not a "
        f"failure. Callables tried: {', '.join(tried[:20]) or 'none'}"
    )


if __name__ == "__main__":
    sys.exit(main())
