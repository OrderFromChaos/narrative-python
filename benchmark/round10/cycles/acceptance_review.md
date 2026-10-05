# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## P4 license audit: 8 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/fc75729c-829a-4600-b348-1ae66bc5a1e3/scratchpad/accept/P4`

### 1. license_audit/inputs.py:52

```python
     44 
     45 def parseIsoDate(raw_date: str) -> pendulum.Date | None:
     46     """Parse a YYYY-MM-DD date, or return None when the text is not a real date in that form."""
     47     ISO_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
     48     if not ISO_DATE.fullmatch(raw_date):
     49         return None
     50     try:
     51         return pendulum.Date.fromisoformat(raw_date)
>>   52     except ValueError:  # a day outside its month, such as 2028-02-30
     53         return None
     54 
     55 
     56 def rejectInput(input_path: Path, problem: str) -> InputError:
     57     _LOG.error('input.rejected', extra={'path': str(input_path), 'problem': problem})
     58     return InputError(f'{input_path}: {problem}')
```

### 2. license_audit/lock_files.py:52

```python
     44                 malformed.append(MalformedLine(lock_path.name, line_number, line_text))
     45             else:
     46                 entries.append(entry)
     47 
     48     return LockContents(entries=tuple(entries), malformed=tuple(malformed))
     49 
     50 
     51 def _parsePin(lock_name: str, line_number: int, pin_text: str) -> LockEntry | None:
>>   52     # matches `psycopg2==2.9.9 ; sys_platform != "win32"  # binary wheel on CI`. Rejects `celery>=5`
     53     PIN = re.compile(
     54         r'(?P<name>[^\s=;#<>!~]+)\s*==\s*(?P<version>[A-Za-z0-9][A-Za-z0-9.+!_-]*)'
     55         r'(?:\s*;\s*[^#]*[^#\s])?'
     56         r'(?:\s+#.*)?',
     57     )
     58     pin = PIN.fullmatch(pin_text)
     59     if pin is None:
     60         return None
     61     package = package_names.parsePackageName(pin['name'])
     62     if package is None:
```

### 3. license_audit/package_names.py:16

```python
      8 
      9 from __future__ import annotations
     10 
     11 import re
     12 
     13 from license_audit.vocabulary import PackageName
     14 
     15 
>>   16 # matches: Flask_SQLAlchemy, zope.interface, x. Rejects: -flask, flask., celery>=5
     17 _VALID_NAME = re.compile(r'[A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]')
     18 _NAME_SEPARATORS = re.compile(r'[-_.]+')
     19 
     20 
     21 def parsePackageName(raw_name: str) -> PackageName | None:
     22     if not _VALID_NAME.fullmatch(raw_name):
     23         return None
     24     return PackageName(_NAME_SEPARATORS.sub('-', raw_name).lower())
```

### 4. license_audit/spdx.py:18

```python
     10 
     11 import re
     12 from collections import deque
     13 from collections.abc import Callable
     14 
     15 from license_audit.vocabulary import Compound, Expression, LicenseId, LicenseLeaf, Operator
     16 
     17 
>>   18 # matches: MIT, Apache-2.0, GPL-2.0+, RSALv2. Rejects: (MIT, -MIT
     19 _LICENSE_ID_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9.+-]*')
     20 _TOKEN_PATTERN = re.compile(r'[()]|[^\s()]+')
     21 _OPERATOR_WORDS = frozenset(operator.value for operator in Operator)
     22 
     23 
     24 def parseLicenseExpression(expression_text: str) -> Expression | None:
     25     """Parse an expression, or return None when the text is not a well-formed expression."""
     26     tokens = deque(_TOKEN_PATTERN.findall(expression_text))
     27     expression = _parseChain(tokens, Operator.OR)
     28     return None if tokens else expression
```

### 5. license_audit/verdict_store.py:29

```python
     21         ' lock TEXT NOT NULL,'
     22         ' line INTEGER NOT NULL,'
     23         ' package TEXT NOT NULL,'
     24         ' version TEXT NOT NULL,'
     25         ' license TEXT,'
     26         ' verdict TEXT NOT NULL'
     27         ') STRICT',
     28     )
>>   29     # NULLs never collide in a SQLite UNIQUE index. Index COALESCE(license, '') so a repeated unknown license collides
     30     connection.execute(
     31         'CREATE UNIQUE INDEX IF NOT EXISTS verdicts_once'
     32         " ON verdicts (audit_date, input_dir, lock, line, package, version, COALESCE(license, ''), verdict)",
     33     )
     34     connection.commit()
     35 
     36 
     37 def recordVerdicts(connection: sqlite3.Connection, audit: Audit) -> int:
     38     """Record one row per audit entry.
     39 
```

### 6. license_audit/verdict_store.py:65

```python
     57     cursor = connection.executemany('INSERT OR IGNORE INTO verdicts VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
     58     connection.commit()
     59     return cursor.rowcount
     60 
     61 
     62 ### vocabulary ###########################################################################################
     63 
     64 
>>   65 # sqlite3.Cursor.executemany() rejects dataclass rows. A NamedTuple is used instead
     66 class _VerdictRow(NamedTuple):
     67     audit_date: str
     68     input_dir: str
     69     lock: str
     70     line: int
     71     package: str
     72     version: str
     73     license: str | None
     74     verdict: str
```

### 7. license_audit/vocabulary.py:12

```python
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from typing import NewType, TypeAlias
      8 
      9 import pendulum
     10 
     11 
>>   12 PackageName = NewType('PackageName', str)  # a name normalised by PEP 503
     13 Version = NewType('Version', str)
     14 LicenseId = NewType('LicenseId', str)  # a casefolded SPDX license id
     15 
     16 
     17 class Verdict(Enum):
     18     ALLOWED = 'allowed'
     19     DENIED = 'denied'
     20     UNREVIEWED = 'unreviewed'
     21     UNKNOWN_LICENSE = 'unknown license'
     22 
```

### 8. license_audit/vocabulary.py:14

```python
      6 from enum import Enum
      7 from typing import NewType, TypeAlias
      8 
      9 import pendulum
     10 
     11 
     12 PackageName = NewType('PackageName', str)  # a name normalised by PEP 503
     13 Version = NewType('Version', str)
>>   14 LicenseId = NewType('LicenseId', str)  # a casefolded SPDX license id
     15 
     16 
     17 class Verdict(Enum):
     18     ALLOWED = 'allowed'
     19     DENIED = 'denied'
     20     UNREVIEWED = 'unreviewed'
     21     UNKNOWN_LICENSE = 'unknown license'
     22 
     23 
     24 class Operator(Enum):
```

## P6 chess replayer: 8 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/fc75729c-829a-4600-b348-1ae66bc5a1e3/scratchpad/accept/P6`

### 9. pgn_replay/fen.py:114

```python
    106     for color in Color:
    107         if board.count(Piece(color, PieceKind.KING)) != 1:
    108             raise _rejectFen(fen_text, f'one {color.name.lower()} king')
    109 
    110     return tuple(board)
    111 
    112 
    113 def _numeric(raw_number: str) -> bool:
>>  114     # isdigit() admits non-ASCII digits such as '²'. Check isascii() too
    115     return raw_number.isascii() and raw_number.isdigit()
    116 
    117 
    118 def _formatPlacement(board: Board) -> str:
    119     rank_texts = []
    120     for rank in range(7, -1, -1):
    121         rank_text = ''
    122         empty_run = 0
    123         for file in range(8):
    124             piece = board[squareAt(file, rank)]
```

### 10. pgn_replay/pgn.py:29

```python
     21 import re
     22 from collections.abc import Iterator
     23 
     24 from pgn_replay.vocabulary import MalformedPgnError, PgnGame
     25 
     26 
     27 _LOG = logging.getLogger(__name__)
     28 
>>   29 # matches: [White "Ada"], {a comment}, (, ), 1/2-1/2, $1, 12..., Nbd7. Rejects: an unclosed {
     30 _TOKEN_PATTERN = re.compile(
     31     r'(?P<tag>\[\s*(?P<tag_name>\w+)\s+"(?P<tag_value>(?:[^"\\]|\\.)*)"\s*\])'
     32     r'|(?P<comment>\{[^}]*\}|;[^\n]*|^%[^\n]*)'
     33     r'|(?P<open>\()'
     34     r'|(?P<close>\))'
     35     r'|(?P<result>(?:1-0|0-1|1/2-1/2|\*)(?![^\s(){};]))'
     36     r'|(?P<glyph>\$\d+)'
     37     r'|(?P<move_number>\d+\.+)'
     38     r'|(?P<symbol>[^\s\[\](){};$]+)'
     39     r'|(?P<space>\s+)',
```

### 11. pgn_replay/rules.py:16

```python
      8 
      9 from collections.abc import Iterator
     10 from dataclasses import dataclass
     11 
     12 from pgn_replay.squares import fileOf, rankOf, squareAt, stepFrom
     13 from pgn_replay.vocabulary import Board, CastlingRight, Color, IllegalReason, Move, Piece, PieceKind, Position, Square
     14 
     15 
>>   16 # (file step, rank step)
     17 _KNIGHT_STEPS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
     18 _KING_STEPS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
     19 _ROOK_DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))
     20 _BISHOP_DIRECTIONS = ((1, 1), (-1, 1), (-1, -1), (1, -1))
     21 
     22 
     23 def generatePseudoLegalMoves(position: Position) -> Iterator[Move]:
     24     """Yield the moves of the side to move other than castling, including moves that leave its king in check."""
     25     side = position.side_to_move
     26     for index, piece in enumerate(position.board):
```

### 12. pgn_replay/rules.py:147

```python
    139 
    140 
    141 def _attackedBy(board: Board, square: Square, attacker: Color) -> bool:
    142     for kind in PieceKind:
    143         for source in _generateReachableSquares(board, square, kind):
    144             if board[source] == Piece(attacker, kind):
    145                 return True
    146 
>>  147     # a pawn attacks diagonally forward, so its source is diagonally behind the square
    148     forward = _pawnGeometryOf(attacker).forward
    149     for file_step in (-1, 1):
    150         pawn_source = stepFrom(square, file_step, -forward)
    151         if pawn_source is not None and board[pawn_source] == Piece(attacker, PieceKind.PAWN):
    152             return True
    153 
    154     return False
    155 
    156 
    157 def _generatePawnMoves(position: Position, pawn: Piece, origin: Square) -> Iterator[Move]:
```

### 13. pgn_replay/san.py:17

```python
      9 import re
     10 from dataclasses import dataclass, replace
     11 
     12 from pgn_replay import rules
     13 from pgn_replay.squares import FILE_LETTERS, fileOf, nameSquare, parseSquareName, rankOf
     14 from pgn_replay.vocabulary import IllegalReason, Move, PieceKind, Position, Square
     15 
     16 
>>   17 # matches: O-O-O, Nbd7, R1xa4, Qh4+, exd6, axb8=N, a8=Q#. Rejects: Kx9, a8Q, Pe4
     18 _SAN_PATTERN = re.compile(
     19     r'(?P<castling>O-O(?:-O)?)'
     20     r'|(?P<piece>[NBRQK])(?P<origin_file>[a-h])?(?P<origin_rank>[1-8])?x?(?P<piece_target>[a-h][1-8])'
     21     r'|(?P<pawn_file>[a-h])(?:x(?P<capture_target>[a-h][1-8])|(?P<push_rank>[1-8]))(?:=(?P<promotion>[NBRQ]))?',
     22 )
     23 _SAN_SUFFIXES = '+#!?'
     24 
     25 
     26 def resolveSan(position: Position, san_text: str) -> Move | IllegalReason:
     27     """Return the legal Move for a SAN in this position, or the reason the SAN is illegal.
```

### 14. pgn_replay/vocabulary.py:10

```python
      2 
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from typing import NewType, TypeAlias
      8 
      9 
>>   10 # rank * 8 + file. a1 is 0, h1 is 7, h8 is 63
     11 Square = NewType('Square', int)
     12 
     13 IllegalReason = NewType('IllegalReason', str)
     14 
     15 
     16 class Color(Enum):
     17     WHITE = 'w'
     18     BLACK = 'b'
     19 
     20     @property
```

### 15. pgn_replay/vocabulary.py:75

```python
     67 
     68 
     69 @dataclass(frozen=True)
     70 class Piece:
     71     color: Color
     72     kind: PieceKind
     73 
     74 
>>   75 # indexed by Square
     76 Board: TypeAlias = tuple[Piece | None, ...]
     77 
     78 
     79 @dataclass(frozen=True)
     80 class Position:
     81     board: Board
     82     side_to_move: Color
     83     castling_rights: frozenset[CastlingRight]
     84     # the square behind a pawn that made a two-square step on the previous move, capturable or not
     85     en_passant_square: Square | None
```

### 16. pgn_replay/vocabulary.py:84

```python
     76 Board: TypeAlias = tuple[Piece | None, ...]
     77 
     78 
     79 @dataclass(frozen=True)
     80 class Position:
     81     board: Board
     82     side_to_move: Color
     83     castling_rights: frozenset[CastlingRight]
>>   84     # the square behind a pawn that made a two-square step on the previous move, capturable or not
     85     en_passant_square: Square | None
     86     halfmove_clock: int
     87     fullmove_number: int
     88 
     89 
     90 @dataclass(frozen=True)
     91 class Move:
     92     piece: Piece
     93     origin: Square
     94     target: Square
```

## P9 text wrapping: 6 comments

`/tmp/claude-1000/-home-order-Dropbox-Python-Code-Utility-improved-ai-code-style/fc75729c-829a-4600-b348-1ae66bc5a1e3/scratchpad/accept/P9`

### 17. termwrap/measuring.py:41

```python
     33 
     34     A zero-width character with no cluster before it, as at the start of the paragraph or after an
     35     SGR sequence or a soft hyphen, is a cluster of width 0.
     36 
     37     Raises:
     38         ValueError: the paragraph has a control character, a newline included, or an escape sequence
     39             that is not SGR.
     40     """
>>   41     # matches: \x1b[1;31m, \x1b[m, and any single character. A bare \x1b matches alone
     42     PIECE_PATTERN = re.compile(r'\x1b\[[0-9;]*m|.', re.DOTALL)
     43     RESETS = ('\x1b[0m', '\x1b[m')
     44     tokens: list[Token] = []
     45     for piece_match in PIECE_PATTERN.finditer(paragraph):
     46         piece = piece_match.group()
     47         previous = tokens[-1] if tokens else None
     48         if piece.startswith('\x1b['):
     49             tokens.append(Sgr(piece, reset=piece in RESETS))
     50         elif piece == '\x1b':
     51             sequence_start = paragraph[piece_match.start() : piece_match.start() + 8]
```

### 18. termwrap/measuring.py:71

```python
     63             tokens[-1] = Cluster(previous.text + piece, previous.width)
     64         else:
     65             tokens.append(Cluster(piece, _characterWidth(piece)))
     66 
     67     return tokens
     68 
     69 
     70 def _zeroWidth(character: str) -> bool:
>>   71     ZERO_WIDTH_FORMAT = ('\u200b', '\u200d')  # zero width space, zero width joiner
     72     return (
     73         unicodedata.combining(character) != 0
     74         or character in ZERO_WIDTH_FORMAT
     75         or '\ufe00' <= character <= '\ufe0f'  # variation selectors
     76     )
     77 
     78 
     79 def _characterWidth(character: str) -> int:
     80     if _zeroWidth(character):
     81         return 0
```

### 19. termwrap/measuring.py:75

```python
     67     return tokens
     68 
     69 
     70 def _zeroWidth(character: str) -> bool:
     71     ZERO_WIDTH_FORMAT = ('\u200b', '\u200d')  # zero width space, zero width joiner
     72     return (
     73         unicodedata.combining(character) != 0
     74         or character in ZERO_WIDTH_FORMAT
>>   75         or '\ufe00' <= character <= '\ufe0f'  # variation selectors
     76     )
     77 
     78 
     79 def _characterWidth(character: str) -> int:
     80     if _zeroWidth(character):
     81         return 0
     82     if unicodedata.east_asian_width(character) in ('W', 'F'):
     83         return 2
     84     return 1
```

### 20. termwrap/wrapping.py:34

```python
     26     break is dropped. Where an SGR style is active at the end of any line but the last, `ESC[0m` ends
     27     that line, and every SGR sequence since the last reset is repeated at the start of the next. A
     28     `\n` is a line end here. A line with no clusters gets neither.
     29 
     30     Raises:
     31         ValueError: width is below 2, or text has a control character other than `\n`, or an escape
     32             sequence that is not SGR.
     33     """
>>   34     MIN_WIDTH = 2  # a 2-column cluster has to fit on an empty line
     35     RESET = '\x1b[0m'
     36     if width < MIN_WIDTH:
     37         raise ValueError(f'width {width} is below {MIN_WIDTH} (expected an int of {MIN_WIDTH} or more)')
     38 
     39     broken_lines: list[_Line] = []
     40     for paragraph in text.split('\n'):
     41         broken_lines.extend(_breakParagraph(measuring.tokenizeParagraph(paragraph), width))
     42 
     43     sgr_since_reset: list[str] = []
     44     lines: list[str] = []
```

### 21. termwrap/wrapping.py:82

```python
     74 def _chooseBreak(tokens: Sequence[Token], start: int, width: int) -> _Break:
     75     """Choose where the line that starts at tokens[start] ends.
     76 
     77     Where the rest of the paragraph fits, the line is all of it. Otherwise the line ends at the latest
     78     space run or soft hyphen that fits. Where none fits, the line ends after the last cluster that fits.
     79     """
     80     SPACE = Cluster(' ', 1)
     81     latest_preferred: _Break | None = None
>>   82     fitted_end = start  # index after the last cluster that fits
     83     used = 0
     84     for position in range(start, len(tokens)):
     85         token = tokens[position]
     86         has_content = fitted_end > start
     87         if has_content and token == SPACE and tokens[position - 1] != SPACE:
     88             resume = position
     89             while resume < len(tokens) and tokens[resume] == SPACE:
     90                 resume += 1
     91             latest_preferred = _Break(position, resume, hyphenated=False)
     92         if has_content and isinstance(token, SoftHyphen) and used + len('-') <= width:
```

### 22. tests/test_termwrap.py:111

```python
    103     wrap_cases = [
    104         WrapCase(case['text'], case['width'], tuple(case['lines']) if 'lines' in case else None)
    105         for case in raw_cases['wrap']
    106     ]
    107     return width_cases, wrap_cases
    108 
    109 
    110 def generateText(generator: random.Random) -> str:
>>  111     # keep '-' out of the alphabet. stripLayout() removes every '-' as a shown soft hyphen
    112     # fmt: off
    113     ALPHABET = (
    114         'a', 'b', 'c', 'x', ' ', ' ', ' ', '\u00a0', '\u65e5', '\u672c', '\u0301', '\u200b',
    115         '\u200d', '\ufe0f', '\u00ad', '\x1b[1m', '\x1b[31m', '\x1b[0m', '\x1b[m', '\n',
    116     )
    117     # fmt: on
    118     return ''.join(generator.choices(ALPHABET, k=generator.randint(0, 40)))
    119 
    120 
    121 def stripLayout(text: str) -> str:
```
