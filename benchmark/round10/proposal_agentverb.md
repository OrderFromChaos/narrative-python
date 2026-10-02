# Agent-verb check: prototype results and decisions

## How it works

A check over every comment and docstring line:

1. **Find subject and verb.** spaCy's dependency parser finds each clause's subject and verb. Terse
   comments defeat the parser on noun/verb homographs ("a plan marks", "the month raw_month
   names"), so a second rule reads agreement: a singular determiner cannot start a plural noun
   phrase, so in `a plan marks` the `-s` word is a verb. A third rule catches modals: `a policy can
   judge`.
2. **Is the subject a person?** WordNet's noun classes (`noun.person`, `noun.animal`), a short list
   of role words (`user`, `caller`, `reader`, `developer`, `customer`), and the pronouns. A code
   identifier is never a person.
3. **Does the verb need a mind?** WordNet's verb classes `verb.cognition`, `verb.communication`
   and `verb.perception`, plus a fixed list: `keep`, `hold`, `carry`, `own`, `know`, `decide`,
   `want`, `need`, `see`, `find`, `judge`, `rank`, `mark`, `name`, `state`, `say`, `tell`,
   `list`, `assume`, `expect`.
4. **Allowed:** verbs code literally does (`return`, `raise`, `read`, `write`, `call`, `skip`,
   `parse`, `match`, `accept`, `reject`, `fail`, `admit`, …) and stative verbs (`mean`, `imply`,
   `indicate`, `look`, `seem`, `appear`, `specify`, `require`).

## Results

| text | lines | flagged | rate |
|---|---|---|---|
| Cycles 7–8 comments and docstring summaries (tuned on) | 140 | 18 | 13% |
| CPython stdlib comments, random sample | 1,500 | 52 | 3.5% |
| Round 10 Claude corpus, sentences | 1,058 | 259 | 24.5% |

- **Cycles 7–8:** 17 of 18 flags are agent verbs. It misses 2 that the parser cannot split.
- **Claude corpus, 30 flags judged:**
  - about 23 are agent or container verbs (`SQLite holds two NULLs to be distinct`, `a matched pair
    can disagree`, `the shell records the bare fact`);
  - 4 make a document the agent (`a docstring shows`, `a document cites`, `_SCHEMA declares`);
  - 3 are parser errors.
- **Human stdlib:** about half the flags are personification that humans write too (`socket
  knows`, `an algorithm wants`, `the parser can decide`, `make pdb believe`); the rest are parser
  errors, such as `Tim saw` and `single quotes`.

Model size barely matters: spaCy's 40 MB model and its 400 MB model give 21 and 18 flags on cycles
7–8.

## Decisions

1. **Documents as agents.** Is `the report names it`, `plan.json lists`, `RFC 3548 specifies` or
   `the docstring shows` an agent verb? You flagged `a problem names the line` and `a malformed line
   names no customer`, but rated `basename, as the report names it` fine. Options: flag all; allow
   documents, specs and files with communication verbs; allow only standards and specs.
2. **Dependency weight.** spaCy, the 40 MB English model and NLTK's WordNet data, about 70 MB, pinned
   in `requirements-lock.txt`. `checks.py` stays stdlib-only, so this would be a separate script that
   `verify.py` runs.
3. **Strictness.** A new finding code that fails the run and is silenced with `# noqa`; or an advisory list printed after a passing run, like the comment inventory now
   being tested. At 2–3% false flags on human text, a hard failure would need a `noqa` on roughly one
   comment in forty.
