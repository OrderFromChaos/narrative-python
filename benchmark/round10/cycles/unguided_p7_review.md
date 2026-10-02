# Comments for review: P7 without the skill

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package midi_analyser): 0 comments

`scratchpad/nos/p7_1/midi_analyser`

## Run 2 (package midistat): 1 comments

`scratchpad/nos/p7_2/midistat`

### 1. analysis.py:63

```python
     55         return min(self.notes, key=lambda note: (-note.seconds, note.start, note.pitch), default=None)
     56 
     57     @property
     58     def hanging(self) -> int:
     59         return sum(note.hanging for note in self.notes)
     60 
     61     @property
     62     def maxPolyphony(self) -> int:
>>   63         # At equal ticks an end (-1) sorts before a start (+1), so touching notes do not overlap.
     64         changes = sorted([(note.startTick, 1) for note in self.notes] + [(note.endTick, -1) for note in self.notes])
     65         sounding = 0
     66         most = 0
     67         for _, change in changes:
     68             sounding += change
     69             most = max(most, sounding)
     70         return most
     71 
     72 
     73 def analyseBytes(data: bytes) -> Analysis:
```

## Run 3 (package midistat): 13 comments

`scratchpad/nos/p7_3/midistat`

### 2. analysis.py:15

```python
      7 
      8 import bisect
      9 from collections import defaultdict, deque
     10 from dataclasses import asdict, dataclass
     11 
     12 from midistat.smf import MidiFile, Track, parse_smf
     13 
     14 DEFAULT_MICROS_PER_QUARTER = 500_000
>>   15 DRUM_CHANNEL = 9  # channel 10 as musicians number it
     16 NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
     17 SECONDS_DIGITS = 6
     18 
     19 
     20 def analyse_midi(data: bytes) -> 'FileAnalysis':
     21     """Analyse the bytes of one Standard MIDI File.
     22 
     23     Raises midistat.MidiError when the bytes are unreadable.
     24     """
     25     midi = parse_smf(data)
```

### 3. analysis.py:118

```python
    110 
    111 def max_polyphony(notes: list['Note']) -> int:
    112     """The most notes sounding at once; a note sounds on [start, end), so zero-length notes never do."""
    113     changes = []
    114     for note in notes:
    115         if note.end_tick > note.start_tick:
    116             changes.append((note.start_tick, 1))
    117             changes.append((note.end_tick, -1))
>>  118     changes.sort()  # at equal ticks, -1 sorts before +1: an ending note frees its slot first
    119     sounding = 0
    120     most = 0
    121     for _, change in changes:
    122         sounding += change
    123         most = max(most, sounding)
    124     return most
    125 
    126 
    127 def note_name(pitch: int) -> str:
    128     return f'{NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}'
```

### 4. analysis.py:133

```python
    125 
    126 
    127 def note_name(pitch: int) -> str:
    128     return f'{NOTE_NAMES[pitch % 12]}{pitch // 12 - 1}'
    129 
    130 
    131 @dataclass(frozen=True)
    132 class Note:
>>  133     channel: int  # 0 to 15
    134     pitch: int
    135     start_tick: int
    136     end_tick: int
    137 
    138 
    139 @dataclass(frozen=True)
    140 class TempoMap:
    141     """Tempo spans sorted by start tick, each with the tick-microseconds elapsed before it."""
    142 
    143     span_starts: list[int]
```

### 5. analysis.py:146

```python
    138 
    139 @dataclass(frozen=True)
    140 class TempoMap:
    141     """Tempo spans sorted by start tick, each with the tick-microseconds elapsed before it."""
    142 
    143     span_starts: list[int]
    144     span_tempos: list[int]
    145     span_offsets: list[int]
>>  146     micros_per_second_of_ticks: int  # division * 1,000,000
    147 
    148     @classmethod
    149     def from_file(cls, midi: MidiFile) -> 'TempoMap':
    150         # Sort by tick, then track, then order within the track; at a shared tick the last wins.
    151         changes = sorted(
    152             (tempo.tick, track_index, event_index, tempo.micros_per_quarter)
    153             for track_index, track in enumerate(midi.tracks)
    154             for event_index, tempo in enumerate(track.tempos)
    155         )
    156         starts = [0]
```

### 6. analysis.py:150

```python
    142 
    143     span_starts: list[int]
    144     span_tempos: list[int]
    145     span_offsets: list[int]
    146     micros_per_second_of_ticks: int  # division * 1,000,000
    147 
    148     @classmethod
    149     def from_file(cls, midi: MidiFile) -> 'TempoMap':
>>  150         # Sort by tick, then track, then order within the track; at a shared tick the last wins.
    151         changes = sorted(
    152             (tempo.tick, track_index, event_index, tempo.micros_per_quarter)
    153             for track_index, track in enumerate(midi.tracks)
    154             for event_index, tempo in enumerate(track.tempos)
    155         )
    156         starts = [0]
    157         tempos = [DEFAULT_MICROS_PER_QUARTER]
    158         offsets = [0]
    159         for tick, _, _, micros in changes:
    160             offsets.append(offsets[-1] + (tick - starts[-1]) * tempos[-1])
```

### 7. analysis.py:176

```python
    168 
    169     def seconds_at(self, tick: int) -> float:
    170         return round(self.tick_micros(tick) / self.micros_per_second_of_ticks, SECONDS_DIGITS)
    171 
    172 
    173 @dataclass(frozen=True)
    174 class LongestNote:
    175     name: str
>>  176     channel: int  # 1 to 16
    177     start: float
    178     seconds: float
    179 
    180 
    181 @dataclass(frozen=True)
    182 class FileAnalysis:
    183     format: int
    184     tracks: int
    185     division: int
    186     seconds: float
```

### 8. smf.py:18

```python
     10 
     11 class MidiError(Exception):
     12     """The bytes are not a Standard MIDI File this package can read."""
     13 
     14 
     15 @dataclass(frozen=True)
     16 class NoteEvent:
     17     tick: int
>>   18     channel: int  # 0 to 15, as stored in the status byte
     19     pitch: int
     20     velocity: int
     21     is_on: bool  # True for a 9n status byte, False for 8n
     22 
     23 
     24 @dataclass(frozen=True)
     25 class TempoEvent:
     26     tick: int
     27     micros_per_quarter: int
     28 
```

### 9. smf.py:21

```python
     13 
     14 
     15 @dataclass(frozen=True)
     16 class NoteEvent:
     17     tick: int
     18     channel: int  # 0 to 15, as stored in the status byte
     19     pitch: int
     20     velocity: int
>>   21     is_on: bool  # True for a 9n status byte, False for 8n
     22 
     23 
     24 @dataclass(frozen=True)
     25 class TempoEvent:
     26     tick: int
     27     micros_per_quarter: int
     28 
     29 
     30 @dataclass(frozen=True)
     31 class TimeSignatureEvent:
```

### 10. smf.py:42

```python
     34     denominator: int
     35 
     36 
     37 @dataclass(frozen=True)
     38 class Track:
     39     notes: list[NoteEvent]
     40     tempos: list[TempoEvent]
     41     time_signatures: list[TimeSignatureEvent]
>>   42     end_tick: int  # the end-of-track tick, or the last event's tick when the track has none
     43 
     44 
     45 @dataclass(frozen=True)
     46 class MidiFile:
     47     format: int
     48     track_count: int  # as declared in the MThd chunk
     49     division: int  # ticks per quarter note
     50     tracks: list[Track]  # the MTrk chunks present, in file order
     51 
     52 
```

### 11. smf.py:48

```python
     40     tempos: list[TempoEvent]
     41     time_signatures: list[TimeSignatureEvent]
     42     end_tick: int  # the end-of-track tick, or the last event's tick when the track has none
     43 
     44 
     45 @dataclass(frozen=True)
     46 class MidiFile:
     47     format: int
>>   48     track_count: int  # as declared in the MThd chunk
     49     division: int  # ticks per quarter note
     50     tracks: list[Track]  # the MTrk chunks present, in file order
     51 
     52 
     53 META_PREFIX = 0xFF
     54 META_END_OF_TRACK = 0x2F
     55 META_SET_TEMPO = 0x51
     56 META_TIME_SIGNATURE = 0x58
     57 SYSEX_STATUSES = (0xF0, 0xF7)
     58 
```

### 12. smf.py:49

```python
     41     time_signatures: list[TimeSignatureEvent]
     42     end_tick: int  # the end-of-track tick, or the last event's tick when the track has none
     43 
     44 
     45 @dataclass(frozen=True)
     46 class MidiFile:
     47     format: int
     48     track_count: int  # as declared in the MThd chunk
>>   49     division: int  # ticks per quarter note
     50     tracks: list[Track]  # the MTrk chunks present, in file order
     51 
     52 
     53 META_PREFIX = 0xFF
     54 META_END_OF_TRACK = 0x2F
     55 META_SET_TEMPO = 0x51
     56 META_TIME_SIGNATURE = 0x58
     57 SYSEX_STATUSES = (0xF0, 0xF7)
     58 
     59 # Data bytes after the status byte, by the status byte's high nibble.
```

### 13. smf.py:50

```python
     42     end_tick: int  # the end-of-track tick, or the last event's tick when the track has none
     43 
     44 
     45 @dataclass(frozen=True)
     46 class MidiFile:
     47     format: int
     48     track_count: int  # as declared in the MThd chunk
     49     division: int  # ticks per quarter note
>>   50     tracks: list[Track]  # the MTrk chunks present, in file order
     51 
     52 
     53 META_PREFIX = 0xFF
     54 META_END_OF_TRACK = 0x2F
     55 META_SET_TEMPO = 0x51
     56 META_TIME_SIGNATURE = 0x58
     57 SYSEX_STATUSES = (0xF0, 0xF7)
     58 
     59 # Data bytes after the status byte, by the status byte's high nibble.
     60 CHANNEL_DATA_LENGTHS = {0x8: 2, 0x9: 2, 0xA: 2, 0xB: 2, 0xC: 1, 0xD: 1, 0xE: 2}
```

### 14. smf.py:59

```python
     51 
     52 
     53 META_PREFIX = 0xFF
     54 META_END_OF_TRACK = 0x2F
     55 META_SET_TEMPO = 0x51
     56 META_TIME_SIGNATURE = 0x58
     57 SYSEX_STATUSES = (0xF0, 0xF7)
     58 
>>   59 # Data bytes after the status byte, by the status byte's high nibble.
     60 CHANNEL_DATA_LENGTHS = {0x8: 2, 0x9: 2, 0xA: 2, 0xB: 2, 0xC: 1, 0xD: 1, 0xE: 2}
     61 
     62 
     63 def parse_smf(data: bytes) -> MidiFile:
     64     if data[:4] != b'MThd':
     65         raise MidiError('does not start with an MThd chunk')
     66     chunks = split_chunks(data)
     67     header = chunks[0][1]
     68     if len(header) < 6:
     69         raise MidiError(f'MThd chunk is {len(header)} bytes, shorter than 6')
```
