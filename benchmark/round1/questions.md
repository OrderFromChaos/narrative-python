# Round 1 — forced-choice snippets

**Answer as if you had infinite time and effort.** Not "what would I type under deadline" —
what is the *best possible* version. These two answers are known to differ; only the second is
being measured.

Every pair is behaviourally identical. Only one dimension varies per question — if you find
yourself weighing two things at once, say so, that is a bug in the question.

"Depends" is a real answer. Give the condition in one line and it gets recorded as a conditional
rule rather than a flat one.

Do not read `key.md` until you have answered. It names what each question probes.

---

## Q01

```python
# A
def summariseRun(scan_count: int) -> str:
    return f'{SITE_CODE}: {scan_count} scans, retention {RETENTION_DAYS}d'

# B
def summariseRun(scan_count: int) -> str:
    global RETENTION_DAYS, SITE_CODE
    return f'{SITE_CODE}: {scan_count} scans, retention {RETENTION_DAYS}d'
```

---

## Q02

```python
# A
def parseScanPayload(raw: bytes) -> dict[str, int | float | str]:
    header, body = raw[:32], raw[32:]
    return {
        'scan_id': int.from_bytes(header[4:8], 'little'),
        'sample_ref': header[8:20].rstrip(b'\x00').decode('ascii'),
        'pixel_count': int.from_bytes(header[20:24], 'little'),
        'mean_intensity': sum(body) / len(body),
    }

# B
@dataclass(frozen=True, slots=True)
class ScanPayload:
    scan_id: int
    sample_ref: str
    pixel_count: int
    mean_intensity: float


def parseScanPayload(raw: bytes) -> ScanPayload:
    header, body = raw[:32], raw[32:]
    return ScanPayload(
        scan_id=int.from_bytes(header[4:8], 'little'),
        sample_ref=header[8:20].rstrip(b'\x00').decode('ascii'),
        pixel_count=int.from_bytes(header[20:24], 'little'),
        mean_intensity=sum(body) / len(body),
    )
```

---

## Q03

```python
# A
CALIBRATION_HELP = (
    'Calibration failed. Check that the stage is homed, then re-run with --recalibrate. '
    'If the fault persists, the reference cell may be out of date; see runbook section 4.'
)

# B
CALIBRATION_HELP = textwrap.dedent("""
    Calibration failed. Check that the stage is homed, then re-run with --recalibrate.
    If the fault persists, the reference cell may be out of date; see runbook section 4.
""").strip()
```

---

## Q04

```python
# A
class ScanSession:

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.last_error: str | None = None

    def run(self) -> None:
        self.frame_buffer = self.acquire()

# B
class ScanSession:

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.last_error: str | None = None
        self.frame_buffer: bytes | None = None

    def run(self) -> None:
        self.frame_buffer = self.acquire()
```

---

## Q05

```python
# A
def normaliseIntensity(frame: bytes, floor: int) -> list[float]:
    # Values below the noise floor are clamped rather than dropped, so the output
    # length always matches pixel_count and downstream reshape stays valid.
    # Returns values in [0.0, 1.0]. Raises ValueError on an empty frame.
    if not frame:
        raise ValueError('frame is empty')
    span = max(max(frame) - floor, 1)
    return [max(v - floor, 0) / span for v in frame]

# B
def normaliseIntensity(frame: bytes, floor: int) -> list[float]:
    """Scale a frame to [0.0, 1.0], clamping at the noise floor."""
    if not frame:
        raise ValueError('frame is empty')
    span = max(max(frame) - floor, 1)
    return [max(v - floor, 0) / span for v in frame]

# C
def normaliseIntensity(frame: bytes, floor: int) -> list[float]:
    """Scale a frame to [0.0, 1.0], clamping at the noise floor.

    Values below the floor are clamped rather than dropped, so the output length
    always matches pixel_count and the downstream reshape stays valid.

    Args:
        frame: Raw 8-bit intensity samples.
        floor: Noise floor; samples at or below this map to 0.0.

    Returns:
        One float in [0.0, 1.0] per input sample.

    Raises:
        ValueError: If frame is empty.
    """
    if not frame:
        raise ValueError('frame is empty')
    span = max(max(frame) - floor, 1)
    return [max(v - floor, 0) / span for v in frame]
```

---

## Q06

```python
# A
def routeScan(scan: ScanPayload, config: SiteConfig) -> Path:
    if scan.pixel_count == config.expected_pixel_count:
        if scan.sample_ref in config.known_refs:
            if not config.archive_root.exists():
                config.archive_root.mkdir(parents=True)
            return config.archive_root / f'{scan.scan_id}.scan'
        else:
            return config.quarantine_root / f'{scan.scan_id}.scan'
    else:
        return config.quarantine_root / f'{scan.scan_id}.scan'

# B
def routeScan(scan: ScanPayload, config: SiteConfig) -> Path:
    if scan.pixel_count != config.expected_pixel_count:
        return config.quarantine_root / f'{scan.scan_id}.scan'
    if scan.sample_ref not in config.known_refs:
        return config.quarantine_root / f'{scan.scan_id}.scan'

    if not config.archive_root.exists():
        config.archive_root.mkdir(parents=True)
    return config.archive_root / f'{scan.scan_id}.scan'
```

---

## Q07

```python
# A
recent_faults = [
    (entry.scan_id, entry.reason)
    for entry in log_entries
    if entry.level == 'ERROR' and entry.timestamp >= cutoff
    if entry.reason not in SUPPRESSED_REASONS
]

# B
recent_faults = []
for entry in log_entries:
    if entry.level != 'ERROR' or entry.timestamp < cutoff:
        continue
    if entry.reason in SUPPRESSED_REASONS:
        continue
    recent_faults.append((entry.scan_id, entry.reason))
```

---

## Q08

```python
# A
LOG.info('%s ingested, %d px, site %s', scan.sample_ref, scan.pixel_count, site_code)

# B
LOG.info(f'{scan.sample_ref} ingested, {scan.pixel_count} px, site {site_code}')

# C
LOG.info(
    'scan_ingested',
    extra={
        'sample_ref': scan.sample_ref,
        'pixel_count': scan.pixel_count,
        'site_code': site_code,
    },
)
```

---

## Q09

```python
# A
def fetchScanMetadata(scan_ids: list[int]) -> list[ScanMeta]:
    out: list[ScanMeta] = []
    for batch in batched(scan_ids, 50):  # API caps a request at 50 ids
        out.extend(requestBatch(batch))
    return out

# B
API_MAX_IDS_PER_REQUEST = 50


def fetchScanMetadata(scan_ids: list[int]) -> list[ScanMeta]:
    out: list[ScanMeta] = []
    for batch in batched(scan_ids, API_MAX_IDS_PER_REQUEST):
        out.extend(requestBatch(batch))
    return out
```

---

## Q10

```python
# A
if __name__ == '__main__':

    INPUT_DIR = Path('~/scans/incoming').expanduser()
    DRY_RUN = False

    db = openDatabase(INPUT_DIR.parent / 'scans.db')
    config = loadSiteConfig(INPUT_DIR.parent / 'sites.json')

    outcomes = []
    for path in sorted(INPUT_DIR.glob('*.scan')):
        outcomes.append(ingestOne(path, db, config, dry_run=DRY_RUN))

    print(f'{sum(o.ok for o in outcomes)}/{len(outcomes)} ingested')

# B
def main() -> int:
    input_dir = Path('~/scans/incoming').expanduser()

    db = openDatabase(input_dir.parent / 'scans.db')
    config = loadSiteConfig(input_dir.parent / 'sites.json')

    outcomes = [ingestOne(path, db, config, dry_run=False) for path in sorted(input_dir.glob('*.scan'))]

    print(f'{sum(o.ok for o in outcomes)}/{len(outcomes)} ingested')
    return 0 if all(o.ok for o in outcomes) else 1


if __name__ == '__main__':
    sys.exit(main())
```

---

## Q11

```python
# A
def rebinFrames(img_arr: np.ndarray, cfg: RebinConfig) -> np.ndarray:
    out = np.zeros_like(img_arr)
    for idx, row in enumerate(img_arr):
        out[idx] = row.reshape(-1, cfg.factor).mean(axis=1)
    return out

# B
def rebinFrames(image_array: np.ndarray, config: RebinConfig) -> np.ndarray:
    output = np.zeros_like(image_array)
    for index, row in enumerate(image_array):
        output[index] = row.reshape(-1, config.factor).mean(axis=1)
    return output

# C
def rebinFrames(image_array: np.ndarray, rebin_config: RebinConfig) -> np.ndarray:
    out = np.zeros_like(image_array)
    for i, row in enumerate(image_array):
        out[i] = row.reshape(-1, rebin_config.factor).mean(axis=1)
    return out
```

---

## Q12

```python
# A
def readyForScan(device: Device) -> bool:
    return device.state is DeviceState.READY and device.calibration_age_days < 30

# B
def isReadyForScan(device: Device) -> bool:
    return device.state is DeviceState.READY and device.calibration_age_days < 30

# C
def checkReadyForScan(device: Device) -> bool:
    return device.state is DeviceState.READY and device.calibration_age_days < 30
```

---

## Q13

```python
# A
def totalPixels(scans: list[ScanPayload]) -> int:
    return sum(s.pixel_count for s in scans)

# B
def totalPixels(scans: Sequence[ScanPayload]) -> int:
    return sum(s.pixel_count for s in scans)

# C
def totalPixels(scans: Iterable[ScanPayload]) -> int:
    return sum(s.pixel_count for s in scans)
```

---

## Q14

A site-config file arrives as JSON from a spreadsheet export. You index into it immediately and
pass it around the application.

```python
# A
def loadSiteConfig(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


expected = loadSiteConfig(p)['sites'][ref]['expected_pixel_count']

# B
class SiteEntry(TypedDict):
    expected_pixel_count: int
    site_code: str


class SiteConfigFile(TypedDict):
    sites: dict[str, SiteEntry]


def loadSiteConfig(path: Path) -> SiteConfigFile:
    return json.loads(path.read_text())


expected = loadSiteConfig(p)['sites'][ref]['expected_pixel_count']

# C
@dataclass(frozen=True, slots=True)
class SiteEntry:
    expected_pixel_count: int
    site_code: str


def loadSiteConfig(path: Path) -> dict[str, SiteEntry]:
    raw = json.loads(path.read_text())
    return {ref: SiteEntry(**entry) for ref, entry in raw['sites'].items()}


expected = loadSiteConfig(p)[ref].expected_pixel_count
```

---

## Q15

```python
# A
def linkScanToSample(scan_id: int, sample_ref: str) -> None:
    DB.execute('INSERT INTO scan_sample VALUES (?, ?)', (scan_id, sample_ref))

# B
ScanId = NewType('ScanId', int)
SampleRef = NewType('SampleRef', str)


def linkScanToSample(scan_id: ScanId, sample_ref: SampleRef) -> None:
    DB.execute('INSERT INTO scan_sample VALUES (?, ?)', (scan_id, sample_ref))
```

---

## Q16

You need to swap the real socket transport for a fake one in tests.

```python
# A
class Transport(Protocol):

    def send(self, payload: bytes) -> None: ...

    def recvLine(self, timeout_s: float) -> bytes: ...


def pollDevice(transport: Transport) -> Reading: ...

# B
class Transport(ABC):

    @abstractmethod
    def send(self, payload: bytes) -> None: ...

    @abstractmethod
    def recvLine(self, timeout_s: float) -> bytes: ...


class SocketTransport(Transport): ...


def pollDevice(transport: Transport) -> Reading: ...

# C
def pollDevice(transport: SocketTransport) -> Reading: ...
```

---

## Q17

```python
# A
def loadThresholds(path: Path) -> dict:
    data = json.loads(path.read_text())
    return data['thresholds']

# B
def loadThresholds(path: Path) -> dict[str, float]:
    data: dict[str, Any] = json.loads(path.read_text())
    thresholds = data['thresholds']
    assert isinstance(thresholds, dict)
    return cast(dict[str, float], thresholds)
```

---

## Q18

```python
# A
def describeOutcome(outcome: Outcome) -> str:
    if outcome is Outcome.INGESTED:
        return 'ingested'
    elif outcome is Outcome.QUARANTINED:
        return 'quarantined'
    elif outcome is Outcome.SKIPPED_DUPLICATE:
        return 'skipped (duplicate)'
    else:
        raise ValueError(f'unhandled outcome: {outcome}')

# B
def describeOutcome(outcome: Outcome) -> str:
    match outcome:
        case Outcome.INGESTED:
            return 'ingested'
        case Outcome.QUARANTINED:
            return 'quarantined'
        case Outcome.SKIPPED_DUPLICATE:
            return 'skipped (duplicate)'
        case _ as unreachable:
            assert_never(unreachable)
```

---

## Q19

```python
# A
def ingestOne(path: Path) -> Outcome:
    try:
        raw = path.read_bytes()
        header = parseHeader(raw)
        site = SITE_CONFIG[header.sample_ref]
        DB.execute('INSERT INTO scans VALUES (?, ?)', (header.scan_id, site.site_code))
    except (OSError, struct.error, KeyError, sqlite3.IntegrityError):
        return Outcome.QUARANTINED
    return Outcome.INGESTED

# B
def ingestOne(path: Path) -> Outcome:
    raw = path.read_bytes()

    try:
        header = parseHeader(raw)
    except struct.error:
        return Outcome.QUARANTINED

    site = SITE_CONFIG.get(header.sample_ref)
    if site is None:
        return Outcome.QUARANTINED

    try:
        DB.execute('INSERT INTO scans VALUES (?, ?)', (header.scan_id, site.site_code))
    except sqlite3.IntegrityError:
        return Outcome.SKIPPED_DUPLICATE

    return Outcome.INGESTED
```

---

## Q20

```python
# A
if header.magic != EXPECTED_MAGIC:
    raise ValueError(f'bad magic {header.magic!r}, expected {EXPECTED_MAGIC!r}')

# B
class CorruptScanFile(Exception):
    pass


if header.magic != EXPECTED_MAGIC:
    raise CorruptScanFile(f'bad magic {header.magic!r}, expected {EXPECTED_MAGIC!r}')
```

---

## Q21

```python
# A
try:
    site = SITE_CONFIG[header.sample_ref]
except KeyError:
    raise UnknownSampleRef(header.sample_ref) from None

# B
try:
    site = SITE_CONFIG[header.sample_ref]
except KeyError as exc:
    raise UnknownSampleRef(header.sample_ref) from exc

# C
try:
    site = SITE_CONFIG[header.sample_ref]
except KeyError:
    LOG.exception('unknown sample ref %s', header.sample_ref)
    raise
```

---

## Q22

```python
# A
def loadCalibration(path: Path) -> Calibration:
    if not path.exists():
        return DEFAULT_CALIBRATION
    if not path.is_file():
        raise CalibrationError(f'{path} is not a file')
    return parseCalibration(path.read_text())

# B
def loadCalibration(path: Path) -> Calibration:
    try:
        return parseCalibration(path.read_text())
    except FileNotFoundError:
        return DEFAULT_CALIBRATION
    except IsADirectoryError as exc:
        raise CalibrationError(f'{path} is not a file') from exc
```

---

## Q23

```python
# A
def parseHeader(raw: bytes) -> ScanHeader:
    if len(raw) < HEADER_BYTES:
        LOG.error('short header: %d bytes', len(raw))
        raise CorruptScanFile(f'short header: {len(raw)} bytes')
    ...


def ingestOne(path: Path) -> Outcome:
    try:
        header = parseHeader(path.read_bytes())
    except CorruptScanFile:
        return Outcome.QUARANTINED

# B
def parseHeader(raw: bytes) -> ScanHeader:
    if len(raw) < HEADER_BYTES:
        raise CorruptScanFile(f'short header: {len(raw)} bytes')
    ...


def ingestOne(path: Path) -> Outcome:
    try:
        header = parseHeader(path.read_bytes())
    except CorruptScanFile as exc:
        LOG.error('quarantining %s: %s', path.name, exc)
        return Outcome.QUARANTINED
```

---

## Q24

A nightly batch of ~400 scan files. One file has a corrupt header.

```python
# A
def ingestDirectory(input_dir: Path) -> int:
    outcomes: list[tuple[Path, Outcome]] = []
    for path in sorted(input_dir.glob('*.scan')):
        outcomes.append((path, ingestOne(path)))

    failed = [p for p, o in outcomes if o is Outcome.QUARANTINED]
    LOG.info('ingested %d, quarantined %d', len(outcomes) - len(failed), len(failed))
    for path in failed:
        LOG.warning('quarantined %s', path.name)
    return 1 if failed else 0

# B
def ingestDirectory(input_dir: Path) -> int:
    for path in sorted(input_dir.glob('*.scan')):
        outcome = ingestOne(path)
        if outcome is Outcome.QUARANTINED:
            # A corrupt file means the acquisition station is misconfigured; the rest of
            # tonight's batch is suspect too, so stop rather than ingest bad data.
            LOG.error('aborting batch at %s', path.name)
            return 1
    return 0
```
