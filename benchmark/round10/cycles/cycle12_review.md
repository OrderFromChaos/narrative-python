# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package midi_report): 6 comments

`scratchpad/cycle12/p7_W_1/midi_report`

### 1. analysis.py:39

```python
     31     tempo_changes = _collectEvents(smf_file.tracks, TempoChange)
     32     tempo_map = tempo.buildTempoMap(tempo_changes, smf_file.header.ticks_per_quarter)
     33     pairings = [pairing.pairNotes(track) for track in smf_file.tracks]
     34     notes: list[Note] = []
     35     for track_pairing in pairings:
     36         notes.extend(track_pairing.notes)
     37     pitches = [note.pitch for note in notes]
     38     end_tick = max((track.end_tick for track in smf_file.tracks), default=None)
>>   39     # of time signatures on one tick, min() returns the first in track order
     40     time_signature = min(_collectEvents(smf_file.tracks, TimeSignature), key=lambda each: each.tick, default=None)
     41 
     42     analysis = FileAnalysis(
     43         format=smf_file.header.format,
     44         tracks=len(smf_file.tracks),
     45         ticks_per_quarter=smf_file.header.ticks_per_quarter,
     46         seconds=Fraction(0) if end_tick is None else tempo.secondsAtTick(tempo_map, end_tick),
     47         time_signature=time_signature,
     48         tempo_changes=len(tempo_changes),
     49         notes=len(notes),
```

### 2. analysis.py:89

```python
     81     return min(
     82         timed_notes,
     83         key=lambda timed: (-timed.seconds, timed.start_seconds, timed.pitch, timed.channel),
     84         default=None,
     85     )
     86 
     87 
     88 def _measureMaxPolyphony(notes: Sequence[Note]) -> int:
>>   89     # an end sorts before a start on the same tick, so a note ending as another starts doesn't overlap it
     90     START = 1
     91     END = -1
     92     edges = sorted([(note.start_tick, START) for note in notes] + [(note.end_tick, END) for note in notes])
     93     sounding = 0
     94     max_polyphony = 0
     95     for _, step in edges:
     96         sounding += step
     97         max_polyphony = max(max_polyphony, sounding)
     98 
     99     return max_polyphony
```

### 3. report.py:134

```python
    126             return (
    127                 f'{_roundSeconds(analysis.seconds):>10.6f} s  {_formatTimeSignature(analysis.time_signature)}  '
    128                 f'{analysis.notes} notes {pitch_range}, {analysis.drum_hits} drum hits, '
    129                 f'polyphony {analysis.max_polyphony}, {analysis.hanging} hanging, {analysis.orphan_offs} orphan offs'
    130             )
    131 
    132 
    133 def _formatTimeSignature(time_signature: TimeSignature | None) -> str:
>>  134     # a Standard MIDI File without a time signature is in 4/4
    135     if time_signature is None:
    136         return '4/4'
    137 
    138     return f'{time_signature.numerator}/{time_signature.denominator}'
    139 
    140 
    141 def _nameNote(pitch: Pitch) -> str:
    142     NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    143     return f'{NAMES[pitch % 12]}{pitch // 12 - 1}'
    144 
```

### 4. smf.py:203

```python
    195         if end > len(self.track_payload):
    196             raise self.rejectEvent('event runs past the end of the track')
    197 
    198         taken = self.track_payload[self.position : end]
    199         self.position = end
    200         return taken
    201 
    202     def readVariableLength(self) -> int:
>>  203         # 7 bits per byte, most significant first. The top bit is set on every byte but the last.
    204         value = 0
    205         while True:
    206             byte = self.readByte()
    207             value = (value << 7) | (byte & 0x7F)
    208             if byte < 0x80:
    209                 return value
    210 
    211     def rejectEvent(self, reason: str) -> UnreadableFileError:
    212         return _rejectFile(f'track {self.track_number}, byte {self.position} of the chunk: {reason}')
    213 
```

### 5. vocabulary.py:62

```python
     54 
     55 
     56 TrackEvent = NoteStart | NoteEnd | TempoChange | TimeSignature
     57 
     58 
     59 @dataclass(frozen=True)
     60 class Track:
     61     events: tuple[TrackEvent, ...]
>>   62     end_tick: Tick  # the end-of-track event, or the last event when the chunk ends without one
     63 
     64 
     65 @dataclass(frozen=True)
     66 class SmfFile:
     67     header: SmfHeader
     68     tracks: tuple[Track, ...]
     69 
     70 
     71 @dataclass(frozen=True)
     72 class TempoSegment:
```

### 6. vocabulary.py:74

```python
     66 class SmfFile:
     67     header: SmfHeader
     68     tracks: tuple[Track, ...]
     69 
     70 
     71 @dataclass(frozen=True)
     72 class TempoSegment:
     73     start_tick: Tick
>>   74     elapsed_tick_microseconds: int  # sum of ticks times microseconds per quarter before start_tick
     75     microseconds_per_quarter: int
     76 
     77 
     78 @dataclass(frozen=True)
     79 class TempoMap:
     80     ticks_per_quarter: int
     81     segments: tuple[TempoSegment, ...]
     82 
     83 
     84 @dataclass(frozen=True)
```

## Run 2 (package midi_analyser): 8 comments

`scratchpad/cycle12/p7_W_2/midi_analyser`

### 7. analysis.py:57

```python
     49         max_polyphony=_computeMaxPolyphony(pairing.notes),
     50         hanging=pairing.hanging,
     51         orphan_offs=pairing.orphan_offs,
     52     )
     53 
     54 
     55 def _findFirstTimeSignature(tracks: Iterable[Track]) -> TimeSignature | None:
     56     changes = chain.from_iterable(track.time_signature_changes for track in tracks)
>>   57     # min() returns the first of several equal ticks, which is the earliest in track order
     58     first = min(changes, key=lambda change: change.tick, default=None)
     59     return None if first is None else first.time_signature
     60 
     61 
     62 def _findLongestNote(timed_notes: Iterable[_TimedNote]) -> LongestNote | None:
     63     longest = min(
     64         timed_notes,
     65         key=lambda timed: (
     66             timed.start_seconds - timed.end_seconds,
     67             timed.note.start,
```

### 8. analysis.py:91

```python
     83 
     84 def _computeMaxPolyphony(notes_played: Iterable[Note]) -> int:
     85     edges: list[tuple[int, int]] = []
     86     for note in notes_played:
     87         edges.extend(((note.start, 1), (note.end, -1)))
     88 
     89     sounding = 0
     90     peak = 0
>>   91     # -1 sorts before +1, so a note ending on a tick is gone before a note starting on that tick
     92     for _, change in sorted(edges):
     93         sounding += change
     94         peak = max(peak, sounding)
     95     return peak
     96 
     97 
     98 ### vocabulary #########################################################################
     99 
    100 
    101 @dataclass(frozen=True)
```

### 9. notes.py:18

```python
     10 
     11 from collections import defaultdict, deque
     12 from collections.abc import Iterable
     13 from dataclasses import dataclass
     14 
     15 from midi_analyser.vocabulary import Channel, Note, NoteMessage, NotePairing, NoteStatus, Pitch, Tick, Track
     16 
     17 
>>   18 # General MIDI percussion, channel 10 to musicians
     19 DRUM_CHANNEL = Channel(9)
     20 
     21 
     22 def pairNotes(tracks: Iterable[Track]) -> NotePairing:
     23     """Pair note messages within each track, in file order."""
     24     notes: list[Note] = []
     25     drum_hits = 0
     26     hanging = 0
     27     orphan_offs = 0
     28     for track in tracks:
```

### 10. report.py:120

```python
    112 
    113 def _formatOptionalNoteName(pitch: Pitch | None) -> str | None:
    114     return None if pitch is None else _formatNoteName(pitch)
    115 
    116 
    117 def _formatNoteName(pitch: Pitch) -> str:
    118     NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    119 
>>  120     # pitch 60 is C4
    121     return f'{NAMES[pitch % 12]}{pitch // 12 - 1}'
    122 
    123 
    124 ### vocabulary #########################################################################
    125 
    126 
    127 @dataclass(frozen=True)
    128 class _Totals:
    129     files: int
    130     unreadable: int
```

### 11. smf.py:112

```python
    104         tick = Tick(tick + reader.readVariableLength())
    105         lead = reader.readByte()
    106 
    107         if lead == META:
    108             meta_type = reader.readByte()
    109             payload = reader.readBytes(reader.readVariableLength())
    110             if meta_type == END_OF_TRACK:
    111                 break
>>  112             # a payload too short for the fields of its type is skipped
    113             if meta_type == SET_TEMPO and len(payload) >= TEMPO_SIZE:
    114                 tempo_changes.append(TempoChange(tick, int.from_bytes(payload[:TEMPO_SIZE], 'big')))
    115             if meta_type == TIME_SIGNATURE and len(payload) >= TIME_SIGNATURE_SIZE:
    116                 time_signature = TimeSignature(numerator=payload[0], denominator=2 ** payload[1])
    117                 time_signature_changes.append(TimeSignatureChange(tick, time_signature))
    118             continue
    119         if lead in SYSTEM_EXCLUSIVE:
    120             reader.readBytes(reader.readVariableLength())
    121             continue
    122         if lead >= SYSTEM_STATUS:
```

### 12. smf.py:189

```python
    181         STATUS_FLAG = 0x80
    182 
    183         value = self.readByte()
    184         if value & STATUS_FLAG:
    185             raise _rejectMidi(f'status byte {value:#04x} appears where a data byte belongs')
    186         return value
    187 
    188     def readVariableLength(self) -> int:
>>  189         # 7 bits per byte, most significant first
    190         BITS_PER_BYTE = 7
    191         VALUE_MASK = 0x7F
    192         CONTINUATION_FLAG = 0x80
    193 
    194         value = 0
    195         while True:
    196             byte = self.readByte()
    197             value = (value << BITS_PER_BYTE) | (byte & VALUE_MASK)
    198             if not byte & CONTINUATION_FLAG:
    199                 return value
```

### 13. tempo.py:17

```python
      9 from bisect import bisect_right
     10 from collections.abc import Iterable
     11 from dataclasses import dataclass
     12 from fractions import Fraction
     13 
     14 from midi_analyser.vocabulary import TempoChange, Tick
     15 
     16 
>>   17 # SMF 1.0 tempo before the first set-tempo event, 120 beats per minute
     18 DEFAULT_MICROSECONDS_PER_QUARTER = 500_000
     19 
     20 
     21 class TempoMap:
     22     def __init__(self, ticks_per_quarter: int, tempo_changes: Iterable[TempoChange]) -> None:
     23         spans = [_TempoSpan(Tick(0), Fraction(0), DEFAULT_MICROSECONDS_PER_QUARTER)]
     24         # a stable sort leaves same-tick changes in track order, so the last of them applies
     25         for change in sorted(tempo_changes, key=lambda change: change.tick):
     26             start_seconds = _computeSpanSeconds(spans[-1], change.tick, ticks_per_quarter)
     27             if change.tick == spans[-1].start:
```

### 14. tempo.py:24

```python
     16 
     17 # SMF 1.0 tempo before the first set-tempo event, 120 beats per minute
     18 DEFAULT_MICROSECONDS_PER_QUARTER = 500_000
     19 
     20 
     21 class TempoMap:
     22     def __init__(self, ticks_per_quarter: int, tempo_changes: Iterable[TempoChange]) -> None:
     23         spans = [_TempoSpan(Tick(0), Fraction(0), DEFAULT_MICROSECONDS_PER_QUARTER)]
>>   24         # a stable sort leaves same-tick changes in track order, so the last of them applies
     25         for change in sorted(tempo_changes, key=lambda change: change.tick):
     26             start_seconds = _computeSpanSeconds(spans[-1], change.tick, ticks_per_quarter)
     27             if change.tick == spans[-1].start:
     28                 spans.pop()
     29             spans.append(_TempoSpan(change.tick, start_seconds, change.microseconds_per_quarter))
     30 
     31         self.ticks_per_quarter = ticks_per_quarter
     32         self.spans = tuple(spans)
     33         self.span_starts = tuple(span.start for span in spans)
     34 
```
