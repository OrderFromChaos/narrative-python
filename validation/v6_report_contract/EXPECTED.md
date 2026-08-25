# Expected result for this fixture

Derived from `TASK.md` only. No implementation was read while this file was written.

Rules in force, as `fixture/reconcile.json` states them:

- `ignored_skus = ["platform-support-tier"]`
- `region_aliases = {"mc7": "mc", "mid-continent-7": "mc7", "north-atlantic-1": "na1", "south-pacific-2": "sp2"}`
- `grace_cents = 750`

All three pass the type check: a list of strings, an object of string to string, and a non-negative
integer.

`mid-continent-7 -> mc7` and `mc7 -> mc` form a two-step chain. The spec resolves one hop only, so
`mid-continent-7` and `mc` are different regions.

`broken.scan.json` stops after `"team": "billi`. The quote, the object, the array and the outer
object are all unclosed. No parser can accept it, so the file fails as a whole. The two resource ids
inside it, `min-halite-6612` and `min-pyrite-8874`, occur nowhere else in the fixture. If either id
appears in any finding, the reader accepted a file that it must reject.

Files are read in ascending basename order: `broken.scan.json`, `core.billing.csv`,
`edge.billing.csv`, `estate.scan.json`. `reconcile.json` is the rules file and is neither read as an
inventory file nor reported. The directory holds no other entry, no subdirectory and no dotfile, and
the program writes nothing into it.

The fixture is plain ASCII throughout, every line ends in a single LF, neither CSV holds a blank or
whitespace-only line, and no file carries a byte-order mark. No field is quoted and no field holds a
comma. Nothing in the report therefore depends on the input encoding, the line ending, or the CSV
dialect.

## Every record, against the closed rejection list

The closed list rejects a billing line for a row that does not hold exactly four fields, a
`monthly_cents` that is not a base-ten integer or is negative, an empty `resource_id`, `sku` or
`region`, or a `resource_id` that already appeared on the billing side. It rejects a scanned
resource that is not a JSON object, that lacks `id`, `sku`, `team` or `region`, that holds a
non-string or empty value for any of the four, or whose `id` already appeared on the scan side.
Three clauses pin it further: "already appeared" means "was accepted", a blank line is not a record,
and `monthly_cents` is a run of ASCII digits and nothing else. The header row is not a record.

Two records in this fixture fail that list, and no other record fails any part of it:

| Record | File | Condition it fails |
|---|---|---|
| the second `min-galena-3357` row, at 1400 | `edge.billing.csv` | `resource_id` already appeared on the billing side. The earlier row carrying that id, at 900, was **accepted**, so it does reserve the id. |
| `min-borax-8241` | `estate.scan.json` | `region` is the empty string |

Checks against each pinned clause:

- **Header.** Both billing files open with `resource_id,sku,monthly_cents,region` exactly, so
  neither file fails, and neither header is counted as a record. Fields are read by position.
- **Blank lines.** Each CSV ends with one LF and holds no empty line, so no reader construction can
  manufacture a phantom row, and the clause has nothing to exempt.
- **`monthly_cents`.** Every cost in the fixture — 182400, 43900, 12750, 9600, 250000, 41200, 6300,
  20000, 20000, 8800, 3300, 7100, 15000, 750, 31000, 4500, 900, 1400 — is a bare run of ASCII
  digits. No sign, no space, no underscore, no leading zero.
- **"Already appeared" means "was accepted".** This changes nothing here. The one duplicate follows
  an accepted record, so it is still rejected, and the one rejected scan record appears only once,
  so it has no successor to release.

Every other record holds four non-empty fields or four non-empty string values. `NA1` on the
`min-agate-2216` billing row is a non-empty region and is therefore accepted; its case is a join
question, not a rejection question.

Ascending basename order puts `core.billing.csv` before `edge.billing.csv`, so the billing side is
filled from `core` first. No id is shared between the two billing files, so file order changes
nothing here. Within `edge.billing.csv` the surviving `min-galena-3357` is the earlier row, at 900.

## The 13 findings, in the order the report must list them

| # | Kind | Resource id | Rule that puts it there |
|---|---|---|---|
| 1 | `billed_not_found` | `min-flint-5520` | Billed at 41200, never scanned. Highest cost, so it ranks first. |
| 2 | `billed_not_found` | `min-augite-5290` | Billed at 20000, never scanned. Ties with `min-zircon-1147` on cost, and `min-augite-5290` sorts first on `resource_id`. The CSV writes `min-zircon-1147` on the earlier line, so file order and report order disagree. |
| 3 | `billed_not_found` | `min-zircon-1147` | The other half of the tie. |
| 4 | `billed_not_found` | `min-borax-8241` | Billed at 15000. The scan file holds a record for this id, but its `region` is empty, so the closed list rejects it and it reaches neither the join nor any total. The billing line is therefore unmatched. `sources` names the billing file only, because a rejected record supplies nothing. |
| 5 | `billed_not_found` | `min-slate-6647` | Billed at 6300, never scanned. |
| 6 | `billed_not_found` | `min-galena-3357` | `edge.billing.csv` holds this id twice, at 900 and at 1400. The first record wins, so the cost is 900. A report that says 1400 kept the last record instead of the first. |
| 7 | `billed_not_found` | `min-marl-1183` | Billed at 750, never scanned. 750 is not strictly greater than `grace_cents`, so `above_grace` is false and this finding does not set the exit code. It still holds its rank. |
| 8 | `found_not_billed` | `min-chert-8830` | The two sides disagree on `sku`. `edge.billing.csv` says `platform-support-tier`, which is ignored, so the billing record drops before the join. `estate.scan.json` says `object-archive`, which is not ignored, so the scan record survives with no partner. |
| 9 | `found_not_billed` | `min-cinnabar-7028` | Scanned, no billing line anywhere. |
| 10 | `found_not_billed` | `min-schist-3391` | Scanned, no billing line anywhere. |
| 11 | `region_mismatch` | `min-agate-2216` | Matched pair. The billing side says `NA1`, the scan side says `na1`. Comparison is exact and does not fold case, and `NA1` is not an alias key. |
| 12 | `region_mismatch` | `min-obsidian-3062` | Matched pair. `north-atlantic-1` resolves to `na1`; the scan side says `sp2`. |
| 13 | `region_mismatch` | `min-topaz-9053` | Matched pair. The billing side says `mid-continent-7`, which resolves one hop to `mc7`. The scan side says `mc`, which is not an alias key. `mc7` and `mc` are different. A transitive resolver reaches `mc` from `mid-continent-7` and drops this finding. |

Order within the block: `billed_not_found` by `monthly_cents` descending then `resource_id`
ascending; `found_not_billed` by `resource_id` ascending; `region_mismatch` by `resource_id`
ascending. Every comparison is by Unicode code point. Every id in this fixture is lowercase ASCII,
so no ordering here depends on the collation rule; the only mixed-case string in the data is a
region value, which no sort touches.

Each finding carries exactly the values the per-kind table in `TASK.md` assigns to its kind. All
three `region_mismatch` pairs agree on `sku` across the two sides, so the rule that a
`region_mismatch` states the billing side's `sku` does not move a byte in this fixture.

### Rows that must produce no finding

| Resource id | What it holds | Why there is no finding |
|---|---|---|
| `min-quartz-4471` | region `na1` on both sides | Control. Identical id, identical region text. |
| `min-basalt-2298` | billing `north-atlantic-1`, scan `na1` | The alias direction the rules file writes. |
| `min-gypsum-7715` | billing `sp2`, scan `south-pacific-2` | The reverse direction. The rules file maps long to short only, and the comparison must still make these equal. |
| `min-jasper-4408` | billing sku `blockstore-ssd`, scan sku `object-archive`, region `na1` on both sides | Neither sku is ignored, so both sides survive and the pair joins. A sku disagreement between two matched records is not a finding. This pair counts in `matched`. |
| `min-pumice-9104` | sku `platform-support-tier` on both sides | The sku is ignored on both sides. The regions differ on purpose (`na1` against `sp2`) and the cost is 250000. A `region_mismatch` here means the ignore did not run. |
| `min-tuff-2504` | billing only, sku `platform-support-tier` | The billing record drops before the join, so the absent scan record raises nothing. A `billed_not_found` of 31000 here means the ignore ran after the join. |
| `min-halite-6612`, `min-pyrite-8874` | `broken.scan.json` only | The file does not parse. Nothing inside it is data. |

## Per-file outcomes, in the order the report must list them

| # | Path | Format | Status | Accepted | Rejected | `len(problems)` | Rule that puts it there |
|---|---|---|---|---|---|---|---|
| 1 | `broken.scan.json` | `scan` | `failed` | 0 | 0 | 1 | `format` follows the filename suffix alone, so a `*.scan.json` that holds no JSON is still `scan` and it fails. `accepted` and `rejected` are both 0 on a failed file. One file-level failure is one problem string. |
| 2 | `core.billing.csv` | `billing` | `ok` | 13 | 0 | 0 | An exact header and 13 data rows, none of which fails the closed list. The header is not a record, and there is no blank line to exempt. `min-pumice-9104` carries an ignored sku and is still counted in `accepted`, because the ignore runs after reading. |
| 3 | `edge.billing.csv` | `billing` | `partial` | 4 | 1 | 1 | An exact header and 5 data rows. The second `min-galena-3357` repeats an id that was accepted, so it is one rejected record and one problem string. The two ignored rows, `min-tuff-2504` and `min-chert-8830`, stay in `accepted`. |
| 4 | `estate.scan.json` | `scan` | `partial` | 11 | 1 | 1 | 12 records. `min-borax-8241` holds an empty `region`, so it is one rejected record and one problem string. |

`len(problems)` is `rejected` plus 1 when `status` is `failed`, on every row above. Order is by
`path`, and `path` is the basename, which is also the read order.

## The report

`TASK.md` pins the serialisation to
`json.dumps(report, indent=2, ensure_ascii=False) + '\n'`, written as UTF-8 with `newline='\n'`. The
block below is that output, byte for byte, including the way `indent=2` puts every array element on
its own line and renders an empty array as `[]`. The file ends with one LF.

Three values are exempt from the byte comparison: `generated_at`, `input_dir` (the path as given on
the command line), and the prose inside each `problems` string. The *length* of each `problems`
array is fixed, and is given in the table above.

```json
{
  "generated_at": "<datetime.now(UTC).isoformat(timespec='seconds') at the start of the run>",
  "input_dir": "fixture",
  "rules": {
    "ignored_skus": [
      "platform-support-tier"
    ],
    "region_aliases": {
      "mc7": "mc",
      "mid-continent-7": "mc7",
      "north-atlantic-1": "na1",
      "south-pacific-2": "sp2"
    },
    "grace_cents": 750
  },
  "totals": {
    "billing_lines": 17,
    "scanned_resources": 11,
    "ignored_billing": 3,
    "ignored_scanned": 1,
    "matched": 7,
    "findings": 13,
    "above_grace": 6,
    "by_kind": {
      "billed_not_found": 7,
      "found_not_billed": 3,
      "region_mismatch": 3
    }
  },
  "findings": [
    {
      "kind": "billed_not_found",
      "resource_id": "min-flint-5520",
      "sku": "gpu-accelerated-1",
      "monthly_cents": 41200,
      "team": null,
      "billed_region": "na1",
      "scanned_region": null,
      "above_grace": true,
      "sources": [
        "core.billing.csv"
      ]
    },
    {
      "kind": "billed_not_found",
      "resource_id": "min-augite-5290",
      "sku": "compute-burst-2",
      "monthly_cents": 20000,
      "team": null,
      "billed_region": "sp2",
      "scanned_region": null,
      "above_grace": true,
      "sources": [
        "core.billing.csv"
      ]
    },
    {
      "kind": "billed_not_found",
      "resource_id": "min-zircon-1147",
      "sku": "compute-burst-2",
      "monthly_cents": 20000,
      "team": null,
      "billed_region": "na1",
      "scanned_region": null,
      "above_grace": true,
      "sources": [
        "core.billing.csv"
      ]
    },
    {
      "kind": "billed_not_found",
      "resource_id": "min-borax-8241",
      "sku": "queue-broker",
      "monthly_cents": 15000,
      "team": null,
      "billed_region": "sp2",
      "scanned_region": null,
      "above_grace": true,
      "sources": [
        "core.billing.csv"
      ]
    },
    {
      "kind": "billed_not_found",
      "resource_id": "min-slate-6647",
      "sku": "blockstore-ssd",
      "monthly_cents": 6300,
      "team": null,
      "billed_region": "sp2",
      "scanned_region": null,
      "above_grace": true,
      "sources": [
        "core.billing.csv"
      ]
    },
    {
      "kind": "billed_not_found",
      "resource_id": "min-galena-3357",
      "sku": "object-archive",
      "monthly_cents": 900,
      "team": null,
      "billed_region": "na1",
      "scanned_region": null,
      "above_grace": true,
      "sources": [
        "edge.billing.csv"
      ]
    },
    {
      "kind": "billed_not_found",
      "resource_id": "min-marl-1183",
      "sku": "dns-zone",
      "monthly_cents": 750,
      "team": null,
      "billed_region": "na1",
      "scanned_region": null,
      "above_grace": false,
      "sources": [
        "edge.billing.csv"
      ]
    },
    {
      "kind": "found_not_billed",
      "resource_id": "min-chert-8830",
      "sku": "object-archive",
      "monthly_cents": null,
      "team": "archive-guild",
      "billed_region": null,
      "scanned_region": "south-pacific-2",
      "above_grace": false,
      "sources": [
        "estate.scan.json"
      ]
    },
    {
      "kind": "found_not_billed",
      "resource_id": "min-cinnabar-7028",
      "sku": "queue-broker",
      "monthly_cents": null,
      "team": "ml-research",
      "billed_region": null,
      "scanned_region": "north-atlantic-1",
      "above_grace": false,
      "sources": [
        "estate.scan.json"
      ]
    },
    {
      "kind": "found_not_billed",
      "resource_id": "min-schist-3391",
      "sku": "compute-standard-8",
      "monthly_cents": null,
      "team": "data-eng",
      "billed_region": null,
      "scanned_region": "sp2",
      "above_grace": false,
      "sources": [
        "estate.scan.json"
      ]
    },
    {
      "kind": "region_mismatch",
      "resource_id": "min-agate-2216",
      "sku": "dns-zone",
      "monthly_cents": 3300,
      "team": "network-eng",
      "billed_region": "NA1",
      "scanned_region": "na1",
      "above_grace": false,
      "sources": [
        "core.billing.csv",
        "estate.scan.json"
      ]
    },
    {
      "kind": "region_mismatch",
      "resource_id": "min-obsidian-3062",
      "sku": "nat-gateway",
      "monthly_cents": 9600,
      "team": "network-eng",
      "billed_region": "north-atlantic-1",
      "scanned_region": "sp2",
      "above_grace": false,
      "sources": [
        "core.billing.csv",
        "estate.scan.json"
      ]
    },
    {
      "kind": "region_mismatch",
      "resource_id": "min-topaz-9053",
      "sku": "compute-standard-8",
      "monthly_cents": 7100,
      "team": "platform-core",
      "billed_region": "mid-continent-7",
      "scanned_region": "mc",
      "above_grace": false,
      "sources": [
        "core.billing.csv",
        "estate.scan.json"
      ]
    }
  ],
  "files": [
    {
      "path": "broken.scan.json",
      "format": "scan",
      "status": "failed",
      "accepted": 0,
      "rejected": 0,
      "problems": [
        "<one file-level failure: the file does not parse>"
      ]
    },
    {
      "path": "core.billing.csv",
      "format": "billing",
      "status": "ok",
      "accepted": 13,
      "rejected": 0,
      "problems": []
    },
    {
      "path": "edge.billing.csv",
      "format": "billing",
      "status": "partial",
      "accepted": 4,
      "rejected": 1,
      "problems": [
        "<one rejected record: min-galena-3357 is a repeated resource_id>"
      ]
    },
    {
      "path": "estate.scan.json",
      "format": "scan",
      "status": "partial",
      "accepted": 11,
      "rejected": 1,
      "problems": [
        "<one rejected record: min-borax-8241 has an empty region>"
      ]
    }
  ],
  "exit_code": 1
}
```

### How the totals are reached

Each member is taken from the `totals` table in `TASK.md`.

- `billing_lines` = accepted billing records across every file, before the ignore = 13 from
  `core.billing.csv` + 4 from `edge.billing.csv` = 17.
- `scanned_resources` = accepted scanned records across every file, before the ignore = 11 from
  `estate.scan.json` + 0 from `broken.scan.json` = 11.
- `ignored_billing` = 3: `min-pumice-9104`, `min-tuff-2504` and `min-chert-8830` all carry
  `platform-support-tier` on the billing side. All three are counted in `accepted` and in
  `billing_lines` first, and dropped after.
- `ignored_scanned` = 1: `min-pumice-9104` alone carries `platform-support-tier` on the scan side.
- 17 - 3 = 14 billing records reach the join. 11 - 1 = 10 scan records reach the join.
- `matched` = 7 pairs that joined, whether or not their regions agreed: `min-quartz-4471`,
  `min-basalt-2298`, `min-gypsum-7715`, `min-obsidian-3062`, `min-jasper-4408`, `min-agate-2216`,
  `min-topaz-9053`.
- `billed_not_found` = 14 - 7 = 7. `found_not_billed` = 10 - 7 = 3. `region_mismatch` = 3 of the 7
  matched pairs.
- `findings` = 13, the length of the `findings` array, and 7 + 3 + 3 = 13.
- `above_grace` = 6 findings whose `above_grace` is true: the 7 `billed_not_found` less
  `min-marl-1183` at exactly 750.
- `exit_code` = 1, because at least one `billed_not_found` is above the grace.

### Re-run behaviour

A second run over this unchanged directory must not change the row count in SQLite, and must produce
the same `files` array, because the program writes nothing into the input directory.

## Verdict

**The byte-identical claim holds for this fixture.** Every byte of the report above is determined by
`TASK.md`, except `generated_at`, `input_dir` and the prose inside the four `problems` strings, all
three of which the document exempts. The array lengths, the key orders, the value sorts, the
indentation, the empty-array rendering and the trailing newline are all pinned.

**No value moved** from the previous derivation. `billing_lines` 17, `scanned_resources` 11, 13
findings, `matched` 7, `above_grace` 6, `exit_code` 1. The two rejections stayed exactly where they
were: the duplicate `min-galena-3357` follows an *accepted* record, so the "already appeared means
was accepted" clause still rejects it, and `min-borax-8241` occurs once, so that clause has no
successor to release. Neither CSV holds a blank line, so the blank-line clause has nothing to
exempt.

One hole this round closed that the previous pass only half-saw. The header question was live, and
worse than "miscounted": the header row holds four non-empty fields, so it fails no clause of the
closed list *except* the `monthly_cents` rule, whose value is the literal `monthly_cents`. An
implementation that did not exempt the header would have **rejected** it, reporting
`core.billing.csv` as `partial` with `accepted` 13, `rejected` 1 and one problem string. "The header
is not a record" removes that.

## Known-open, out of reach of this fixture

None of these can change a byte of the report above. They are recorded so their absence is
deliberate, not overlooked.

1. **`--report` defaults into the input directory when the working directory is the input
   directory.** "Default `report.json` in the working directory" and "the program never writes
   inside the input directory" cannot both be obeyed from a working directory that *is* the input
   directory, and the document does not say which wins. The documented invocation,
   `python3 -m <package> <fixture-dir>`, runs from outside the fixture, so the two clauses never
   meet. Worth one sentence if a harness might ever `cd` into the fixture.

2. **The read encoding, the line ending and the CSV dialect of the input files are not pinned.**
   The report's *write* path is pinned; the read path is not. A byte-order mark would break the
   exact-header rule under `utf-8` and pass under `utf-8-sig`. A CRLF file read by splitting on
   `\n` would leave `\r` on the `region` field, which is non-empty and so accepted, and would change
   `billed_region` in the output. A quoted field holding a comma splits differently under
   `csv.reader` and under `str.split`. This fixture is pure ASCII, LF-terminated, unquoted and
   comma-free, and the one file not authored for this round, `broken.scan.json`, fails as a whole
   for a reason independent of all three. Verified at byte level.

3. **"Blank line" is not defined against a whitespace-only line.** `"   "` is one field, not zero,
   so the closed list rejects it while the blank-line clause arguably exempts it. Neither CSV holds
   such a line.

4. **A wrong header versus no header.** The file-failure clause says a `*.billing.csv` fails "when
   it has no header row", and the new clause says it "must open with the header ... exactly". Read
   together a wrong header fails the file, which is surely the intent, but the two sentences are
   adjacent rather than joined. Both headers here are exact.

5. **The empty-directory clause says "empty `findings` and `files` arrays",** but a directory that
   holds no inventory file may still hold a non-inventory file, which the `files` rules require to
   be reported as `skipped`. The two statements collide only in that case. This fixture holds four
   inventory files.

6. **Where the SQLite database is written** is still unspecified beyond "not inside the input
   directory". That is now enough: it can no longer appear in a `files` array.
