---
name: self-consistency-narrative
description: Check the Narrative skill's own files against its own rules, so no violation reaches agents that load it. Covers the prose, headings and comment examples of skill/*.md, the comments, docstrings and messages of skill/*.py, and the shipped config comments, and applies every rule added since the last pass. Use when the user asks for a self-consistency pass, a self-evaluation, or to re-apply the rules to the skill.
---

# Self-consistency pass on the Narrative skill

Agents copy the skill's examples and wording. A violation in `skill/` teaches the violation, so the
skill's own text must pass its own rules. This pass finds the violations, fixes the clear ones and
reports the rest.

Repository root: the directory with `skill/`, `benchmark/` and `verify_docs.py`. `S` below is a
directory in the scratchpad.

## 1. Rules added since the last pass

List the decisions added since the last commit that touched `skill/`:

```bash
git log -1 --format=%cs -- skill/
```

Read every record in `benchmark/decisions.jsonl` with that date or later. For each rule, search the
skill files for text that breaks it, and for examples that teach the old form. A new rule usually
makes some older example wrong.

## 2. Mechanical checks

```bash
.lintenv/bin/python .claude/skills/self-consistency-narrative/prose_as_comments.py S
.lintenv/bin/python skill/agentverbs.py S
.lintenv/bin/python skill/checks.py S --select NAR013 --select NAR014 --select NAR015 --select NAR016 --select NAR018
```

`prose_as_comments.py` writes `SKILL.py` (prose and headings) and `SKILL_examples.py` (every comment
example) for each document, keeping line numbers, so a finding at `SKILL.py:171` is line 171 of
`skill/SKILL.md`.

Then the scripts, from a directory whose `pyproject.toml` is the skill's config:

```bash
cp skill/pyproject-snippet.toml S/pyproject.toml
cd S && PATH=<repo>/.lintenv/bin:$PATH <repo>/.lintenv/bin/python <repo>/skill/verify.py --venv <repo>/.lintenv <repo>/skill/verify.py <repo>/skill/checks.py <repo>/skill/agentverbs.py
```

All 7 checks must pass. Read the comment and docstring list it prints, and the scripts' error messages and `--help` text, through the steps of **Prose review** under **Procedures**.

```bash
.lintenv/bin/python skill/agentverbs.py --score benchmark/round10/agentverb/gold.tsv
.lintenv/bin/python verify_docs.py
```

The gold score must not drop. `verify_docs.py` must report 0 problems, including the README's
decision count.

## 3. What the checks miss

`agentverbs.py` misses a plural-looking verb after a long subject (`An error for malformed input
names the expected form`) and anything in backticks in prose. Search for those directly:

```bash
grep -nE "\b(error|guard|message|comment|function|module|test|file|docstring|name|check|rule|code|type|key|record|sample|example|regex|line|branch|table|value|field|report|log|plan|policy|config|tool|program|class|section|annotation|signature)s? (names|says|states|tells|knows|wants|needs|decides|shows|records|documents|describes|explains|expects|assumes|reports|sees|finds|holds|carries|keeps|owns)\b" skill/*.md
```

Read for these by eye, in prose, headings, comment examples, example docstrings, finding messages
in `checks.py` and comments in `pyproject-snippet.toml` and `requirements-lock.txt`:
- a colon, dash or semicolon joining two clauses (a colon before a list or a code example is fine)
- `, which`, `, since` and other connectives where two sentences read better
- `without X,` and `X would` in a comment example, where the fact can be stated directly
- spoken or physical metaphors (`said slowly`, `anchors it`, `a file records`), personified
  placement (`Where a constant lives`, `it lives in`, `its only home`), and vague `it` or `them`.
  `grep -nE '\blives?\b|\bhome\b|, which |, since ' skill/*.md` finds most of them
- intensifiers (`perfectly`, `genuinely`, `actually`)
- `its own`, `their own`, `on its own` anywhere in prose, not only in comments
- a comment example that breaks a rule beside it, such as a one-line comment with a capital or a
  final period

## 4. Known false positives

Do not fix these, and do not re-report them as new:
- a person as the real subject, misread by the parser: `A reader who has never opened the module
  must understand`, `the person making an edit must know`, `a reader arriving … from a stack trace
  sees`, `Could someone change this value safely knowing`, `The reader needs every shape the module
  can emit and needs no volume`
- verb-shaped modifiers: `thinking traces`, `is missing`, `attribute declared in`, `a group described
  only with`, `database values`
- literal code verbs the lists do not cover: `declares global`, `may catch it` (an exception), `hold
  open` and `an idle hold` (a file handle or connection)
- the rule text naming the word it bans (`deliberately`, `holds`, `its own`, `no longer` in the
  bullets that ban them), quoted bad examples, and dashes after a list-item term
- decision ids and the missing module docstring in the generated files

When a hit is new, judge it by reading the sentence: does a non-person subject do something only a
mind does?

## 5. Fix and report

- Fix clear violations in place. Rewrite the sentence. Do not delete words until it passes.
- A fix that changes what a rule says, adds a rule or removes one is a rule change. Put it to the
  user first. Long proposals go in a file under `benchmark/round10/` and the question stays short.
- A changed example that a decision quotes gets a note on that decision.
- Run every check in section 2 again after the fixes.
- Report in plain language: what was fixed (before → after for the notable ones), what a check
  missed, judgement calls left alone, and proposals. Check the report's own sentences for agent
  verbs before sending.
- Never commit. After the user commits, `./install.sh` updates the installed copy.
