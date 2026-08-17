# NAR005 is wrong about coordinates and blind to callables

Real code. Five runnable 97–133 line programs that read a `name,x,y` CSV and report arc length and
bounding box per series. The four in Part 1 produce identical output on the same 1,200-row fixture,
and all five pass `ruff check`, `ruff format`, `pylint`, `mypy --strict` and `vermin -t=3.10`
**clean**. Only `checks.py` differs. The patched checker below also passes the full toolchain itself.

## Part 1 — the rule's own remedy buys no type safety

```python
# b1_tuple.py -- depth 3.  b1_tuple.py:55: NAR005 depth 3: dict[str, list[tuple[float, float]]]
def loadSeries(source: Path) -> dict[str, list[tuple[float, float]]]:
def parsePoint(row: list[str]) -> tuple[float, float]:
    return float(row[X_COLUMN]), float(row[Y_COLUMN])

# b2_point.py -- depth 2, NAR005 clean. The promotion the rule asks for.
def loadSeries(source: Path) -> dict[str, list[Point]]:
def parsePoint(row: list[str]) -> Point:
    return Point(float(row[X_COLUMN]), float(row[Y_COLUMN]))

@dataclass(frozen=True)
class Point:
    x: float
    y: float

# the genuine error, injected identically into all four forms -- CSV columns read swapped
    return float(row[Y_COLUMN]), float(row[X_COLUMN])          # b1
    return Point(float(row[Y_COLUMN]), float(row[X_COLUMN]))   # b2
```

| | annotation | lines | NAR005 | `mypy --strict` catches the swap |
|---|---|---|---|---|
| b1 tuple of float | `dict[str, list[tuple[float, float]]]` | 97 | **depth 3, fires** | **no** |
| b2 Point dataclass | `dict[str, list[Point]]` | 107 | clean | **no** |
| b3 tuple of NewType | `dict[str, list[tuple[XCoord, YCoord]]]` | 105 | **depth 3, fires** | **yes** |
| b2n Point of NewType | `dict[str, list[Point]]` | 112 | clean | **yes** |

```
bug_b3_newtype.py:80: error: Incompatible return value type
  (got "tuple[YCoord, XCoord]", expected "tuple[XCoord, YCoord]")  [return-value]
bug_b2n_point_newtype.py:81: error: Argument 1 to "Point" has incompatible type "YCoord"; expected "XCoord"
```

**The safety comes entirely from `NewType`, and is orthogonal to tuple-vs-dataclass.** The 2×2 is
decisive: the form NAR005 mandates (b2) catches nothing, and one of the two forms that *do* catch the
bug (b3) is flagged by NAR005. Following the rule as written moves you from b1 to b2 — ten extra
lines, zero errors caught. Following Q15 instead moves you from b1 to b3 — eight extra lines, the
error caught, and a NAR005 finding to suppress.

Cost, 1,000,000 points, `time.perf_counter` on 3.10.18 (the floor), `tracemalloc` peak:

| | build | walk | peak RSS |
|---|---|---|---|
| `tuple[float, float]` | 0.698 s | 0.133 s | 107.2 MiB |
| `Point` frozen dataclass | 1.656 s (**2.37×**) | 0.184 s (1.38×) | 198.8 MiB (**1.85×**) |
| `Point` frozen, `slots=True` | 1.091 s (1.56×) | 0.168 s (1.26×) | 99.6 MiB (0.93×) |

Material at this size. `slots=True` recovers the memory and none of the construction cost. On 3.14 the
gap narrows to 1.52× / 1.20×, so this is a floor-version penalty, not a permanent one.

## Part 2 — the hole is real, and asymmetric

`annotationDepth` recurses only through `ast.Subscript`. A callable's parameter list parses as
`ast.List`, which scores 0 and hides everything inside it. Confirmed by running the shipped function:

```
depth 3  FIRES   dict[str, list[tuple[float, float]]]
depth 1  passes  Callable[[int, str], None]
depth 1  passes  Callable[[str, list[tuple[float, float]]], str | None]
depth 1  passes  Callable[[dict[str, list[tuple[float, float]]],
                           Mapping[str, Sequence[frozenset[Path]]]], None]
depth 1  passes  Callable[[Callable[[dict[str, list[tuple[float, float]]]], None]], None]
depth 4  FIRES   Callable[[int], dict[str, list[tuple[float, float]]]]
```

The claim holds, and the last line adds what GAPS did not: the blindness is **positional inside one
annotation**. The callable's *return* type is measured; its parameter list is not. The same type scores
4 in return position and 0 in parameter position. `b4_callable.py` puts both on adjacent lines of one
signature. It runs, exits 0 on both checks, and `checks.py` reports three findings — none the callables:

```python
def runCheck(
    series: dict[str, list[tuple[float, float]]],                    # depth 3 -- FIRES
    check: Callable[[str, list[tuple[float, float]]], str | None],   # depth 1 -- silent
) -> dict[str, str]:

def registerSink(
    sink: Callable[
        [dict[str, list[tuple[float, float]]], Mapping[str, Sequence[frozenset[Path]]]],
        None,
    ],
) -> int:                                                            # depth 1 -- silent
```

## The fix, and what it costs

Two clauses in `annotationDepth`, in a copy of `checks.py` (`checks_nar005.py`):

1. **Recurse through `ast.List` without charging a level.** A parameter list is syntax, not a type
   constructor, so it must not cost a level — but what it holds is real nesting.
   `Callable[[int, str], None]` stays at 1.
2. **`leafTuple`: a fixed-arity tuple whose every element is a bare type reference charges 0.**
   `tuple[float, float]` and `tuple[XCoord, YCoord]` are records with named positions and no inner
   structure to unfold; `tuple[str, list[int]]` is a container and still charges 1.

| findings | conformant corpus (10 files, 436 annotations) | wider repo (26 files, 1,537 annotations) | b1 | b3 | b4 |
|---|---|---|---|---|---|
| current | 0 | 2 | 2 | 2 | 3 |
| clause 1 only | 0 | 2 (0 new) | 2 | 2 | **6** |
| clause 2 only | 0 | 2 (0 new) | **0** | **0** | 0 |
| both | **0** | **2 (0 new)** | **0** | **0** | **2** |

**Zero regressions.** Not one annotation anywhere in the repo is newly flagged. The two pre-existing
findings, `list[tuple[str, int, list[LogRecord]]]` in `validation/`, survive all four modes — clause 2
does not gut the rule, because that tuple holds a `list`. What the fix newly catches in `b4`, correctly:

```
b4_callable.py:73:  NAR005 depth 4: Callable[[dict[str, list[tuple[float, float]]],
                      Mapping[str, Sequence[frozenset[Path]]]], None]
b4_callable.py:126: NAR005 depth 3: dict[str, Callable[[str, list[tuple[float, float]]], str | None]]
```

## Recommendation

Ship both clauses, and amend the rule text. "Promote it to a dataclass" is the wrong instruction: a
dataclass fixes depth and catches nothing. It should read **"name the inner type"** — satisfied by a
dataclass, a `NewType`, or a type alias. Line 126 above is fixed by
`Check = Callable[[str, list[tuple[float, float]]], str | None]`, not by a dataclass.

Counter-argument, stated fairly. Clause 2 is a special case carved for one shape, and special cases
accumulate; a reviewer could reasonably say `tuple[float, float]` inside `dict[str, list[...]]` really
is three levels of unfolding that the reader does pay for. Clause 1 imposes a *new* obligation nobody
asked for — `dict[str, Callable[...]]` registry types now need an alias. And zero regressions is weaker
evidence than it looks: the corpus contains **no** `Callable` annotation deep enough to move, so clause
1 is measured only against `b4`, which was written to exercise it.

**Question: should NAR005 measure how deep an annotation nests, or how many distinct unnamed types a
reader must hold at once? `tuple[float, float]` is two levels and zero unnamed concepts;
`Callable[[dict[str, list[tuple[float, float]]]], None]` is one level and four.**
