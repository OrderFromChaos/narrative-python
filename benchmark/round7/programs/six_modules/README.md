# What a six-module program does to the single-file reading order

Built after `R7-B01` chose six modules of 40 to 90 lines over one file of 340. That answer costs the
style its central metaphor, and this program is where the cost was measured.

The repository opens by claiming *"a module reads as a document: `main()` is the thesis, the workflow
functions are the argument in call order, and the types are a glossary at the back."* That is a
**whole-file** device. Six modules is six documents, and no thesis.

## The program

A collector service. Polls three instruments, parses their replies, writes readings to SQLite,
prunes what has aged out, reports each round. One instrument returns garbage every time, so the
degrade-and-report path of `Q24` runs on every round.

```
collector/__init__.py     0 lines, empty
collector/__main__.py    63 lines   main, framedReply, the reading map
collector/service.py     28 lines   pollForever
collector/poller.py      39 lines   pollRound, pollOne
collector/protocol.py    36 lines   parseFrame, verifyChecksum
collector/store.py       47 lines   openDatabase, insertReading, readingSeen, pruneOldReadings
collector/vocabulary.py  61 lines   every type that crosses, and the error hierarchy
                        274 lines
```

```
$ python3 -m collector
round 0: 2 read, 1 refused
round 1: 2 read, 1 refused
round 2: 2 read, 1 refused
$ echo $?
1
```

Clean on `ruff check`, `ruff format`, `pylint`, `mypy --strict` and `vermin -t=3.10`. `checks.py`
reports one finding, discussed below.

The program follows every block-A and block-B answer: types that cross live in `vocabulary.py`
(`R7-A02`, `R7-B07`), the error hierarchy is central (`R7-A04-revised`), the entry point owns the
database and passes it down (`R7-A03`), `__main__.py` holds `main` (`R7-B09`), and the poller
collects per-device failures rather than letting one kill the round (`R7-A08`, `Q24`).

## Finding 1 — the checker found the question before the question was asked

```
collector/__init__.py:1: NAR009 module has no docstring
```

This is the **first `__init__.py` in the repository**. There are none anywhere else, so `NAR009` had
never met one, and it rejects the ordinary correct content of an application package's `__init__.py`,
which is nothing.

Note it is not covered by the exemption `R7-B10-scope` just granted. That one is worded *exactly one
def*, and an empty `__init__.py` has none.

So `NAR009` now carries **two pending change requests** (`R7-B10`, `R7-B01-init`), both found in this
round, neither implemented. The acceptance gate wants a cost measurement first.

## Finding 2 — the map lives with `main()`, and the sideways reader pays

`R7-B01-map`. `__main__.py` opens with the thesis and the module list in reading order:

```python
"""Poll instruments over TCP and write readings to SQLite.

Read this file first. It is the thesis: main() names the whole workflow in the order it runs, and
each module below it holds one part.

    __main__.py   this file -- start here
    service.py    the poll loop that runs for the life of the process
    poller.py     one round, and one device inside it
    protocol.py   the bytes an instrument returns
    store.py      SQLite
    vocabulary.py every type the modules above pass between them
"""
```

A reader who starts there gets the whole program. A reader who arrives at `store.py` from a stack
trace or a grep gets this and nothing else:

```python
"""Hold readings in SQLite, and forget the ones that are too old."""
```

True, useful, and silent about the five siblings, the loop that drives it, and where to go next.
**Most readers do not arrive at the entry point.** That cost is accepted rather than solved. A
back-pointer per module — `store.py` saying "poller.py writes here" — was offered and not chosen.

## Finding 3 — the glossary is bounded by signatures

`R7-B07-bound`. `R7-B07` centralises types pre-emptively, which read literally would send every shape
to the glossary. It does not:

```python
magic, celsius, declared = struct.unpack(FRAME_FORMAT, raw)
```

Those three values live for four lines inside `parseFrame` and are never named. They stay unnamed.
The test is whether a shape appears in a parameter or return annotation — that makes it a type the
program has, and it centralises. A shape built and consumed inside one function is a step, not a
type. This is what keeps `vocabulary.py` an inventory of what modules pass between them rather than
of every intermediate value, and it is where `R7-B07` and `R7-A05-property` meet.

## Finding 4 — a stated preference the toolchain overrules

`R7-indent`. The preferred signature layout is a hanging double indent:

```python
def pollRound(
        connection: sqlite3.Connection,
        devices: tuple[DeviceEntry, ...],
        replies: dict[str, bytes],
        observed_at: EpochSeconds,
    ) -> RoundReport:
```

PEP 8 blesses this form, to distinguish arguments from the body, and the reason survives inspection:
under the shipped form a parameter line sits at the same indent as the first body line.

**`ruff format` rewrites it and has no setting for it.** Verified: it is Black-compatible, and Black
exposes no continuation-indent knob deliberately. Three ways out, all costly — switch formatters,
which breaks `tooling.md`'s ownership split and `R6-02`'s single-pipeline decision; fence every
multi-argument signature with `# fmt: off`, which `R2b-B2` licensed for a rare packed literal and
which would here be pervasive; or accept ruff's form, which the program does.

Recorded as a preference the toolchain overrules rather than dropped. A preference silently dropped
is how a style document starts lying.

`NAR003` is unaffected either way: it requires one positional argument per line above three, and says
nothing about the indent.

## Counter-argument, stated fairly

**274 lines is not 340, and six modules of 28 to 63 is not six of 40 to 90.** This program is a
smaller instance of the shape `R7-B01` chose, not that program. Whether the reading-order cost grows
or shrinks with size is unmeasured.

**The map has nothing checking it.** Six module names are typed into a docstring by hand. Nothing
verifies that those six are the six that exist, and `verify_docs.py` does not read this file. The
`__init__.py` option that was rejected has the same defect, so this is not an argument between the
options — it is an argument that the map is unverified wherever it lives.

**One finding is an artefact of the program being new.** `NAR009` firing on `__init__.py` is only a
defect if application packages are common in this style. The corpus has none, and until round 7 the
style had never produced a package at all.

## Reproduce

```bash
python3 -m collector                      # from this directory
python3 ../../../../skill/checks.py collector/
```
