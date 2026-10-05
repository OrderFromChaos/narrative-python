# Comments for review: cleanup of code written without the skill

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Skill before R10-cleanup-rewrite and R10-subject-verb: 26 comments

`scratchpad/cleanup/review/old`

### 1. chest-attribution.py:1

```python
>>    1 #!/usr/bin/env python3
      2 """Sort the chests of a corpus by loot source, and count the chests with no known source.
      3 
      4 Each chest inside the corpus window goes to the first bucket that matches:
      5 
      6     predicted                    the prefilter has a chest at this XZ
      7     <traced source>              --trace has a fill at this position from a known generator class
      8     traced-unrecognised-caller   --trace has a fill at this position from any other class
      9     village-piece                in a village piece the prefilter laid out, with items: a chest-site table miss
     10     village-piece-empty          in a village piece the prefilter laid out, with no items: furniture
     11     thaumcraft-hilltop           listed by --thaumcraft, or on a WorldGenHilltopStones pedestal in a --dump
```

### 2. chest-attribution.py:76

```python
     68 from collections.abc import Iterable, Mapping
     69 from dataclasses import dataclass
     70 from enum import Enum
     71 from pathlib import Path
     72 from types import ModuleType
     73 
     74 
     75 NEAR_BLOCKS = 16
>>   76 # Vanilla WorldGenDungeons chests are not confined to low Y. On beta-3 seed -1636594104014467454
>>   77 # they run from Y41 to Y58 inside the spawn window. 64 is sea level.
     78 DEEP_Y = 64
     79 DEFAULT_SHOW = 30
     80 UNKNOWN_CALLERS_SHOWN = 12
     81 EXIT_SUCCESS = 0
     82 EXIT_NOTHING_TO_ATTRIBUTE = 1
     83 EXIT_USAGE = 2
     84 
     85 
     86 def main() -> int:
     87     """Attribute every corpus chest inside its window, then print a report per seed and the totals."""
```

### 3. chest-attribution.py:95

```python
     87     """Attribute every corpus chest inside its window, then print a report per seed and the totals."""
     88     judge = loadJudge()
     89     arguments = parseArguments(sys.argv)
     90     if arguments is None:
     91         print(__doc__)
     92         return EXIT_USAGE
     93 
     94     corpus = readCorpus(judge, arguments.raw_corpus_path)
>>   95     # without this check, an empty corpus exits 0 with no seed section, which looks like success
     96     if not any(window.chests for window in corpus.values()):
     97         print(
     98             f'NOTHING TO ATTRIBUTE: {arguments.raw_corpus_path} yielded no chests '
     99             f'({len(corpus)} seed(s) loaded). An empty attribution is not a complete '
    100             'one — check the reports carry a chest search.',
    101             file=sys.stderr,
    102         )
    103         return EXIT_NOTHING_TO_ATTRIBUTE
    104 
    105     predictions = judge.load_prefilter(str(arguments.prefilter_path))
```

### 4. chest-attribution.py:156

```python
    148 
    149 
    150 def loadJudge() -> ModuleType:
    151     """Load prefilter-judge-chests.py from the directory of this file.
    152 
    153     Raises:
    154         JudgeLoadError: Python has no loader for the file.
    155     """
>>  156     # A copy of the judge's readers would drift from the sections it scores as predictions.
>>  157     # The dash in its filename makes a plain `import` a syntax error.
    158     judge_path = Path(__file__).absolute().parent / 'prefilter-judge-chests.py'
    159     spec = importlib.util.spec_from_file_location('prefilter_judge_chests', judge_path)
    160     if spec is None or spec.loader is None:
    161         raise JudgeLoadError(f'no loader for {judge_path}')
    162     judge = importlib.util.module_from_spec(spec)
    163     spec.loader.exec_module(judge)
    164     return judge
    165 
    166 
    167 def parseArguments(argv: list[str]) -> Arguments | None:
```

### 5. chest-attribution.py:231

```python
    223                 )
    224                 chests.append(chest)
    225         corpus[seed] = CorpusWindow(tuple(chests), centre, radius)
    226 
    227     return corpus
    228 
    229 
    230 def readVillagePieces(prefilter_path: Path) -> dict[int, tuple[VillagePiece, ...]]:
>>  231     # name@min_x,min_y,min_z..max_x,max_y,max_z, such as ComponentSmeltery@204,64,-495..210,66,-487
    232     PIECE_PATTERN = re.compile(r'(\w+)@(-?\d+),(-?\d+),(-?\d+)\.\.(-?\d+),(-?\d+),(-?\d+)')
    233     pieces: defaultdict[int, list[VillagePiece]] = defaultdict(list)
    234     with prefilter_path.open() as prefilter_file:
    235         for line in prefilter_file:
    236             record = json.loads(line)
    237             if 'kill' in record:
    238                 continue
    239             for start in record.get('village_starts', []):
    240                 for found in PIECE_PATTERN.finditer(start.get('pieces') or ''):
    241                     pieces[record['seed']].append(VillagePiece(found[1], *(int(v) for v in found.groups()[1:])))
```

### 6. chest-attribution.py:277

```python
    269                 name, _, raw_meta = raw_block.rpartition(':')
    270                 position = (chunk_x * CHUNK_WIDTH + local_x, y, chunk_z * CHUNK_WIDTH + local_z)
    271                 blocks[position] = Block(name, int(raw_meta))
    272 
    273     return blocks
    274 
    275 
    276 def readChestTrace(trace_path: Path | None) -> ChestTrace:
>>  277     # abs=x,y,z, then cat=<loot table>, then caller=<class>.<method>:<line>
    278     TRACE_PATTERN = re.compile(r'abs=(-?\d+),(-?\d+),(-?\d+)\b.*?\bcat=(\S+).*?\bcaller=(\S+)')
    279     fillers: dict[Position, Filler] = {}
    280     fill_counts: Counter[Position] = Counter()
    281     if trace_path is None:
    282         return ChestTrace(fillers, 0)
    283 
    284     with trace_path.open(errors='replace') as trace_file:
    285         for line in trace_file:
    286             if '[chesttrace]' not in line:
    287                 continue
```

### 7. chest-attribution.py:326

```python
    318     return by_bucket
    319 
    320 
    321 def attributeChest(chest: Chest, prediction: Prediction, evidence: Evidence) -> Assignment:
    322     """Put one chest in the first bucket that matches, in the order of the module docstring."""
    323     if chest.column in prediction.columns:
    324         return Assignment(chest, Bucket.PREDICTED)
    325 
>>  326     # trace first: the filling class is the source, and every check below is a guess
    327     filler = evidence.trace.fillers.get(chest.position)
    328     if filler is not None:
    329         bucket = bucketForCaller(filler.caller, filler.category)
    330         if bucket is None:
    331             return Assignment(chest, Bucket.TRACED_UNRECOGNISED_CALLER, f'{filler.caller} cat={filler.category}')
    332         if bucket is Bucket.VILLAGE_PIECE:
    333             # a.b.TaigaStructures$TaigaHut.func_74875_a -> TaigaStructures$TaigaHut
    334             return Assignment(chest, bucket, filler.caller.rsplit('.', 1)[0].split('.')[-1])
    335         return Assignment(chest, bucket)
    336 
```

### 8. chest-attribution.py:333

```python
    325 
    326     # trace first: the filling class is the source, and every check below is a guess
    327     filler = evidence.trace.fillers.get(chest.position)
    328     if filler is not None:
    329         bucket = bucketForCaller(filler.caller, filler.category)
    330         if bucket is None:
    331             return Assignment(chest, Bucket.TRACED_UNRECOGNISED_CALLER, f'{filler.caller} cat={filler.category}')
    332         if bucket is Bucket.VILLAGE_PIECE:
>>  333             # a.b.TaigaStructures$TaigaHut.func_74875_a -> TaigaStructures$TaigaHut
    334             return Assignment(chest, bucket, filler.caller.rsplit('.', 1)[0].split('.')[-1])
    335         return Assignment(chest, bucket)
    336 
    337     piece = findEnclosingVillagePiece(chest.position, prediction.village_pieces)
    338     if piece is not None:
    339         bucket = Bucket.VILLAGE_PIECE if chest.stack_count else Bucket.VILLAGE_PIECE_EMPTY
    340         return Assignment(chest, bucket, piece.name)
    341 
    342     if chest.position in evidence.hilltop_hints or onHilltopPedestal(chest.position, evidence.blocks):
    343         return Assignment(chest, Bucket.THAUMCRAFT_HILLTOP)
```

### 9. chest-attribution.py:362

```python
    354 
    355 
    356 def bucketForCaller(caller: str, category: str) -> Bucket | None:
    357     """Match the generator class of a traced fill, and its loot table category, to a loot source.
    358 
    359     Returns:
    360         None for a class or a category that matches no known source.
    361     """
>>  362     # Vanilla WorldGenDungeons and Roguelike Dungeons run inside chunk population, with no frame of
>>  363     # their generator on the stack. Bucket those fills by loot table category.
    364     if 'ChunkGeneratorRealistic' in caller:
    365         match category:
    366             case 'dungeonChest':
    367                 return Bucket.VANILLA_DUNGEON_OR_ROGUELIKE
    368             case 'mineshaftCorridor':
    369                 return Bucket.MINESHAFT
    370             case 'strongholdLibrary' | 'strongholdCorridor' | 'strongholdCrossing':
    371                 return Bucket.STRONGHOLD
    372             case _:
    373                 return None
```

### 10. chest-attribution.py:409

```python
    401             and piece.min_y - MARGIN_BELOW <= y <= piece.max_y + MARGIN_ABOVE
    402         ):
    403             return piece
    404 
    405     return None
    406 
    407 
    408 def onHilltopPedestal(position: Position, blocks: Mapping[Position, Block]) -> bool:
>>  409     # WorldGenHilltopStones.func_76484_a places the chest on an obsidian pedestal (blockCosmeticSolid
>>  410     # meta 1), on a mob spawner, in the centre column of the ring.
>>  411     # On beta-3 seed -1636594104014467454 the chest at (36, 97, 278) has, in chunk-local positions:
>>  412     #   4,95,6 minecraft:mob_spawner / 4,96,6 Thaumcraft:blockCosmeticSolid:1 / 4,97,6 minecraft:chest:3
    413     BLOCKS_BELOW = ((-1, 'Thaumcraft:blockCosmeticSolid', 1), (-2, 'minecraft:mob_spawner', None))
    414     x, y, z = position
    415     for dy, name, meta in BLOCKS_BELOW:
    416         block = blocks.get((x, y + dy, z))
    417         if block is None or block.name != name or (meta is not None and block.meta != meta):
    418             return False
    419 
    420     return True
    421 
    422 
```

### 11. chest-attribution.py:488

```python
    480             chest = assignment.chest
    481             type_name = '?' if chest.type_name is None else chest.type_name
    482             print(f'    {formatPosition(chest.position):20s} {type_name:22s} {chest.signature}')
    483 
    484     print()
    485 
    486 
    487 def formatPosition(position: Position) -> str:
>>  488     # str() of the tuple would print (x, y, z), unlike the [x, y, z] of the corpus JSON
    489     return str(list(position))
    490 
    491 
    492 ### vocabulary #########################################################################
    493 
    494 
    495 Position = tuple[int, int, int]
    496 Column = tuple[int, int]  # block x and z
    497 
    498 
```

### 12. chest-attribution.py:496

```python
    488     # str() of the tuple would print (x, y, z), unlike the [x, y, z] of the corpus JSON
    489     return str(list(position))
    490 
    491 
    492 ### vocabulary #########################################################################
    493 
    494 
    495 Position = tuple[int, int, int]
>>  496 Column = tuple[int, int]  # block x and z
    497 
    498 
    499 class Bucket(Enum):
    500     PREDICTED = 'predicted'
    501     VILLAGE_PIECE = 'village-piece'
    502     VILLAGE_PIECE_EMPTY = 'village-piece-empty'
    503     THAUMCRAFT_HILLTOP = 'thaumcraft-hilltop'
    504     THAUMCRAFT_BARROW = 'thaumcraft-barrow'
    505     MINESHAFT = 'mineshaft'
    506     STRONGHOLD = 'stronghold'
```

### 13. chest-attribution.py:558

```python
    550     @property
    551     def column(self) -> Column:
    552         return (self.position[0], self.position[2])
    553 
    554 
    555 @dataclass(frozen=True)
    556 class CorpusWindow:
    557     chests: tuple[Chest, ...]
>>  558     centre: tuple[int, int]  # chunk x and z
    559     radius: int | None
    560 
    561 
    562 @dataclass(frozen=True)
    563 class VillagePiece:
    564     name: str
    565     min_x: int
    566     min_y: int
    567     min_z: int
    568     max_x: int
```

### 14. chest-attribution.py:588

```python
    580 @dataclass(frozen=True)
    581 class Block:
    582     name: str
    583     meta: int
    584 
    585 
    586 @dataclass(frozen=True)
    587 class Filler:
>>  588     caller: str  # class and method, such as rwg.world.ChunkGeneratorRealistic.func_73153_a
    589     category: str
    590 
    591 
    592 @dataclass(frozen=True)
    593 class ChestTrace:
    594     fillers: Mapping[Position, Filler]
    595     refilled_count: int
    596 
    597 
    598 @dataclass(frozen=True)
```

### 15. diff-chests.py:1

```python
>>    1 #!/usr/bin/env python3
      2 """Compare the chests of two batches of probe search reports, counting existence, contents and NBT apart.
      3 
      4     existence  a chest position in one batch only
      5     contents   same position, different (slot, id, damage, count) list
      6     NBT        same position and item list, different tag
      7 
      8 Each directory has the per-seed search reports of one probe batch run with PROBE_SEARCH=true. Reports
      9 are paired on the seed and dimension recorded inside them, so filenames and order may differ. A chest is
     10 an entry of search.chunks["<cx>,<cz>"].chests:
     11 
```

### 16. diff-chests.py:196

```python
    188                 file=sys.stderr,
    189             )
    190             continue
    191         seed = report.get('seed')
    192         if seed is None:
    193             continue
    194 
    195         dimension = report.get('dim', 0)
>>  196         # keyed on dimension too: one seed can have an overworld and a Twilight Forest report
    197         seed_dimension = SeedDimension(f'{seed}@{dimension}')
    198         if seed_dimension in chests_by_seed_dimension:
    199             print(
    200                 f'  ! {report_path.name}: duplicate seed/dim {seed_dimension} — earlier report ignored',
    201                 file=sys.stderr,
    202             )
    203         chests_by_seed_dimension[seed_dimension] = parseChests(report, container_type)
    204     return chests_by_seed_dimension
    205 
    206 
```

### 17. diff-chests.py:246

```python
    238     return (int(raw_dimension or 0), int(raw_seed))
    239 
    240 
    241 def compareChests(chests_a: ChestsByPosition, chests_b: ChestsByPosition) -> ChestDifferences:
    242     common = chests_a.keys() & chests_b.keys()
    243     contents = frozenset(
    244         position for position in common if listItemStacks(chests_a[position]) != listItemStacks(chests_b[position])
    245     )
>>  246     # without the tag comparison, differing enchantments, charge levels and bee genomes would pass
    247     changed = frozenset(position for position in common if chests_a[position].items != chests_b[position].items)
    248     return ChestDifferences(
    249         only_a=frozenset(chests_a.keys() - chests_b.keys()),
    250         only_b=frozenset(chests_b.keys() - chests_a.keys()),
    251         contents=contents,
    252         nbt_only=changed - contents,
    253     )
    254 
    255 
    256 def listItemStacks(chest: Chest) -> list[ItemStack]:
```

### 18. diff-chests.py:283

```python
    275 def formatItems(chest: Chest) -> str:
    276     return str(
    277         [(item.stack.slot, item.stack.item_id, item.stack.damage, item.stack.count, item.tag) for item in chest.items],
    278     )
    279 
    280 
    281 ### vocabulary #########################################################################
    282 
>>  283 SeedDimension = NewType('SeedDimension', str)  # "<seed>@<dim>", as printed
    284 Position = NewType('Position', tuple[object, ...])
    285 
    286 
    287 @dataclass(frozen=True)
    288 class Arguments:
    289     report_dir_a: Path
    290     report_dir_b: Path
    291     container_type: str | None
    292     verbose: bool
    293     allow_jar_mismatch: bool
```

### 19. loot-csv.py:1

```python
>>    1 #!/usr/bin/env python3
      2 """Export every chest of one seed in a stage-0 prefilter sweep as a CSV, one row per item stack.
      3 
      4 Usage:
      5     $ python3 loot-csv.py value-table.csv \
      6           prefilter-0.5-d17a685-gtnhdaily707-10-chest-loot-r60.jsonl -6270331762397506834
      7     $ python3 loot-csv.py value-table.csv prefilter-3seeds-stronghold.jsonl -1297854885530077460 --radius 100
      8     $ python3 loot-csv.py value-table.csv sweep.jsonl <seed> -o route.csv --surfacey surface-y.jsonl
      9 
     10 One row of each shape, from the first two runs:
     11 
```

### 20. loot-csv.py:163

```python
    155             'the chest count above is a LOWER BOUND.',
    156         )
    157         print('    most common: ' + ', '.join(f'{name} x{count}' for name, count in piece_counts.most_common(5)))
    158 
    159     return EXIT_SUCCESS
    160 
    161 
    162 def readValueTable(value_table_path: Path) -> ValueTable:
>>  163     # an import statement cannot load loot-score.py, whose filename has a hyphen
    164     spec = importlib.util.spec_from_file_location('loot_score', SCRIPT_DIR / 'loot-score.py')
    165     if spec is None or spec.loader is None:
    166         raise ImportError(f'cannot load {SCRIPT_DIR / "loot-score.py"}')
    167     loot_score = importlib.util.module_from_spec(spec)
    168     spec.loader.exec_module(loot_score)
    169 
    170     unit_values, _limits, minimums, _display, _duplicates = loot_score.load_values(value_table_path, 'max')
    171     min_gated = frozenset(key for key, minimum in minimums.items() if minimum)
    172     return ValueTable(unit_values, min_gated, loot_score.norm)
    173 
```

### 21. loot-csv.py:210

```python
    202     except (OSError, ValueError) as exc:
    203         print(
    204             f'warning: could not read {raw_chest_sites_path} ({exc}); '
    205             f'coverage of the chest-site table will not be reported',
    206             file=sys.stderr,
    207         )
    208         return frozenset()
    209 
>>  210     # without chestless, every piece measured to place no chest gets a village-UNKNOWN-PIECE row
    211     sites = [*chest_sites.get('sites', []), *chest_sites.get('chestless', [])]
    212     # simple class name, the form in a village start's pieces string
    213     return frozenset(site['piece'].rsplit('$', 1)[-1].rsplit('.', 1)[-1] for site in sites)
    214 
    215 
    216 def collectUncoveredPieces(record: dict[str, Any], covered_pieces: frozenset[str]) -> list[UncoveredPiece]:
    217     PIECE_BOX = re.compile(r'(\w+)@(-?\d+),(-?\d+),(-?\d+)\.\.(-?\d+),(-?\d+),(-?\d+)')  # class@x1,y1,z1..x2,y2,z2 box
    218 
    219     # without this guard, every piece counts as uncovered when the chest-site table is unreadable
    220     if not covered_pieces:
```

### 22. loot-csv.py:212

```python
    204             f'warning: could not read {raw_chest_sites_path} ({exc}); '
    205             f'coverage of the chest-site table will not be reported',
    206             file=sys.stderr,
    207         )
    208         return frozenset()
    209 
    210     # without chestless, every piece measured to place no chest gets a village-UNKNOWN-PIECE row
    211     sites = [*chest_sites.get('sites', []), *chest_sites.get('chestless', [])]
>>  212     # simple class name, the form in a village start's pieces string
    213     return frozenset(site['piece'].rsplit('$', 1)[-1].rsplit('.', 1)[-1] for site in sites)
    214 
    215 
    216 def collectUncoveredPieces(record: dict[str, Any], covered_pieces: frozenset[str]) -> list[UncoveredPiece]:
    217     PIECE_BOX = re.compile(r'(\w+)@(-?\d+),(-?\d+),(-?\d+)\.\.(-?\d+),(-?\d+),(-?\d+)')  # class@x1,y1,z1..x2,y2,z2 box
    218 
    219     # without this guard, every piece counts as uncovered when the chest-site table is unreadable
    220     if not covered_pieces:
    221         return []
    222 
```

### 23. loot-csv.py:217

```python
    209 
    210     # without chestless, every piece measured to place no chest gets a village-UNKNOWN-PIECE row
    211     sites = [*chest_sites.get('sites', []), *chest_sites.get('chestless', [])]
    212     # simple class name, the form in a village start's pieces string
    213     return frozenset(site['piece'].rsplit('$', 1)[-1].rsplit('.', 1)[-1] for site in sites)
    214 
    215 
    216 def collectUncoveredPieces(record: dict[str, Any], covered_pieces: frozenset[str]) -> list[UncoveredPiece]:
>>  217     PIECE_BOX = re.compile(r'(\w+)@(-?\d+),(-?\d+),(-?\d+)\.\.(-?\d+),(-?\d+),(-?\d+)')  # class@x1,y1,z1..x2,y2,z2 box
    218 
    219     # without this guard, every piece counts as uncovered when the chest-site table is unreadable
    220     if not covered_pieces:
    221         return []
    222 
    223     uncovered: list[UncoveredPiece] = []
    224     for start in record.get('village_starts', []):
    225         village_tp = formatChunkTeleport(start.get('c'), SKY_Y)
    226         for piece_box in PIECE_BOX.finditer(start.get('pieces') or ''):
    227             piece_class = piece_box.group(1)
```

### 24. loot-csv.py:219

```python
    211     sites = [*chest_sites.get('sites', []), *chest_sites.get('chestless', [])]
    212     # simple class name, the form in a village start's pieces string
    213     return frozenset(site['piece'].rsplit('$', 1)[-1].rsplit('.', 1)[-1] for site in sites)
    214 
    215 
    216 def collectUncoveredPieces(record: dict[str, Any], covered_pieces: frozenset[str]) -> list[UncoveredPiece]:
    217     PIECE_BOX = re.compile(r'(\w+)@(-?\d+),(-?\d+),(-?\d+)\.\.(-?\d+),(-?\d+),(-?\d+)')  # class@x1,y1,z1..x2,y2,z2 box
    218 
>>  219     # without this guard, every piece counts as uncovered when the chest-site table is unreadable
    220     if not covered_pieces:
    221         return []
    222 
    223     uncovered: list[UncoveredPiece] = []
    224     for start in record.get('village_starts', []):
    225         village_tp = formatChunkTeleport(start.get('c'), SKY_Y)
    226         for piece_box in PIECE_BOX.finditer(start.get('pieces') or ''):
    227             piece_class = piece_box.group(1)
    228             if piece_class in covered_pieces:
    229                 continue
```

### 25. loot-csv.py:375

```python
    367 
    368 
    369 @dataclass(frozen=True)
    370 class PredictedChest:
    371     source: ChestSource
    372     structure: str
    373     category: str
    374     position: tuple[int, int, int]
>>  375     stacks: tuple[Stack, ...] | None  # None when the contents are not predicted
    376     structure_tp: str
    377     y_note: str
    378     reason: str = ''
    379 
    380 
    381 @dataclass(frozen=True)
    382 class UncoveredPiece:
    383     piece_class: str
    384     centre: tuple[int, int, int]
    385     village_tp: str
```

### 26. loot-csv.py:392

```python
    384     centre: tuple[int, int, int]
    385     village_tp: str
    386 
    387 
    388 @dataclass(frozen=True)
    389 class ValueTable:
    390     unit_values: Mapping[str, float]
    391     min_gated: frozenset[str]
>>  392     match_key: Callable[[str], str]  # loot-score.py's norm(): display name to the table's key
    393 
    394     def unitValue(self, name: str | None) -> float | None:
    395         if not name:
    396             return None
    397         return self.unit_values.get(self.match_key(name))
    398 
    399     def stackValue(self, stack: Stack) -> float:
    400         unit_value = self.unitValue(stack.name)
    401         return 0 if unit_value is None else unit_value * stack.count
    402 
```

## Skill with R10-cleanup-rewrite and R10-subject-verb: 18 comments

`scratchpad/cleanup/review/new`

### 27. chest-attribution.py:1

```python
>>    1 #!/usr/bin/env python3
      2 """Attribute each chest of a corpus to a prefilter prediction, or to the likely reason for its absence.
      3 
      4 The corpus and prefilter readers are those of prefilter-judge-chests.py, which must be in the same
      5 directory as this file. A chest goes to the first bucket that matches:
      6 
      7   predicted                     a predicted chest at the same XZ
      8   traced bucket                 with --trace, the bucket of the frame that filled the chest
      9   traced-unrecognised-caller    with --trace, a frame that lookUpCallerBucket() has no bucket for
     10   village-piece                 inside a village piece box from the prefilter, with items
     11   village-piece-empty           inside a village piece box, with no items
```

### 28. chest-attribution.py:80

```python
     72 from collections.abc import Iterable, Mapping
     73 from dataclasses import dataclass
     74 from enum import Enum
     75 from pathlib import Path
     76 from typing import Any, TypeAlias
     77 
     78 
     79 NEAR_PREDICTION_BLOCKS = 16
>>   80 # Mineshaft corridors and vanilla WorldGenDungeons are stage-0 blind spots with their chests below sea
>>   81 # level, Y64. On beta-3 seed -1636594104014467454, dungeon chests reach Y58.
     82 DEEP_Y = 64
     83 DEFAULT_LISTING_LIMIT = 30
     84 LISTED_UNMAPPED_CALLERS = 12
     85 EXIT_SUCCESS = 0
     86 EXIT_NO_CHESTS = 1
     87 
     88 
     89 def main() -> int:
     90     """Attribute the chests of every seed in the corpus, and print a report per seed."""
     91     arguments = parseArguments()
```

### 29. chest-attribution.py:288

```python
    280         bucket = lookUpCallerBucket(fill)
    281         if bucket is None:
    282             return Attribution(
    283                 chest,
    284                 Bucket.TRACED_UNRECOGNISED_CALLER,
    285                 unmapped_caller=f'{fill.caller} cat={fill.category}',
    286             )
    287         if bucket is Bucket.VILLAGE_PIECE:
>>  288             # the piece is the class before the obfuscated method name (func_74875_a)
    289             return Attribution(chest, bucket, village_piece=fill.caller.rsplit('.', 1)[0].split('.')[-1])
    290         return Attribution(chest, bucket)
    291 
    292     piece_name = next((piece.name for piece in prediction.village_pieces if piece.encloses(position)), None)
    293     if piece_name is not None:
    294         # an empty inventory in a village piece is furniture, such as a Tinkers' casting table or a barrel
    295         bucket = Bucket.VILLAGE_PIECE if chest.get('items') else Bucket.VILLAGE_PIECE_EMPTY
    296         return Attribution(chest, bucket, village_piece=piece_name)
    297 
    298     if position in evidence.hilltop_hints or onHilltopPedestal(position, evidence.blocks):
```

### 30. chest-attribution.py:294

```python
    286             )
    287         if bucket is Bucket.VILLAGE_PIECE:
    288             # the piece is the class before the obfuscated method name (func_74875_a)
    289             return Attribution(chest, bucket, village_piece=fill.caller.rsplit('.', 1)[0].split('.')[-1])
    290         return Attribution(chest, bucket)
    291 
    292     piece_name = next((piece.name for piece in prediction.village_pieces if piece.encloses(position)), None)
    293     if piece_name is not None:
>>  294         # an empty inventory in a village piece is furniture, such as a Tinkers' casting table or a barrel
    295         bucket = Bucket.VILLAGE_PIECE if chest.get('items') else Bucket.VILLAGE_PIECE_EMPTY
    296         return Attribution(chest, bucket, village_piece=piece_name)
    297 
    298     if position in evidence.hilltop_hints or onHilltopPedestal(position, evidence.blocks):
    299         return Attribution(chest, Bucket.THAUMCRAFT_HILLTOP)
    300     if nearBarrow(position, evidence.blocks):
    301         return Attribution(chest, Bucket.THAUMCRAFT_BARROW)
    302     if nearPrediction((x, z), columns_in_window):
    303         return Attribution(chest, Bucket.NEAR_PREDICTION)
    304     if y < DEEP_Y:
```

### 31. chest-attribution.py:311

```python
    303         return Attribution(chest, Bucket.NEAR_PREDICTION)
    304     if y < DEEP_Y:
    305         return Attribution(chest, Bucket.DEEP_BLIND_SPOT)
    306     return Attribution(chest, Bucket.UNATTRIBUTED)
    307 
    308 
    309 def lookUpCallerBucket(fill: TracedFill) -> Bucket | None:
    310     """Look up the bucket of the frame that filled a chest, or None for a frame with no mapping."""
>>  311     # Vanilla and Roguelike dungeons are generated during chunk population, so the frame of their fill
>>  312     # is the populate entry point. Their bucket comes from the loot category.
    313     GENERIC_CALLERS = ('ChunkGeneratorRealistic',)
    314     CATEGORY_BUCKETS = {
    315         'dungeonChest': Bucket.VANILLA_DUNGEON_OR_ROGUELIKE,
    316         'mineshaftCorridor': Bucket.MINESHAFT,
    317         'strongholdLibrary': Bucket.STRONGHOLD,
    318         'strongholdCorridor': Bucket.STRONGHOLD,
    319         'strongholdCrossing': Bucket.STRONGHOLD,
    320     }
    321 
    322     caller = fill.caller
```

### 32. chest-attribution.py:343

```python
    335     if 'WorldGenDungeons' in caller:
    336         return Bucket.VANILLA_DUNGEON
    337     if 'greymerk' in caller or 'roguelike' in caller.lower():
    338         return Bucket.ROGUELIKE
    339     return None
    340 
    341 
    342 def onHilltopPedestal(position: BlockPosition, blocks: Mapping[BlockPosition, PlacedBlock]) -> bool:
>>  343     # WorldGenHilltopStones.func_76484_a places, on the centre column of the ring only, a mob spawner
>>  344     # two blocks below the chest and an obsidian pedestal (blockCosmeticSolid meta 1) one block below.
>>  345     # The fingerprint matches the blocks of chest (36, 97, 278) on beta-3 seed -1636594104014467454.
    346     HILLTOP_FINGERPRINT = (
    347         (-1, 'Thaumcraft:blockCosmeticSolid', 1),
    348         (-2, 'minecraft:mob_spawner', None),
    349     )
    350 
    351     x, y, z = position
    352     for offset_y, name, meta in HILLTOP_FINGERPRINT:
    353         block = blocks.get((x, y + offset_y, z))
    354         if block is None or block.name != name or (meta is not None and block.meta != meta):
    355             return False
```

### 33. chest-attribution.py:486

```python
    478     trace_path: Path | None
    479     listing_limit: int
    480 
    481 
    482 @dataclass(frozen=True)
    483 class CorpusWindow:
    484     seed: int
    485     chests_by_column: Mapping[BlockColumn, list[Chest]]
>>  486     centre: tuple[int, int]  # chunk coordinates
    487     radius: int | None  # in chunks, None for no limit
    488 
    489 
    490 @dataclass(frozen=True)
    491 class VillagePiece:
    492     name: str
    493     low: BlockPosition
    494     high: BlockPosition
    495 
    496     def encloses(self, position: BlockPosition) -> bool:
```

### 34. chest-attribution.py:487

```python
    479     listing_limit: int
    480 
    481 
    482 @dataclass(frozen=True)
    483 class CorpusWindow:
    484     seed: int
    485     chests_by_column: Mapping[BlockColumn, list[Chest]]
    486     centre: tuple[int, int]  # chunk coordinates
>>  487     radius: int | None  # in chunks, None for no limit
    488 
    489 
    490 @dataclass(frozen=True)
    491 class VillagePiece:
    492     name: str
    493     low: BlockPosition
    494     high: BlockPosition
    495 
    496     def encloses(self, position: BlockPosition) -> bool:
    497         SIDE_MARGIN = 1
```

### 35. chest-attribution.py:520

```python
    512 class SeedPrediction:
    513     columns: frozenset[BlockColumn]
    514     village_pieces: tuple[VillagePiece, ...]
    515 
    516 
    517 @dataclass(frozen=True)
    518 class TracedFill:
    519     position: BlockPosition
>>  520     caller: str  # class and method of the frame, without the line number
    521     category: str
    522 
    523 
    524 @dataclass(frozen=True)
    525 class PlacedBlock:
    526     name: str
    527     meta: int
    528 
    529 
    530 @dataclass(frozen=True)
```

### 36. chest-attribution.py:558

```python
    550     def inBucket(self, bucket: Bucket) -> list[Attribution]:
    551         return [entry for entry in self.attributions if entry.bucket is bucket]
    552 
    553 
    554 class PrefilterJudge:
    555     """Typed wrappers of the corpus and prefilter readers of prefilter-judge-chests.py."""
    556 
    557     def __init__(self) -> None:
>>  558         # the filename has a dash, so an import statement cannot load it
    559         judge_path = Path(__file__).absolute().parent / 'prefilter-judge-chests.py'
    560         spec = importlib.util.spec_from_file_location('prefilter_judge_chests', judge_path)
    561         if spec is None or spec.loader is None:
    562             raise JudgeLoadError(f'cannot load {judge_path}')
    563         self.module = importlib.util.module_from_spec(spec)
    564         spec.loader.exec_module(self.module)
    565 
    566     def readCorpus(self, raw_corpus_path: str) -> list[CorpusWindow]:
    567         corpus = self.module.load_corpus(raw_corpus_path)
    568         windows = []
```

### 37. diff-chests.py:1

```python
>>    1 #!/usr/bin/env python3
      2 """Compare the chests of two batches of probe search reports, seed by seed.
      3 
      4 Each directory has the JSON search reports of one probe batch run with PROBE_SEARCH=true. Reports are
      5 paired by the seed and dimension recorded in them, and chests by block position. Each difference falls
      6 into one bucket:
      7 
      8     existence  a chest in one batch only
      9     contents   a different list of (slot, id, damage, count)
     10     NBT        the same list, with a different tag on an item
     11 
```

### 38. diff-chests.py:96

```python
     88     build_stamp.check(args.batch_a_dir, args.batch_b_dir, 'A', 'B', allow_mismatch=args.allow_jar_mismatch)
     89     if container_type:
     90         print(f'comparing only containers of type {container_type}')
     91     batch_a = readChests(args.batch_a_dir, container_type)
     92     batch_b = readChests(args.batch_b_dir, container_type)
     93 
     94     shared_keys = sorted(batch_a.keys() & batch_b.keys(), key=parseDimAndSeed)
     95     print(f'batch A: {len(batch_a)} seeds   batch B: {len(batch_b)} seeds   compared: {len(shared_keys)}')
>>   96     # warm-shard.sh leaves both output directories empty when it aborts on its memory guard
     97     if not batch_a or not batch_b or not shared_keys:
     98         empty = [label for label, batch in (('A', batch_a), ('B', batch_b)) if not batch]
     99         reason = (
    100             f'no usable reports in batch {" and ".join(empty)}'
    101             if empty
    102             else 'the two batches share no seed/dim in common'
    103         )
    104         print(
    105             f'NO COMPARISON PERFORMED: {reason}. '
    106             f'This is a failed run, not a passing one — check the probe output directories.',
```

### 39. diff-chests.py:136

```python
    128     print(f'\ntotal chests: A={chest_total_a} B={chest_total_b}')
    129     print(f'existence differences: {sum(diff.countExistence() for diff in diffs.values())}')
    130     print(f'contents  differences: {sum(len(diff.contents) for diff in diffs.values())}')
    131     print(f'NBT-only  differences: {sum(len(diff.nbt) for diff in diffs.values())}   <- a failure, not a footnote')
    132 
    133     if differing_keys:
    134         print(f'\nVERDICT: {len(differing_keys)}/{len(shared_keys)} seeds differ: {", ".join(differing_keys)}')
    135         return EXIT_FAILURE
>>  136     # a warm-shard.sh run that dies halfway leaves seeds in one batch only
    137     if unpaired_keys:
    138         print(
    139             f'\nVERDICT: INCOMPLETE — the {len(shared_keys)} seed/dim pairs that were compared are '
    140             f'identical, but {len(unpaired_keys)} exist in only one batch and were never compared. '
    141             f'Re-run the missing arm before calling this a pass.',
    142         )
    143         return EXIT_FAILURE
    144     print('\nVERDICT: ALL SEEDS IDENTICAL')
    145     return EXIT_SUCCESS
    146 
```

### 40. loot-csv.py:1

```python
>>    1 #!/usr/bin/env python3
      2 """Write every predicted chest of one seed to a CSV, one row per item stack.
      3 
      4 Usage:
      5     $ python3 loot-csv.py value-table.csv sweep.jsonl -7269948338495788698
      6     $ python3 loot-csv.py value-table.csv sweep.jsonl -7269948338495788698 -o route.csv --radius 15
      7     $ python3 loot-csv.py value-table.csv sweep.jsonl -7269948338495788698 --surfacey surface-y.jsonl
      8 
      9 The first data row of a run over a stage-0 prefilter record, one column per line:
     10 
     11     seed                 -7269948338495788698
```

### 41. loot-csv.py:213

```python
    205 
    206 def readValueTable(value_table_path: Path) -> ValueTable:
    207     spec = importlib.util.spec_from_file_location('loot_score', LOOT_SCORE_PATH)
    208     if spec is None or spec.loader is None:
    209         raise ImportError(f'no loader for {LOOT_SCORE_PATH}')
    210     loot_score = importlib.util.module_from_spec(spec)
    211     spec.loader.exec_module(loot_score)
    212 
>>  213     # 'max': of duplicate rows for one item, the highest value applies
    214     unit_values, _limits, minimums, _display, _duplicates = loot_score.load_values(value_table_path, 'max')
    215     min_gated = frozenset(key for key, minimum in minimums.items() if minimum)
    216     return ValueTable(unit_values, min_gated, loot_score.norm)
    217 
    218 
    219 def findSeedRecord(sweep_path: Path, seed: int) -> dict[str, Any] | None:
    220     for record in readJsonLines(sweep_path):
    221         if record.get('seed') == seed:
    222             return record
    223     return None
```

### 42. loot-csv.py:257

```python
    249         print(
    250             f'warning: could not read {raw_chest_sites_path} ({exc}); '
    251             f'coverage of the chest-site table will not be reported',
    252             file=sys.stderr,
    253         )
    254         return frozenset()
    255 
    256     covered = set()
>>  257     # without `chestless`, a piece measured to place no chest would get an unknown-piece row
    258     for group in ('sites', 'chestless'):
    259         for entry in chest_sites.get(group, []):
    260             covered.add(entry['piece'].rsplit('$', 1)[-1].rsplit('.', 1)[-1])
    261     return frozenset(covered)
    262 
    263 
    264 def parseSeedPrediction(
    265     raw_record: Mapping[str, Any],
    266     surface_heights: Mapping[tuple[int, int], int],
    267 ) -> SeedPrediction:
```

### 43. loot-csv.py:351

```python
    343     """Return the teleport Y and the `y_note` of a village chest."""
    344     surface_y = surface_heights.get((pos.x, pos.z))
    345     if surface_y is None:
    346         return SKY_Y, nominal_note
    347     return surface_y + 1, 'surface Y resolved (virgin, exact on bare ground, up to 4 low under a building)'
    348 
    349 
    350 def parseVillagePieces(raw_start: Mapping[str, Any]) -> list[VillagePiece]:
>>  351     # class name, then the box corners: ComponentBankerHome@1104,64,-657..1108,69,-654
    352     PIECE_PATTERN = re.compile(r'(\w+)@(-?\d+),(-?\d+),(-?\d+)\.\.(-?\d+),(-?\d+),(-?\d+)')
    353     structure_tp = formatChunkCentreTeleport(raw_start.get('c'), SKY_Y)
    354     pieces = []
    355     for match in PIECE_PATTERN.finditer(raw_start.get('pieces') or ''):
    356         min_x, min_y, min_z, max_x, max_y, max_z = (int(group) for group in match.groups()[1:])
    357         centre = BlockPos((min_x + max_x) // 2, (min_y + max_y) // 2, (min_z + max_z) // 2)
    358         pieces.append(VillagePiece(name=match.group(1), centre=centre, structure_tp=structure_tp))
    359     return pieces
    360 
    361 
```

### 44. loot-csv.py:572

```python
    564 
    565 
    566 @dataclass(frozen=True)
    567 class Chest:
    568     source: Source
    569     structure: str
    570     category: str
    571     pos: BlockPos
>>  572     stacks: tuple[Stack, ...] | None  # None when the contents are not predicted
    573     structure_tp: str
    574     teleport_y: int
    575     y_note: str
    576     reason: str
    577 
    578 
    579 @dataclass(frozen=True)
    580 class VillagePiece:
    581     name: str
    582     centre: BlockPos
```
