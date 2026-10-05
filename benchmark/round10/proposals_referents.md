# Proposals: noun referents and case coverage

Source: a review pass by another agent on a PR in a private repository, with the user's ratings. Eight of
its eleven rewrites were rated great, and the user called the exchange very fruitful. The examples
below are rewritten from this repository's benchmark runs, because the originals are private.

All five are applied. 4 was reworded as numbered steps in a section of their own (R10-closing-review). Ids are `R10-` because round 10 is still open.

## What the eleven hits had in common

Almost every sentence passed the agent-verb check (`NAR017`) and failed a different one:

- the noun named something that did not exist yet, or a property of another object
- a pronoun or `such` with no clear antecedent
- a claim true in one case of several
- a count of the wrong unit
- error advice pointing at a place the program had already searched

The user's two corrections add a third rule and a cut:

- #2: after the fix, a clause that only explained the wrong noun stayed (`The compose file declares
  it external`). The user: "why even add" it. The restatement gate covers this.
- #3 and #4: two sentences about two different approaches read as one. The user: they "should say
  'Alternatively, …' to make it clear they are talking about different approaches".

## 1. Every noun phrase picks out one real thing

For **Sentence form**:

> - every noun phrase picks out one real thing, at the moment the sentence is about. Name the object
>   in the program each noun phrase refers to, and rewrite when:
>   - the thing does not exist yet, or does not have its property yet: `# open() creates a missing
>     log file` → `# open() creates the log file if it doesn't exist`
>   - the property belongs to another object: `# in the snapshot's timezone` → `# in the policy's
>     timezone`. A snapshot name is in UTC, and the timezone comes from the policy
>   - the referent is gone or ambiguous: `tz=None leaves TOML local times without one` → `without a
>     UTC offset`. A pronoun at the start of a sentence can refer to the subject of either sentence
>     before it, so repeat the noun
>   (R10-referent)

The middle example is from P3. The last is #17 of the new-rules cycle, which the user flagged in
R10-rating14.

## 2. A claim holds in every case that reaches it, or names its case

For **Sentence form**:

> - a claim holds in every case that reaches it, or names its case. List the paths that reach the
>   sentence:
>   - `# an expired item is removed on lookup` → `# an expired item is removed on lookup, or before
>     any eviction`
>   - `Returns the cached copy.` → `Returns the cached copy when one exists, otherwise the downloaded
>     one.`
>   - count the unit the code counts: `# every file is counted` → `# the lines of every file are
>     counted`
>   - advice in an error message names something the program has not tried: `no policy file found.
>     Check the input directory` → `no policy.json in fixture/. Pass --policy to use another file`
>   (R10-case-coverage)

The first is from the P8 runs, where expired items were dropped on lookup and in a sweep before
eviction. The last is from P4, whose policy path defaults to the input directory.

## 3. Mark a switch to another approach

For **Sentence form**:

> - when a comment moves from one approach to another, mark the switch with `Alternatively,` or
>   `Instead,`: `# open(path, 'w') empties the file before writing. Alternatively, os.replace()
>   swaps in a complete copy`. Without the marker, the reader takes the second sentence as more about the first thing
>   (R10-alternative-marker)

From #3 and #4 of the user's ratings. The example is new, with nothing from the private repository.
This one may be too specific for the skill. The user
dislikes narrow rules, so the alternative is to fold it into proposal 1 as a fourth case: "two
things fit it".

## 4. Extend the closing review

Change **Before you finish** to:

> For each one, name the subject and the verb and ask whether that subject can perform that verb.
> Then name the object each noun phrase refers to, and the cases in which the sentence holds.

The other agent's hit rate came from this review, and `verify.py` already prints the list.

## 5. Messages and help text

Change "These rules cover docstring prose too." to:

> These rules cover docstring prose, error messages and `--help` text too. `verify.py` lists comments
> and docstrings only, so read messages and help text by hand.

Three of the eleven hits were in an error message, the help text and a docstring.

## No linter

Neither rule can be checked by a tool. Each gets a decision id, which the skill requires of a rule
with no linter.
