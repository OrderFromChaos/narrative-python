# The Depth example, and NullHandler

Applied: 1 (a) and 2 (a), with the rule in the imperative and no "nothing else" (R10-depth-example, R10-nullhandler).

## What happened

**Depth** in SKILL.md illustrates a two-sentence comment with this:

```python
# logging.NullHandler() stops the last-resort handler from printing this package's warnings.
# They reach stderr only when the calling program configures logging.
LOG.addHandler(logging.NullHandler())
```

In cycle 13, four packages (P1, P2, P3, P5) added `LOG.addHandler(logging.NullHandler())` to their
`logs.py`, with this comment word for word. The example comes from a cycle 1 package that used
NullHandler (R10-rating3). None of the cycle 5 to 12 review files has one, though they show only
the code around comments. In each of the four, `main()` also adds a stream handler. So the NullHandler
matters only when another program imports the package, which each spec allows ("the computation
must also be importable"). The code is harmless there, and the comment is true, but agents treated
the example as a recipe.

## 1. A new Depth example

The example should show the shape (an outside fact, then what it means for the reader) with content
no task is likely to reuse:

- (a)
  ```python
  # The vendor API returns at most 100 rows per page and no total count.
  # Keep requesting until a page comes back short.
  while len(page := fetchPage(cursor)) == PAGE_SIZE:
  ```
- (b)
  ```python
  # SQLite allows one writer at a time, and a second writer waits 5 s before it fails.
  # Keep write transactions short, or imports fail under the web server's load.
  ```
- (c)
  ```python
  # The bank's export writes amounts with a comma as the decimal separator: 12,50.
  # Convert it before parsing, or the amount splits into two CSV fields.
  ```

(a) is my pick. The second sentence is an action the reader takes, which is the case R10-rating4
asked for ("needs to help the dev understand if they need to take a positive action").

## 2. A NullHandler rule (optional)

Your pasted note proposes this, reworded here for the style:

> Each module gets a logger and nothing else. A package that other programs import adds
> `logging.NullHandler()` once, in its top-level `__init__.py`. A program configures logging once,
> in `main()`, and adds no NullHandler.

One conflict to know about: the skill's file layout uses `LOG = logging.getLogger('app')`, a fixed
name. The note uses `getLogger(__name__)`. In a package, `__name__` gives child loggers that pass
records up to the package logger, and that is what makes "once, in `__init__.py`" work. The rule
would need the layout example changed to `getLogger(__name__)` for packages.

- (a) Add the rule, and change the package logger to `getLogger(__name__)`.
- (b) No rule. The new Depth example removes the prompt, and the four uses were harmless.
