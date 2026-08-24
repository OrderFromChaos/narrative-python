"""Show the result of a run as a table, and write the same result as JSON.

The table holds one line per team, then the largest paths of each team above quota, then one line
per report file. The JSON report holds the same facts, and it holds exact byte counts where the
table holds rounded sizes.

    TEAM              USED      QUOTA    OVERAGE  STATUS
    platform        612.0G     500.0G     112.0G  OVER
    search            1.2T       2.0T          -  ok
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from quota_reconcile.sizes import formatByteCount
from quota_reconcile.vocabulary import FileOutcome, ReadOutcome, Reconciliation, ReportFormat, TeamUsage


TEAM_COLUMN = 14
SIZE_COLUMN = 10
STATUS_COLUMN = 9
PATH_COLUMN = 60
NO_VALUE = '-'
WORST_PATH_COUNT = 3


def printSummaryTable(result: Reconciliation, out: TextIO) -> None:
    """Show every team, the worst paths of every team above quota, and every report file."""
    printTeamTable(result, out)
    printWorstPaths(result, out)
    printReportOutcomes(result, out)


def printTeamTable(result: Reconciliation, out: TextIO) -> None:
    print(
        f'{"TEAM":<{TEAM_COLUMN}}{"USED":>{SIZE_COLUMN}}{"QUOTA":>{SIZE_COLUMN}}'
        f'{"OVERAGE":>{SIZE_COLUMN}}  {"STATUS":<{STATUS_COLUMN}}',
        file=out,
    )
    for team in result.teams:
        overage = formatByteCount(team.overage) if team.overage > 0 else NO_VALUE
        status = 'OVER' if team.overage > 0 else 'ok'
        print(
            f'{team.team:<{TEAM_COLUMN}}{formatByteCount(team.used):>{SIZE_COLUMN}}'
            f'{formatByteCount(team.quota):>{SIZE_COLUMN}}{overage:>{SIZE_COLUMN}}  {status:<{STATUS_COLUMN}}',
            file=out,
        )

    print(
        f'\nunattributed {formatByteCount(result.unattributed_bytes)}   exempt {formatByteCount(result.exempt_bytes)}',
        file=out,
    )


def printWorstPaths(result: Reconciliation, out: TextIO) -> None:
    for team in result.overages:
        print(f'\n{team.team}, largest paths:', file=out)
        for usage in team.paths[:WORST_PATH_COUNT]:
            print(f'  {formatByteCount(usage.size):>{SIZE_COLUMN}}  {shortenPathText(usage.path)}', file=out)


def printReportOutcomes(result: Reconciliation, out: TextIO) -> None:
    print('\nREPORTS', file=out)
    for outcome in result.outcomes:
        print(f'  {describeReadOutcome(outcome.outcome):<{STATUS_COLUMN}}{formatReportLine(outcome)}', file=out)


def formatReportLine(outcome: FileOutcome) -> str:
    """Give the tail of one report line in the table, which names the file and what came of it."""
    report = outcome.report
    if report is None:
        return f'{outcome.source.name} ({describeReportFormat(outcome.report_format)}): {outcome.detail}'
    return (
        f'{outcome.source.name} ({describeReportFormat(outcome.report_format)}): '
        f'{len(report.entries)} entries, {report.rejected_lines} rejected'
    )


def writeJsonReport(result: Reconciliation, report_json_path: Path) -> None:
    """Write the whole result as one JSON object, with exact byte counts."""
    document: JsonObject = {
        'input_dir': str(result.input_dir),
        'teams': [describeTeamUsage(team) for team in result.teams],
        'overages': [describeTeamUsage(team) for team in result.overages],
        'unattributed_bytes': int(result.unattributed_bytes),
        'exempt_bytes': int(result.exempt_bytes),
        'reports': [describeFileOutcome(outcome) for outcome in result.outcomes],
    }
    report_json_path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


def describeTeamUsage(team: TeamUsage) -> JsonObject:
    return {
        'team': str(team.team),
        'used_bytes': int(team.used),
        'quota_bytes': int(team.quota),
        'overage_bytes': int(team.overage),
        'paths': [{'path': str(usage.path), 'bytes': int(usage.size)} for usage in team.paths],
    }


def describeFileOutcome(outcome: FileOutcome) -> JsonObject:
    report = outcome.report
    return {
        'source': str(outcome.source),
        'format': outcome.report_format.value,
        'outcome': outcome.outcome.value,
        'host': None if report is None else report.host,
        'entries': 0 if report is None else len(report.entries),
        'rejected': 0 if report is None else report.rejected_lines,
        'detail': outcome.detail,
    }


def describeReadOutcome(outcome: ReadOutcome) -> str:
    match outcome:
        case ReadOutcome.READ:
            return 'ok'
        case ReadOutcome.DEGRADED:
            return 'degraded'
        case ReadOutcome.UNREADABLE:
            return 'failed'


def describeReportFormat(report_format: ReportFormat) -> str:
    match report_format:
        case ReportFormat.TEXT:
            return 'text'
        case ReportFormat.JSON:
            return 'json'


def shortenPathText(entry_path: Path) -> str:
    """Cut a path down to the path column, and keep the end of it.

    Returns:
        The path itself when it fits, and an ellipsis before the last characters when it does not.
    """
    ELLIPSIS = '...'
    text = str(entry_path)
    if len(text) <= PATH_COLUMN:
        return text
    return ELLIPSIS + text[-(PATH_COLUMN - len(ELLIPSIS)) :]


### vocabulary #########################################################################


JsonObject = dict[str, object]
