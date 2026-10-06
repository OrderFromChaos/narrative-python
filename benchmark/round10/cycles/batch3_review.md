# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## P1 timesheet payroll: 9 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/e353c500-9351-4d01-9820-ce74e41e4305/scratchpad/batch3/P1`

### 1. tests/test_timesheet_payroll.py:84

```python
     76     elapsed_seconds=st.integers(min_value=0, max_value=7 * 24 * 3600),
     77     round_to_minutes=st.sampled_from([1, 5, 6, 15, 30, 60]),
     78 )
     79 def testRoundingIsNearestStepWithHalfUp(elapsed_seconds: int, round_to_minutes: int) -> None:
     80     step_seconds = round_to_minutes * 60
     81     paid_minutes = shifts.roundShiftMinutes(pendulum.duration(seconds=elapsed_seconds), round_to_minutes)
     82 
     83     assert paid_minutes % round_to_minutes == 0
>>   84     # The paid length is within half a step of the elapsed time.
>>   85     # At exactly half a step, the paid length is the longer one.
     86     distance = paid_minutes * 60 - elapsed_seconds
     87     assert -step_seconds < 2 * distance <= step_seconds
```

### 2. timesheet_payroll/money.py:21

```python
     13 
     14 import re
     15 
     16 
     17 _CENTS_PER_UNIT = 100
     18 
     19 
     20 def parseCents(raw_amount: str) -> int | None:
>>   21     # matches:
>>   22     # `18.50`
>>   23     # `18`
>>   24     # rejects:
>>   25     # `.5`
>>   26     # `-18.50`
     27     AMOUNT_PATTERN = re.compile(r'([0-9]+)(?:\.([0-9]{1,2}))?')
     28     amount_match = AMOUNT_PATTERN.fullmatch(raw_amount)
     29     if amount_match is None:
     30         return None
     31 
     32     whole, fraction = amount_match.groups(default='')
     33     return int(whole) * _CENTS_PER_UNIT + int(fraction.ljust(2, '0'))
     34 
     35 
     36 def formatCents(cents: int) -> str:
```

### 3. timesheet_payroll/punch_files.py:95

```python
     87     if not (badge is not None and at is not None and fields['direction'] in {member.value for member in Direction}):
     88         return Problem(source, badge, ProblemKind.MALFORMED)
     89 
     90     return Punch(EmployeeId(badge), at, Direction(fields['direction']), source)
     91 
     92 
     93 def _parseInstant(raw_at: str) -> pendulum.DateTime | None:
     94     try:
>>   95         # the default tz=UTC would give a string with no UTC offset a UTC one. With tz=None, the DateTime stays naive
     96         at = pendulum.parse(raw_at, tz=None)
     97     except ValueError:
     98         return None
     99     if not (isinstance(at, pendulum.DateTime) and at.tzinfo is not None):
    100         return None
    101     return at.in_timezone('UTC')
    102 
    103 
    104 ### vocabulary #########################################################################
    105 
```

### 4. timesheet_payroll/roster_file.py:36

```python
     28     """Parse the roster at roster_path. A site is valid when it is a key of site_timezones.
     29 
     30     Raises:
     31         UnusableInputError: the file is missing, unreadable or not UTF-8 CSV, or a row is malformed.
     32     """
     33     if not roster_path.is_file():
     34         raise _rejectRoster(roster_path, 'no such file')
     35     try:
>>   36         # utf-8-sig strips a byte-order mark, such as Excel's CSV UTF-8 export writes before the header
     37         with roster_path.open(encoding='utf-8-sig', newline='') as roster_stream:
     38             rows = list(csv.reader(roster_stream))
     39     except OSError as exc:
     40         raise _rejectRoster(roster_path, f'unreadable: {exc}') from exc
     41     except UnicodeDecodeError as exc:
     42         raise _rejectRoster(roster_path, f'not UTF-8: {exc}') from exc
     43     except csv.Error as exc:
     44         raise _rejectRoster(roster_path, f'not CSV: {exc}') from exc
     45 
     46     if not (rows and rows[0] == _ROSTER_HEADER):
```

### 5. timesheet_payroll/rules_file.py:90

```python
     82             )
     83             raise _rejectRules(rules_path, detail)
     84         site_timezones[site] = pendulum.Timezone(timezone_name)
     85     return site_timezones
     86 
     87 
     88 def _parsePositiveInteger(rules_path: Path, key: str, raw_rules: dict[str, object]) -> int:
     89     raw_value = raw_rules[key]
>>   90     # bool subclasses Python int. Reject it too
     91     if not (isinstance(raw_value, int) and not isinstance(raw_value, bool) and raw_value > 0):
     92         raise _rejectRules(rules_path, f'{key} is {raw_value!r} (expected a positive integer such as 15)')
     93     return raw_value
     94 
     95 
     96 def _parseMultiplier(rules_path: Path, raw_multiplier: object) -> Fraction:
     97     # matches:
     98     # `1.5`
     99     # `2`
    100     # rejects:
```

### 6. timesheet_payroll/rules_file.py:97

```python
     89     raw_value = raw_rules[key]
     90     # bool subclasses Python int. Reject it too
     91     if not (isinstance(raw_value, int) and not isinstance(raw_value, bool) and raw_value > 0):
     92         raise _rejectRules(rules_path, f'{key} is {raw_value!r} (expected a positive integer such as 15)')
     93     return raw_value
     94 
     95 
     96 def _parseMultiplier(rules_path: Path, raw_multiplier: object) -> Fraction:
>>   97     # matches:
>>   98     # `1.5`
>>   99     # `2`
>>  100     # rejects:
>>  101     # `1,5`
>>  102     # `.5`
    103     DECIMAL_PATTERN = re.compile(r'[0-9]+(?:\.[0-9]+)?')
    104     if not (isinstance(raw_multiplier, str) and DECIMAL_PATTERN.fullmatch(raw_multiplier)):
    105         detail = f'overtime_multiplier is {raw_multiplier!r} (expected a decimal string such as "1.5")'
    106         raise _rejectRules(rules_path, detail)
    107     return Fraction(raw_multiplier)
```

### 7. timesheet_payroll/store.py:42

```python
     34         ' week_start TEXT NOT NULL,'
     35         ' name TEXT NOT NULL,'
     36         ' regular_minutes INTEGER NOT NULL CHECK (regular_minutes >= 0),'
     37         ' overtime_minutes INTEGER NOT NULL CHECK (overtime_minutes >= 0),'
     38         ' gross_pay_cents INTEGER NOT NULL CHECK (gross_pay_cents >= 0),'
     39         ' PRIMARY KEY (employee_id, week_start)'
     40         ') STRICT'
     41     )
>>   42     # The WHERE clause skips an update that changes no value.
>>   43     # total_changes then counts only the rows added or changed.
     44     UPSERT = (
     45         'INSERT INTO employee_week VALUES (?, ?, ?, ?, ?, ?)'
     46         ' ON CONFLICT (employee_id, week_start) DO UPDATE SET'
     47         ' name = excluded.name,'
     48         ' regular_minutes = excluded.regular_minutes,'
     49         ' overtime_minutes = excluded.overtime_minutes,'
     50         ' gross_pay_cents = excluded.gross_pay_cents'
     51         ' WHERE name IS NOT excluded.name'
     52         ' OR regular_minutes IS NOT excluded.regular_minutes'
     53         ' OR overtime_minutes IS NOT excluded.overtime_minutes'
```

### 8. timesheet_payroll/store.py:68

```python
     60             week.name,
     61             week.regular_minutes,
     62             week.overtime_minutes,
     63             week.gross_pay_cents,
     64         )
     65         for week in weeks
     66     ]
     67     try:
>>   68         # A connection's context manager commits or rolls back, but does not close the connection.
>>   69         # closing() closes the connection.
     70         with closing(sqlite3.connect(database_path)) as connection, connection:
     71             connection.execute(CREATE_TABLE)
     72             connection.executemany(UPSERT, rows)
     73             changed_rows = connection.total_changes
     74     except sqlite3.Error as exc:
     75         _LOG.error('database.unwritable', extra={'path': str(database_path), 'detail': str(exc)})
     76         raise StoreError(f'{database_path}: {exc}') from exc
     77 
     78     return changed_rows
     79 
```

### 9. timesheet_payroll/store.py:84

```python
     76         raise StoreError(f'{database_path}: {exc}') from exc
     77 
     78     return changed_rows
     79 
     80 
     81 ### vocabulary #########################################################################
     82 
     83 
>>   84 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     85 class _EmployeeWeekRow(NamedTuple):
     86     employee_id: str
     87     week_start: str
     88     name: str
     89     regular_minutes: int
     90     overtime_minutes: int
     91     gross_pay_cents: int
```

## P2 subscription invoices: 6 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/e353c500-9351-4d01-9820-ce74e41e4305/scratchpad/batch3/P2`

### 10. invoicing/billing.py:74

```python
     66         event_count=event_log.line_count,
     67         duplicate_count=event_log.duplicate_count,
     68         billed_cents=sum(invoice.total_cents for invoice in invoices),
     69     )
     70     return billing
     71 
     72 
     73 def _parseMonth(raw_month: str) -> BillingMonth:
>>   74     # matches:
>>   75     # `2028-03`
>>   76     # rejects:
>>   77     # `2028-3`
>>   78     # `2028-13`
     79     MONTH_PATTERN = re.compile(r'([0-9]{4})-(0[1-9]|1[0-2])')
     80 
     81     month_match = MONTH_PATTERN.fullmatch(raw_month)
     82     if month_match is None:
     83         _LOG.debug('billing.bad_month', extra={'month': raw_month})
     84         raise InvoicingSetupError(f'bad month {raw_month!r} (expected "2028-03")')
     85     return BillingMonth(int(month_match[1]), int(month_match[2]))
```

### 11. invoicing/event_files.py:115

```python
    107         return malformed
    108 
    109     kind = EventKind(raw_kind)
    110     plan_valid = isinstance(raw_plan, str) if _planRequired(kind) else 'plan' not in fields
    111     if not plan_valid:
    112         return malformed
    113 
    114     try:
>>  115         # parse() assumes UTC for a time without a UTC offset.
>>  116         # tz=None returns such a time naive, and the check below rejects it.
    117         at = pendulum.parse(raw_at, tz=None)
    118     except ValueError:
    119         return malformed
    120     if not (isinstance(at, DateTime) and at.tzinfo is not None):
    121         return malformed
    122 
    123     plan = PlanName(raw_plan) if isinstance(raw_plan, str) else None
    124     return Event(CustomerId(customer), at, kind, plan, source)
    125 
    126 
```

### 12. invoicing/price_file.py:29

```python
     21 
     22 
     23 def readPrices(prices_json_path: Path) -> Prices:
     24     """Read and check a prices file.
     25 
     26     Raises:
     27         InvoicingSetupError: the file is unreadable, is not JSON, or has a missing or malformed entry.
     28     """
>>   29     # matches:
>>   30     # `9.99`
>>   31     # `120.00`
>>   32     # rejects:
>>   33     # `9.9`
>>   34     # `-1.00`
     35     PRICE_PATTERN = re.compile(r'[0-9]+\.[0-9]{2}')
     36     # matches:
     37     # `0.0725`
     38     # `0`
     39     # rejects:
     40     # `.08`
     41     # `8%`
     42     RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]+)?')
     43     STATE_PATTERN = re.compile(r'[A-Z]{2}')
     44 
```

### 13. invoicing/price_file.py:36

```python
     28     """
     29     # matches:
     30     # `9.99`
     31     # `120.00`
     32     # rejects:
     33     # `9.9`
     34     # `-1.00`
     35     PRICE_PATTERN = re.compile(r'[0-9]+\.[0-9]{2}')
>>   36     # matches:
>>   37     # `0.0725`
>>   38     # `0`
>>   39     # rejects:
>>   40     # `.08`
>>   41     # `8%`
     42     RATE_PATTERN = re.compile(r'[0-9]+(\.[0-9]+)?')
     43     STATE_PATTERN = re.compile(r'[A-Z]{2}')
     44 
     45     try:
     46         document = json.loads(prices_json_path.read_bytes())
     47     except OSError as exc:
     48         raise _rejectPrices(prices_json_path, f'unreadable: {exc.strerror}') from exc
     49     except (json.JSONDecodeError, UnicodeDecodeError) as exc:
     50         raise _rejectPrices(prices_json_path, f'not UTF-8 JSON: {exc}') from exc
     51 
```

### 14. invoicing/store.py:40

```python
     32     )
     33     UPSERT = (
     34         'INSERT INTO invoices VALUES (?, ?, ?, ?, ?)'
     35         ' ON CONFLICT (customer_id, month) DO UPDATE SET'
     36         ' subtotal_cents = excluded.subtotal_cents,'
     37         ' tax_cents = excluded.tax_cents,'
     38         ' total_cents = excluded.total_cents'
     39     )
>>   40     # json_each() turns the JSON array of billed customer ids into rows
     41     DELETE_UNBILLED = 'DELETE FROM invoices WHERE month = ? AND customer_id NOT IN (SELECT value FROM json_each(?))'
     42 
     43     rows = [
     44         _InvoiceRow(
     45             invoice.customer.customer_id,
     46             billing.month.label,
     47             invoice.subtotal_cents,
     48             invoice.tax_cents,
     49             invoice.total_cents,
     50         )
```

### 15. invoicing/store.py:65

```python
     57         connection.executemany(UPSERT, rows)
     58         connection.execute(DELETE_UNBILLED, (billing.month.label, billed_ids))
     59         connection.commit()
     60 
     61 
     62 ### vocabulary #########################################################################
     63 
     64 
>>   65 # sqlite3.Cursor.executemany() rejects dataclass rows. Rows are a NamedTuple
     66 class _InvoiceRow(NamedTuple):
     67     customer_id: str
     68     month: str
     69     subtotal_cents: int
     70     tax_cents: int
     71     total_cents: int
```

## P7 MIDI analyser: 12 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/e353c500-9351-4d01-9820-ce74e41e4305/scratchpad/batch3/P7`

### 16. midi_analyser/analysis.py:67

```python
     59         longest=_findLongestNote(paired.notes, tempo_map),
     60         max_polyphony=_countMaxPolyphony(paired.notes),
     61         hanging_count=sum(note.hanging for note in paired.notes),
     62         orphan_off_count=paired.orphan_off_count,
     63     )
     64 
     65 
     66 def _buildTempoMap(midi_file: MidiFile) -> _TempoMap:
>>   67     # sorted() is stable. Of two changes at one tick, the one read later applies
     68     changes = sorted(
     69         chain.from_iterable(track.tempo_changes for track in midi_file.tracks),
     70         key=lambda change: change.tick,
     71     )
     72     return _TempoMap(ticks_per_quarter=midi_file.ticks_per_quarter, changes=tuple(changes))
     73 
     74 
     75 def _pairNotes(tracks: Iterable[Track]) -> _PairedNotes:
     76     """Pair the note starts and ends of every track, and count the drum hits and orphan offs."""
     77     DRUM_CHANNEL = Channel(9)
```

### 17. midi_analyser/analysis.py:109

```python
    101             )
    102     return _PairedNotes(notes=tuple(notes), drum_hit_count=drum_hit_count, orphan_off_count=orphan_off_count)
    103 
    104 
    105 def _selectTimeSignature(tracks: Iterable[Track]) -> TimeSignature:
    106     changes = list(chain.from_iterable(track.time_signature_changes for track in tracks))
    107     if not changes:
    108         return TimeSignature(numerator=4, denominator=4)
>>  109     # min() returns the first of equal ticks. Of two changes at one tick, the one read first applies
    110     return min(changes, key=lambda change: change.tick).signature
    111 
    112 
    113 def _findLongestNote(notes: Sequence[_Note], tempo_map: _TempoMap) -> LongestNote | None:
    114     if not notes:
    115         return None
    116     longest = min(notes, key=lambda note: (-tempo_map.measureSeconds(note), note.start_tick, note.pitch))
    117     return LongestNote(
    118         pitch=longest.pitch,
    119         channel=longest.channel,
```

### 18. midi_analyser/analysis.py:126

```python
    118         pitch=longest.pitch,
    119         channel=longest.channel,
    120         start_seconds=float(tempo_map.convertTickToSeconds(longest.start_tick)),
    121         seconds=float(tempo_map.measureSeconds(longest)),
    122     )
    123 
    124 
    125 def _countMaxPolyphony(notes: Iterable[_Note]) -> int:
>>  126     # an end (-1) sorts before a start (+1) at one tick, so a note ending as another starts doesn't overlap it
    127     boundaries = sorted(chain.from_iterable(((note.start_tick, 1), (note.end_tick, -1)) for note in notes))
    128     sounding = 0
    129     max_sounding = 0
    130     for _tick, step in boundaries:
    131         sounding += step
    132         max_sounding = max(max_sounding, sounding)
    133     return max_sounding
    134 
    135 
    136 ### vocabulary #########################################################################
```

### 19. midi_analyser/analysis.py:164

```python
    156     notes: tuple[_Note, ...]
    157     drum_hit_count: int
    158     orphan_off_count: int
    159 
    160 
    161 @dataclass(frozen=True)
    162 class _TempoMap:
    163     ticks_per_quarter: int
>>  164     # must be sorted by tick
    165     changes: tuple[TempoChange, ...]
    166 
    167     def convertTickToSeconds(self, tick: int) -> Fraction:
    168         DEFAULT_MICROSECONDS_PER_QUARTER = 500_000
    169         MICROSECONDS_PER_SECOND = 1_000_000
    170         # the sum over tempo spans of ticks × microseconds per quarter note
    171         tick_microseconds = 0
    172         span_start = 0
    173         microseconds_per_quarter = DEFAULT_MICROSECONDS_PER_QUARTER
    174         for change in self.changes:
```

### 20. midi_analyser/analysis.py:170

```python
    162 class _TempoMap:
    163     ticks_per_quarter: int
    164     # must be sorted by tick
    165     changes: tuple[TempoChange, ...]
    166 
    167     def convertTickToSeconds(self, tick: int) -> Fraction:
    168         DEFAULT_MICROSECONDS_PER_QUARTER = 500_000
    169         MICROSECONDS_PER_SECOND = 1_000_000
>>  170         # the sum over tempo spans of ticks × microseconds per quarter note
    171         tick_microseconds = 0
    172         span_start = 0
    173         microseconds_per_quarter = DEFAULT_MICROSECONDS_PER_QUARTER
    174         for change in self.changes:
    175             if change.tick > tick:
    176                 break
    177             tick_microseconds += (change.tick - span_start) * microseconds_per_quarter
    178             span_start = change.tick
    179             microseconds_per_quarter = change.microseconds_per_quarter
    180         tick_microseconds += (tick - span_start) * microseconds_per_quarter
```

### 21. midi_analyser/report.py:115

```python
    107         'notes': analysis.note_count,
    108         'drum_hits': analysis.drum_hit_count,
    109         'lowest': None if analysis.lowest is None else _formatNoteName(analysis.lowest),
    110         'highest': None if analysis.highest is None else _formatNoteName(analysis.highest),
    111         'longest': None
    112         if longest is None
    113         else {
    114             'name': _formatNoteName(longest.pitch),
>>  115             # musicians number channels 1 to 16
    116             'channel': longest.channel + 1,
    117             'start': round(longest.start_seconds, _SECONDS_DIGITS),
    118             'seconds': round(longest.seconds, _SECONDS_DIGITS),
    119         },
    120         'max_polyphony': analysis.max_polyphony,
    121         'hanging': analysis.hanging_count,
    122         'orphan_offs': analysis.orphan_off_count,
    123     }
    124 
    125 
```

### 22. midi_analyser/report.py:146

```python
    138                 f'{round(analysis.seconds, _SECONDS_DIGITS)} s  {signature.numerator}/{signature.denominator}  '
    139                 f'{analysis.note_count} notes  {pitch_range}  polyphony {analysis.max_polyphony}  '
    140                 f'{analysis.drum_hit_count} drum hits  {analysis.hanging_count} hanging  '
    141                 f'{analysis.orphan_off_count} orphan offs'
    142             )
    143 
    144 
    145 def _formatNoteName(pitch: Pitch) -> str:
>>  146     # pitch 60 is C4
    147     NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    148     octave, step = divmod(pitch, 12)
    149     return f'{NAMES[step]}{octave - 1}'
    150 
    151 
    152 ### vocabulary #########################################################################
    153 
    154 
    155 @dataclass(frozen=True)
    156 class _Totals:
```

### 23. midi_analyser/smf.py:67

```python
     59 
     60 
     61 def _rejectMidi(reason: str) -> UnreadableMidiError:
     62     _LOG.debug('midi.unreadable', extra={'reason': reason})
     63     return UnreadableMidiError(reason)
     64 
     65 
     66 def _splitChunks(midi_bytes: bytes) -> list[tuple[bytes, bytes]]:
>>   67     # a 4-byte ASCII type, then a 4-byte big-endian length of the body
     68     CHUNK_HEADER = struct.Struct('>4sI')
     69     chunks = []
     70     offset = 0
     71     while offset < len(midi_bytes):
     72         if len(midi_bytes) - offset < CHUNK_HEADER.size:
     73             raise _rejectMidi(f'chunk header at byte {offset} runs past the end of the data')
     74         chunk_type, length = CHUNK_HEADER.unpack_from(midi_bytes, offset)
     75         body_start = offset + CHUNK_HEADER.size
     76         offset = body_start + length
     77         if offset > len(midi_bytes):
```

### 24. midi_analyser/smf.py:178

```python
    170 
    171 
    172 def _decodeTimeSignature(meta_data: bytes, track_number: int) -> TimeSignature:
    173     USED_LENGTH = 2
    174     if len(meta_data) < USED_LENGTH:
    175         raise _rejectMidi(
    176             f'time-signature event in track {track_number} has {len(meta_data)} data bytes, expected 4',
    177         )
>>  178     # the denominator is written as a power of two
    179     return TimeSignature(numerator=meta_data[0], denominator=2 ** meta_data[1])
    180 
    181 
    182 ### vocabulary #########################################################################
    183 
    184 
    185 class _ByteReader:
    186     """Read bytes and variable-length quantities from the body of one track chunk."""
    187 
    188     def __init__(self, track_bytes: bytes, track_number: int) -> None:
```

### 25. midi_analyser/smf.py:208

```python
    200         read_bytes = self.track_bytes[self.position : end]
    201         self.position = end
    202         return read_bytes
    203 
    204     def readByte(self) -> int:
    205         return self.readBytes(1)[0]
    206 
    207     def readVariableLength(self) -> int:
>>  208         # 7 bits per byte, most significant first. The top bit is set on every byte but the last
    209         value = 0
    210         while True:
    211             byte = self.readByte()
    212             value = (value << 7) | (byte & 0x7F)
    213             if byte < 0x80:
    214                 return value
```

### 26. midi_analyser/vocabulary.py:11

```python
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from typing import NewType, TypeAlias
      8 
      9 
     10 Pitch = NewType('Pitch', int)
>>   11 # 0 to 15, as written in a status byte
     12 Channel = NewType('Channel', int)
     13 
     14 
     15 class UnreadableMidiError(RuntimeError):
     16     """The bytes are not a Standard MIDI File that this package can read."""
     17 
     18 
     19 class NoteKind(Enum):
     20     OFF = 'off'
     21     ON = 'on'
```

### 27. midi_analyser/vocabulary.py:62

```python
     54     tempo_changes: tuple[TempoChange, ...]
     55     time_signature_changes: tuple[TimeSignatureChange, ...]
     56     end_tick: int
     57 
     58 
     59 @dataclass(frozen=True)
     60 class MidiFile:
     61     format: int
>>   62     # the header's count. It can differ from len(tracks)
     63     track_count: int
     64     ticks_per_quarter: int
     65     tracks: tuple[Track, ...]
     66 
     67 
     68 @dataclass(frozen=True)
     69 class LongestNote:
     70     pitch: Pitch
     71     channel: Channel
     72     start_seconds: float
```
