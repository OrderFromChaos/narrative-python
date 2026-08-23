# A fact lives with the thing it is a property of

Built to settle `R7-A05`, which stalled. Three variants, one behaviour, fifteen files. The result
changed the question twice, and both changes came from the answerer reading the code rather than
from the argument.

## What the question started as

`R7-A05` established that a module's level is not its directory depth and not an entry in a declared
layer table. Two candidate tests were left, and no way to choose:

- **Reuse.** The module that could be lifted into another project unchanged is the lower one.
- **Domain change.** Name the real-world event that forces a module to change, then ask whether that
  same event forces the other one.

"Level" buys exactly one thing: **`X` is below `Y` means `Y` may import `X`, and `X` may not import
`Y`.** A level claim that decides no import is decoration.

## The program

A retry schedule for instruments whose firmware recovers at different speeds. Acme answers again
after about thirty seconds; Tesla reboots and needs about two minutes.

```
leak/    vocabulary.py  backoff.py  acme.py  tesla.py  main.py
fixed/   vocabulary.py  backoff.py  acme.py  tesla.py  main.py
owned/   vocabulary.py  backoff.py  acme.py  tesla.py  main.py
```

All three print the same two lines:

```
probe-01   41.50     1.0    2.0    4.0    8.0   16.0   30.0
probe-02   21.25     1.0    2.0    4.0    8.0   16.0   32.0
```

Style is identical and clean across all fifteen files, so placement is the only variable:

| | `ruff check` | `ruff format` | `pylint` | `mypy --strict` | `checks.py` | `vermin -t=3.10` |
|---|---|---|---|---|---|---|
| all three | pass | pass | pass | pass | 0 findings | pass |

## The three placements

**`leak/`** — the backoff module holds every vendor's recovery time.

```python
BASE_S = 1.0
VENDOR_CAPS_S = {'acme': 30.0, 'tesla': 120.0}


def nextDelay(vendor: str, attempt: int) -> Seconds:
    return Seconds(min(BASE_S * 2**attempt, VENDOR_CAPS_S[vendor]))
```

**`fixed/`** — the cap arrives as a value and each vendor module states its own. `main.py` still
builds the devices, so it knows every wire format and every magic byte.

**`owned/`** — each vendor module publishes one `VendorReader` carrying its devices, its reader and
its recovery time. `main.py` knows which vendors exist and nothing else about any of them.

```python
# owned/vocabulary.py
class FrameReader(Protocol):
    def __call__(self, frame: bytes) -> float: ...


@dataclass(frozen=True, slots=True)
class VendorReader:
    name: str
    devices: tuple[Device, ...]
    read_frame: FrameReader
```

```python
# owned/main.py -- the whole of what it knows about instruments
VENDORS = (acme.VENDOR, tesla.VENDOR)
```

The `Protocol` here is earned rather than speculative: two real implementations exist, which is
exactly `R2-01`'s test, and no test double is involved.

### A third finding fell out of the layout (`R7-A05-ordering`)

The first `owned/acme.py` put `DEVICES` at the foot of the file beside `VENDOR`. That is wrong, and
the reason is **who changes the value**:

```python
ACME_FORMAT = '<4sf'
RETRY_CAP_S = Seconds(30.0)
DEVICES = (Device(DeviceId('probe-01'), RETRY_CAP_S, struct.pack(ACME_FORMAT, b'ACME', 41.5)),)


def readAcme(frame: bytes) -> float: ...


VENDOR = VendorReader('acme', DEVICES, readAcme)
```

`DEVICES` is which probes this site actually has — an operator edits it, so it belongs in the
constant block at the top. `VENDOR` is a binding between code and code; only a developer touches it,
and it must follow the function it names, so the foot of the file is right.

This is `R3a-12`'s test — *could someone change this knowing only what the program does* — applied to
**order** rather than to module-level-against-function-local. `SKILL.md` already separates tunable
constants from design-baked globals with a blank line, and this names the criterion behind that
separation.

Note the collision. `DEVICES` is the most operator-facing constant in the file, so it wants to lead
the block, but its value references `ACME_FORMAT` and `RETRY_CAP_S`, so execution order forces it
last within the block. It **joins** the constant block rather than leading it, which is `R4-03`'s
precedent: ordering is forced by execution and you do not contort around it.

The shape that results for a library module: **tunable constants, then the functions, then the
interface binding that names them.**

## The change request

Support a Bosch B40, whose firmware clears a fault after about a minute. Applied to all three. All
three still run and still agree.

| | files touched | `main.py` gains |
|---|---|---|
| `leak/` | **3** — including `backoff.py` | the module import, the vendor string `'bosch'`, the format `'<4sf'`, the magic `b'BSCH'`, the value `101.3`, the id `probe-03`, the reader |
| `fixed/` | **2** | the module import, the format `'<4sf'`, the magic `b'BSCH'`, the value `101.3`, the id `probe-03`, two attribute references |
| `owned/` | **2** | `import bosch`, and `bosch.VENDOR` |

In `leak/` the module that reads as generic infrastructure had to change:

```diff
-VENDOR_CAPS_S = {'acme': 30.0, 'tesla': 120.0}
+VENDOR_CAPS_S = {'acme': 30.0, 'tesla': 120.0, 'bosch': 60.0}
```

## Two findings, and the second is the important one

### 1. The rule is ownership, not level

The reason `leak/` is wrong is not that an arrow points the wrong way. It is that **the recovery
time is a property of the manufacturer's networking stack, and `backoff.py` is not about the
manufacturer.** A fact belongs in the module that is about the thing the fact is a property of.

That subsumes the level question rather than answering it. It also subsumes three other round-7
answers that looked unrelated at the time:

- `R7-A01-revised` — `site_code` is a property of a `DeviceEntry`, so the lookup lives with
  `DeviceEntry` and the caller does not carry it.
- `R7-A04-revised` — an exception type is a property of the whole program, because any module may
  catch it, so it lives in the shared vocabulary and not in the module that raises it.
- The `LOG_FIELDS` case — a log field set is a property of whatever emits the record, not of the
  formatter.

Four answers, one rule. **Ask what the fact is a property of, and put it there.** The reuse test and
the domain-change test both turn out to be indirect ways of asking that, which is why they agree
whenever the fact is in the right place.

### 2. Counting files touched is the wrong measure, and this program shows why

`fixed/` and `owned/` both touch two files. By file count they are the same design. They are not.

The `fixed/` edit spells the wire format, the magic bytes, the reading and the device id into the
entry point. The `owned/` edit spells the word *bosch* twice. A reviewer looking at the `owned/` diff
does not need to know what a Bosch is; a reviewer looking at the `fixed/` diff has to check that
`'<4sf'` and `b'BSCH'` are right, and nothing in `main.py` gives them any way to check it.

So the measure is **what the edit has to know**, not how many files it lands in. That is independent
support for `R7-M01`, which rejected both file-count metrics on the way in — and it arrives from code
rather than from preference.

## Counter-argument, stated fairly

**`owned/` distributes a table.** All three recovery times sat on one readable line in `leak/`. An
operator asking "which of our instruments is slowest to recover" now greps three files. This is the
standard price of distributing a table and the program does not measure it.

**`owned/` costs a `Protocol` and a wrapper record.** `vocabulary.py` grows `FrameReader` and
`VendorReader`, which is fourteen lines that exist only so `main.py` can iterate uniformly. `R7-M02`
prices a named type as the cheapest of the three costs, which licenses this — but it is licence, not
evidence, and a smaller program would not repay it.

**One example is one example.** The claim that the two tests only disagree where a fact is misplaced
was not proven. No counter-example was built, and the argument for why one cannot exist is close to
circular: "a domain change forces this generic module" and "this generic module holds a domain fact"
are nearly the same sentence.

**`main.py` still changes.** No variant reaches the ideal of one new file and nothing else. Something
must name the new module. Getting to one would need a registry that discovers modules at import,
which `R7-A06` already rejected on readability, so two is the floor here rather than a shortfall.

## Open question

The ownership rule says where a fact goes once you know what it is a property of. It says nothing
about **facts that are genuinely a property of two things**. A frame format is a property of the
vendor and also of the wire protocol that the fixture generator writes; `R7-A05` sent that one to a
shared module beside both readers. Whether that is a third case or the same rule with "the pair" as
the owner is unsettled.

## Reproduce

```bash
cd leak  && python3 main.py
cd fixed && python3 main.py
cd owned && python3 main.py
python3 ../../../../skill/checks.py .
```
