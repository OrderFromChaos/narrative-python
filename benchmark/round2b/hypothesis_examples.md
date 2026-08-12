# R2-12 follow-up — where do property-based tests sit?

You asked to see examples before deciding. Three real cases from the scan-ingest domain, each
shown as an example-based test and as a hypothesis property. For each: **which would you require,
which would you accept, which is not worth it?**

Note the interaction with R2-02 (real IO, doubles only for what you cannot run): hypothesis works
best on pure functions, so this question is partly "how much pure surface should exist to test."

---

## H1 — round-trip: header pack/unpack

```python
# Example-based
def test_parseHeader_reads_a_known_good_header() -> None:
    raw = struct.pack('<4sHI12sIHI', b'ISCN', 2, 4711, b'SP-0001', 65536, 8, 0)
    header = parseHeader(raw)
    assert header.scan_id == 4711
    assert header.sample_ref == 'SP-0001'
    assert header.pixel_count == 65536


# Property
@given(
    scan_id=st.integers(min_value=0, max_value=2**32 - 1),
    sample_ref=st.text(alphabet=string.ascii_uppercase + string.digits + '-', min_size=1, max_size=12),
    pixel_count=st.integers(min_value=0, max_value=2**32 - 1),
    repetitions=st.integers(min_value=0, max_value=2**16 - 1),
)
def test_parseHeader_roundtrips(scan_id: int, sample_ref: str, pixel_count: int, repetitions: int) -> None:
    raw = packHeader(scan_id, sample_ref, pixel_count, repetitions)
    header = parseHeader(raw)
    assert (header.scan_id, header.sample_ref, header.pixel_count, header.repetitions) == (
        scan_id, sample_ref, pixel_count, repetitions,
    )
```

*The property found the real bug class here: a `sample_ref` of exactly 12 chars has no null
terminator, so `rstrip(b'\x00')` returns it intact — but an 11-char ref ending in a literal
`'\x00'`-lookalike, or a ref containing a null byte, breaks the round-trip. You would probably
never write that example by hand.*

---

## H2 — numeric invariant: intensity normalisation

```python
# Example-based
def test_normaliseIntensity_scales_to_unit_range() -> None:
    assert normaliseIntensity(bytes([0, 128, 255]), floor=0) == [0.0, 128 / 255, 1.0]


# Property
@given(
    frame=st.binary(min_size=1, max_size=4096),
    floor=st.integers(min_value=0, max_value=255),
)
def test_normaliseIntensity_output_is_bounded_and_same_length(frame: bytes, floor: int) -> None:
    out = normaliseIntensity(frame, floor)
    assert len(out) == len(frame)
    assert all(0.0 <= v <= 1.0 for v in out)
```

*Three properties are available and none is the actual computation restated: length preservation,
range boundedness, and monotonicity (a brighter input pixel never maps to a dimmer output). The
example test asserts the arithmetic, which is a restatement of the implementation.*

---

## H3 — stateful/IO: idempotent ingest

```python
# Example-based, real SQLite in a temp dir (per R2-02)
def test_ingesting_the_same_file_twice_inserts_one_row(tmp_path: Path) -> None:
    writeScanFile(tmp_path / 'a.scan', scan_id=1)
    ingestDirectory(tmp_path)
    ingestDirectory(tmp_path)
    assert countRows(tmp_path / 'scans.db') == 1


# Property, stateful
class IngestMachine(RuleBasedStateMachine):

    @rule(scan_id=st.integers(min_value=1, max_value=20))
    def ingestOne(self, scan_id: int) -> None:
        writeScanFile(self.incoming / f'{scan_id}.scan', scan_id=scan_id)
        ingestDirectory(self.incoming)
        self.seen.add(scan_id)

    @invariant()
    def rowCountMatchesDistinctScanIds(self) -> None:
        assert countRows(self.db_path) == len(self.seen)
```

*The stateful machine generates arbitrary interleavings of ingest and re-ingest and checks the
idempotency invariant after every step. It is genuinely more powerful. It is also slow (real
SQLite per step), and when it fails the shrunk counterexample can take real effort to read.*
