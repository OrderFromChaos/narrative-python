"""Parse the bytes of a Standard MIDI File into an SmfFile.

The events of a Track are note starts, note ends, set-tempo and time signatures. Its end_tick is the
tick of its end-of-track event, where reading stops. A note on with velocity 0 becomes a NoteEnd.
Chunks other than MThd and MTrk, system exclusive events and the other meta events are skipped.
Sysex leaves running status unchanged, as meta events do.
"""

from __future__ import annotations

from dataclasses import dataclass

from midi_report.logs import LOG
from midi_report.vocabulary import (
    Channel,
    NoteEnd,
    NoteStart,
    Pitch,
    SmfFile,
    SmfHeader,
    TempoChange,
    Tick,
    TimeSignature,
    Track,
    TrackEvent,
    UnreadableFileError,
)


def parseSmf(smf_bytes: bytes) -> SmfFile:
    """Parse a whole file.

    Raises:
        UnreadableFileError: the file does not start with MThd, a chunk or an event runs past the
            end of its data, MThd is shorter than 6 bytes, the division is SMPTE time or 0, or a track
            has a byte no event can start with.
    """
    HEADER_TYPE = 'MThd'
    TRACK_TYPE = 'MTrk'
    if not smf_bytes.startswith(HEADER_TYPE.encode('ascii')):
        raise _rejectFile('file does not start with MThd')

    chunks = _readChunks(smf_bytes)
    header = _parseHeader(chunks[0].payload)
    track_payloads = [chunk.payload for chunk in chunks if chunk.chunk_type == TRACK_TYPE]
    tracks = tuple(_parseTrack(payload, track_number) for track_number, payload in enumerate(track_payloads, start=1))
    return SmfFile(header, tracks)


def _rejectFile(reason: str) -> UnreadableFileError:
    LOG.debug('smf.rejected', extra={'reason': reason})
    return UnreadableFileError(reason)


def _readChunks(smf_bytes: bytes) -> list[_Chunk]:
    """Split a file into its chunks, in file order.

    Raises:
        UnreadableFileError: a chunk runs past the end of the file.
    """
    TYPE_SIZE = 4
    CHUNK_PREFIX_SIZE = 8
    chunks: list[_Chunk] = []
    position = 0
    while position < len(smf_bytes):
        payload_start = position + CHUNK_PREFIX_SIZE
        if payload_start > len(smf_bytes):
            raise _rejectFile(f'chunk at byte {position} runs past the end of the file')

        chunk_type = smf_bytes[position : position + TYPE_SIZE].decode('latin-1')
        payload_end = payload_start + int.from_bytes(smf_bytes[position + TYPE_SIZE : payload_start], 'big')
        if payload_end > len(smf_bytes):
            raise _rejectFile(f'{chunk_type} chunk at byte {position} runs past the end of the file')

        chunks.append(_Chunk(chunk_type, smf_bytes[payload_start:payload_end]))
        position = payload_end

    return chunks


def _parseHeader(header_payload: bytes) -> SmfHeader:
    HEADER_SIZE = 6
    SMPTE_FLAG = 0x8000
    if len(header_payload) < HEADER_SIZE:
        raise _rejectFile(f'MThd chunk has {len(header_payload)} bytes, fewer than {HEADER_SIZE}')

    division = int.from_bytes(header_payload[4:6], 'big')
    if division & SMPTE_FLAG:
        raise _rejectFile('SMPTE time is not supported')
    if division == 0:
        raise _rejectFile('division is 0 ticks per quarter note')

    return SmfHeader(format=int.from_bytes(header_payload[0:2], 'big'), ticks_per_quarter=division)


def _parseTrack(track_payload: bytes, track_number: int) -> Track:
    """Read the events of one track chunk up to its end-of-track event.

    Raises:
        UnreadableFileError: an event runs past the end of the chunk, a data byte comes before any
            channel status, or a status byte is a system common or real-time message.
    """
    STATUS_BIT = 0x80
    SYSTEM_MESSAGES = 0xF0
    META = 0xFF
    SYSEX = (0xF0, 0xF7)
    END_OF_TRACK = 0x2F
    reader = _TrackReader(track_payload, track_number)
    events: list[TrackEvent] = []
    tick = Tick(0)
    running_status: int | None = None
    while not reader.exhausted():
        tick = Tick(tick + reader.readVariableLength())
        status = reader.readByte()

        if status == META:
            meta_type = reader.readByte()
            meta_data = reader.readBytes(reader.readVariableLength())
            if meta_type == END_OF_TRACK:
                return Track(tuple(events), tick)
            events.extend(_decodeMetaEvent(tick, meta_type, meta_data))
            continue

        if status in SYSEX:
            reader.readBytes(reader.readVariableLength())
            continue

        if status < STATUS_BIT:
            if running_status is None:
                raise reader.rejectEvent('data byte before any channel status')
            reader.unreadByte()
            status = running_status
        elif status >= SYSTEM_MESSAGES:
            raise reader.rejectEvent(f'status byte 0x{status:02X} has no defined length in a MIDI file')
        running_status = status
        events.extend(_readChannelEvent(reader, tick, status))

    LOG.debug('smf.missing_end_of_track', extra={'track': track_number})
    return Track(tuple(events), tick)


def _decodeMetaEvent(tick: Tick, meta_type: int, meta_data: bytes) -> list[TrackEvent]:
    SET_TEMPO = 0x51
    TIME_SIGNATURE = 0x58
    if meta_type == SET_TEMPO and len(meta_data) == 3:
        return [TempoChange(tick, int.from_bytes(meta_data, 'big'))]
    if meta_type == TIME_SIGNATURE and len(meta_data) >= 2:
        return [TimeSignature(tick, numerator=meta_data[0], denominator=2 ** meta_data[1])]
    if meta_type in (SET_TEMPO, TIME_SIGNATURE):
        LOG.debug('smf.malformed_meta_event', extra={'meta_type': meta_type, 'length': len(meta_data)})

    return []


def _readChannelEvent(reader: _TrackReader, tick: Tick, status: int) -> list[TrackEvent]:
    NOTE_OFF = 0x8
    NOTE_ON = 0x9
    ONE_DATA_BYTE = (0xC, 0xD)
    CHANNEL_MASK = 0x0F
    kind = status >> 4
    channel = Channel((status & CHANNEL_MASK) + 1)
    first_data = reader.readByte()
    if kind in ONE_DATA_BYTE:
        return []

    second_data = reader.readByte()
    if kind == NOTE_ON and second_data > 0:
        return [NoteStart(tick, channel, Pitch(first_data))]
    if kind in (NOTE_OFF, NOTE_ON):
        return [NoteEnd(tick, channel, Pitch(first_data))]

    return []


### vocabulary #########################################################################


class _TrackReader:
    def __init__(self, track_payload: bytes, track_number: int) -> None:
        self.track_payload = track_payload
        self.track_number = track_number
        self.position = 0

    def exhausted(self) -> bool:
        return self.position >= len(self.track_payload)

    def readByte(self) -> int:
        return self.readBytes(1)[0]

    def unreadByte(self) -> None:
        self.position -= 1

    def readBytes(self, count: int) -> bytes:
        end = self.position + count
        if end > len(self.track_payload):
            raise self.rejectEvent('event runs past the end of the track')

        taken = self.track_payload[self.position : end]
        self.position = end
        return taken

    def readVariableLength(self) -> int:
        # 7 bits per byte, most significant first. The top bit is set on every byte but the last.
        value = 0
        while True:
            byte = self.readByte()
            value = (value << 7) | (byte & 0x7F)
            if byte < 0x80:
                return value

    def rejectEvent(self, reason: str) -> UnreadableFileError:
        return _rejectFile(f'track {self.track_number}, byte {self.position} of the chunk: {reason}')


@dataclass(frozen=True)
class _Chunk:
    chunk_type: str
    payload: bytes
