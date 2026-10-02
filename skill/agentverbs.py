"""Flag comments and docstrings whose subject cannot act, paired with a verb for a mental act.

`a period ranks by its newest snapshot` makes a period rank, and `the report names it` makes a
report speak. A subject acts when it is a person, an animal, a role such as `caller`, or a pronoun
for one. A verb counts as mental when its most frequent WordNet sense is cognition,
communication or perception, or when it is on MIND_EXTRA. Verbs on LITERAL never count.

There are four ways to read a subject and its verb, because the parse of a terse comment is often
wrong on words that are both noun and verb (`a plan marks`):
- the dependency parse: a nominal subject of a verb, with `that` and `which` read as the noun
  their clause attaches to
- a coordinated verb takes the subject of its clause: `the file is malformed, or names a zone`
- agreement: after a singular determiner, a noun followed by an `-s` word makes that word a verb
- a modal: `a policy can judge`

It imports spaCy and loads its `en_core_web_md` model, both pinned in requirements-lock.txt.
verify.py runs it with the interpreter of the lint venv.

Usage:
    $ .lintenv/bin/python agentverbs.py src/
    src/join.py:73: NAR017 'period ranks': agent verb on a subject that cannot act
    $ .lintenv/bin/python agentverbs.py --lines sample.txt
    $ .lintenv/bin/python agentverbs.py --score gold.tsv
    precision 1.00, recall 0.91 (29 of 32 found, 0 false)

A line with `# noqa: NAR017` or a bare `# noqa` is skipped.

Exit codes:
    0  nothing flagged
    1  at least one line flagged
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token


CODE = 'NAR017'
MESSAGE = 'agent verb on a subject that cannot act'
WORDS_PATH = Path(__file__).resolve().parent / 'words.json'
MODEL = 'en_core_web_md'

# verbs whose most frequent WordNet sense is not a mind class, but which make their subject a mind
MIND_EXTRA = frozenset({
    'keep', 'hold', 'carry', 'own', 'know', 'decide', 'want', 'need', 'see', 'find', 'judge', 'rank',
    'mark', 'name', 'state', 'say', 'tell', 'list', 'assume', 'expect', 'consider', 'treat', 'care',
    'trust', 'promise', 'insist', 'refuse',
})  # fmt: skip
# what code does, and stative verbs for a relation rather than an act
LITERAL = frozenset({
    'return', 'raise', 'read', 'write', 'call', 'skip', 'parse', 'yield', 'print', 'log', 'match',
    'compare', 'accept', 'reject', 'contain', 'count', 'sort', 'map', 'have', 'be', 'fail', 'admit',
    'split', 'follow', 'drop', 'stop', 'start', 'run', 'pass', 'take', 'mean', 'imply', 'indicate',
    'look', 'seem', 'appear', 'specify', 'require', 'signal', 'point', 'check', 'will', 'decode',
    'encode', 'subtract', 'refer', 'resolve',
})  # fmt: skip
ROLES = frozenset({
    'i', 'you', 'we', 'he', 'she', 'they', 'who', 'someone', 'nobody', 'everyone', 'user', 'caller',
    'reader', 'developer', 'operator', 'customer', 'maintainer', 'reviewer', 'whoever', 'anyone',
    'anybody', 'somebody',
})  # fmt: skip
# noun.person in WordNet, but programs in code
PROGRAMS = frozenset({
    'scanner', 'exporter', 'importer', 'writer', 'sender', 'receiver', 'listener', 'watcher',
    'worker', 'server', 'client', 'scheduler', 'runner', 'checker', 'validator', 'formatter',
    'handler', 'parser', 'loader', 'reporter',
})  # fmt: skip
SINGULAR_DETERMINERS = frozenset({'a', 'an', 'each', 'every', 'this', 'its', 'one'})
# a container verb counts only with an object: `a file holds whole bytes`, not `the invariant holds`  # noqa: NAR016
CONTAINER_VERBS = frozenset({'hold', 'keep', 'carry', 'own'})
MODALS = frozenset({'can', 'cannot', 'could', 'would', 'will', 'may', 'might', 'must', 'should'})
IDENTIFIER = re.compile(r'[_()`.\[\]]|[a-z][A-Z]')
PRAGMA = re.compile(r'(?:noqa|type:|pragma|fmt:|ruff:|pylint:|mypy:)')
NOQA = re.compile(r'#\s*noqa(?::\s*(?P<codes>[A-Z0-9, ]+))?')
# a quoted span is code or an example, not a sentence of the comment
QUOTED = re.compile(r"`[^`]*`|(?<!\w)'[^'\n]+'(?!\w)")
AGREEMENT_WINDOW = 5


def main() -> int:
    """Check the paths given, or flag or score a text file.

    Returns:
        1 when a line is flagged, otherwise 0. Scoring always returns 0.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='*', type=Path)
    parser.add_argument('--lines', type=Path, help='flag each line of a plain text file')
    parser.add_argument('--score', type=Path, help='score against a label<TAB>text file')
    args = parser.parse_args()

    reader = SentenceReader.load(WORDS_PATH)
    if args.score:
        return scoreLabels(reader, args.score)
    if args.lines:
        flagged = 0
        for text in args.lines.read_text(encoding='utf-8').splitlines():
            if hits := reader.agentVerbs(text):
                flagged += 1
                print(f'{text}   <- {"; ".join(hits)}')
        return 1 if flagged else 0

    findings: list[Finding] = []
    for checked_file in discoverPython(args.paths):
        findings.extend(checkFile(reader, checked_file))
    for finding in findings:
        print(f'{finding.checked_file}:{finding.line}: {CODE} {finding.hit!r}: {MESSAGE}')
    return 1 if findings else 0


def scoreLabels(reader: SentenceReader, labels_path: Path) -> int:
    """Compare the check with hand labels: `agent` or `ok`, a tab, then the line.

    Returns:
        0, after printing precision, recall and every disagreement.
    """
    found = false = missed = labelled = 0
    for row in labels_path.read_text(encoding='utf-8').splitlines():
        label, text = row.split('\t', 1)
        hits = reader.agentVerbs(text)
        labelled += label == 'agent'
        if hits and label == 'agent':
            found += 1
        elif hits:
            false += 1
            print(f'false: {text}   <- {"; ".join(hits)}')
        elif label == 'agent':
            missed += 1
            print(f'missed: {text}')

    precision = found / max(found + false, 1)
    recall = found / max(labelled, 1)
    print(f'precision {precision:.2f}, recall {recall:.2f} ({found} of {labelled} found, {false} false)')
    return 0


def discoverPython(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        files.extend(sorted(target.rglob('*.py')) if target.is_dir() else [target])
    return files


def checkFile(reader: SentenceReader, checked_file: Path) -> list[Finding]:
    """Flag every comment and docstring line of one file, skipping lines silenced with noqa.

    Returns:
        One finding per agent verb.
    """
    source = checked_file.read_text(encoding='utf-8')
    silenced = silencedLines(source)
    findings: list[Finding] = []
    for number, text in sorted([*commentLines(source), *docstringLines(ast.parse(source))]):
        if number in silenced:
            continue
        findings.extend(Finding(checked_file, number, hit) for hit in reader.agentVerbs(text))
    return findings


def silencedLines(source: str) -> set[int]:
    silenced: set[int] = set()
    for number, line in enumerate(source.splitlines(), start=1):
        if (pragma := NOQA.search(line)) and (pragma['codes'] is None or CODE in pragma['codes']):
            silenced.add(number)
    return silenced


def commentLines(source: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        text = token.string.lstrip('#').strip()
        if text and not PRAGMA.match(text):
            lines.append((token.start[0], text))
    return lines


def docstringLines(tree: ast.Module) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if ast.get_docstring(node) is None or not isinstance(node.body[0], ast.Expr):
            continue
        literal = node.body[0].value
        if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
            continue
        for offset, text in enumerate(literal.value.splitlines()):
            stripped = text.strip()
            if stripped and not stripped.startswith(('$', '>>>')):
                lines.append((literal.lineno + offset, stripped))
    return lines


### vocabulary #########################################################################################


@dataclass(frozen=True)
class Finding:
    checked_file: Path
    line: int
    hit: str


@dataclass(frozen=True)
class SentenceReader:
    """The parser and the word lists, loaded once per run."""

    nlp: Language
    animate_nouns: frozenset[str]
    mind_verbs: frozenset[str]
    verbs: frozenset[str]

    @classmethod
    def load(cls, words_path: Path) -> SentenceReader:
        words = json.loads(words_path.read_text(encoding='utf-8'))
        mind = (frozenset(words['mind_verbs']) | MIND_EXTRA) - LITERAL
        animate = (frozenset(words['animate_nouns']) | ROLES) - PROGRAMS
        return cls(spacy.load(MODEL), animate, mind, frozenset(words['verbs']))

    def agentVerbs(self, text: str) -> list[str]:
        """Find each subject that cannot act, paired with a verb for a mental act.

        Returns:
            One `subject verb` string per hit, in sentence order.
        """
        doc = self.nlp(QUOTED.sub('value', text))
        hits = {
            **self._parsedSubjects(doc),
            **self._coordinatedSubjects(doc),
            **self._agreeingSubjects(doc),
            **self._modalSubjects(doc),
        }
        return [hits[index] for index in sorted(hits)]

    def _parsedSubjects(self, doc: Doc) -> dict[int, str]:
        hits: dict[int, str] = {}
        for token in doc:
            if token.dep_ != 'nsubj' or token.head.pos_ not in ('VERB', 'AUX'):
                continue
            verb = token.head
            if self._misreadSubject(token, verb):
                continue
            if not self._canAct(token) and self._needsMind(verb):
                hits[verb.i] = f'{token.text} {verb.text}'
        return hits

    def _needsMind(self, verb: Token) -> bool:
        lemma = verb.lemma_.lower()
        if lemma in CONTAINER_VERBS:
            # in `the periods its rule keeps`, the object stands before the relative clause
            return verb.dep_ in ('relcl', 'ccomp') or any(c.dep_ in ('dobj', 'attr') for c in verb.children)
        return lemma in self.mind_verbs

    def _misreadSubject(self, subject: Token, verb: Token) -> bool:
        """Recognise a parse whose subject and verb are not a subject and a verb.

        Terse comments yield imperatives read as subjects, noun compounds read as clauses, and
        list items read as subjects of the verb after the list.

        Returns:
            True when the pair is a misreading and must not be flagged.
        """
        children = list(verb.children)
        clause_start = subject.i == 0 or subject.nbor(-1).pos_ in ('PUNCT', 'CCONJ')
        imperative_opener = clause_start and subject.lower_ in self.verbs and not list(subject.children)
        bare_verb_word = subject.lower_ in self.verbs and subject.tag_ == 'NN' and not list(subject.children)
        # `the code see`: a singular noun takes no base-form verb, so this is no subject and verb
        disagrees = (
            subject.tag_ in ('NN', 'NNP') and verb.tag_ in ('VB', 'VBP') and not any(c.dep_ == 'aux' for c in children)
        )
        bare_participle = verb.tag_ == 'VBN' and not any(c.dep_ in ('aux', 'auxpass') for c in children)
        # `at least one line flagged`: a past form with no object at the end of a phrase
        phrase_end = verb.i == len(verb.doc) - 1 or verb.nbor(1).is_punct
        final_participle = verb.tag_ == 'VBD' and phrase_end and not any(c.dep_ == 'dobj' for c in children)
        listed = any(c.dep_ == 'cc' for c in subject.children)
        # `the prices file`: a plural noun, then a word with no object, is a compound
        compound = (
            subject.tag_ == 'NNS'
            and verb.i == subject.i + 1
            and not any(c.dep_ in ('dobj', 'attr', 'ccomp', 'xcomp') for c in children)
        )
        # `the word lists for`: after `the`, a noun, then an `-s` word and a preposition, is a compound
        the_compound = (
            subject.tag_ == 'NN'
            and verb.tag_ == 'VBZ'
            and verb.i == subject.i + 1
            and not phrase_end
            and verb.nbor(1).pos_ == 'ADP'
            and any(c.lower_ == 'the' for c in subject.children)
        )
        other_subject = any(c.dep_ == 'nsubj' and c.i != subject.i and self._canAct(c) for c in children)
        # `withdrawn codes: kept so ...`: punctuation between the two ends the clause
        separated = any(t.is_punct for t in verb.doc[min(subject.i, verb.i) + 1 : max(subject.i, verb.i)])
        modal = verb.lower_ in MODALS
        return (
            imperative_opener
            or bare_verb_word
            or disagrees
            or bare_participle
            or final_participle
            or listed
            or separated
            or compound
            or the_compound
            or other_subject
            or modal
        )

    def _coordinatedSubjects(self, doc: Doc) -> dict[int, str]:
        hits: dict[int, str] = {}
        for token in doc:
            if token.dep_ != 'conj' or not token.lower_.endswith('s') or token.lower_[:-1] not in self.mind_verbs:
                continue
            # a verb takes an object: `names an unknown timezone`, not `fractions of a cent`
            if token.i + 1 >= len(doc) or doc[token.i + 1].pos_ not in ('DET', 'ADJ', 'NOUN', 'PROPN', 'NUM'):
                continue
            clause = token.head
            while clause.dep_ in ('conj', 'attr', 'acomp') and clause.head.i != clause.i:
                clause = clause.head
            subjects = [c for c in clause.children if c.dep_ == 'nsubj']
            if subjects and not self._canAct(subjects[0]):
                hits[token.i] = f'{subjects[0].text} {token.text}'
        return hits

    def _agreeingSubjects(self, doc: Doc) -> dict[int, str]:
        """Read a noun and a following `-s` word as subject and verb where grammar allows only that.

        After a singular determiner, `a plan marks` cannot be a plural noun phrase. After an
        identifier or `the` that opens a relative clause, `the month raw_month names` and `every
        file the audit needs` cannot either.

        Returns:
            Verb index to `subject verb`.
        """
        hits: dict[int, str] = {}
        for token in doc[1:]:
            left = doc[token.i - 1]
            if not token.lower_.endswith('s') or left.lower_.endswith('s') or left.pos_ == 'DET':
                continue
            # `the Move it names`: after `it`, an `-s` word is a verb
            if left.lower_ == 'it' and token.lower_[:-1] in self.mind_verbs:
                hits[token.i] = f'{left.text} {token.text}'
                continue
            if left.pos_ not in ('NOUN', 'PROPN', 'ADJ', 'NUM', 'X') or self._canAct(left):
                continue
            phrase = doc[max(0, token.i - AGREEMENT_WINDOW) : token.i]
            # a determiner before a preposition belongs to another noun phrase
            boundary = max((t.i for t in phrase if t.pos_ in ('ADP', 'PUNCT')), default=phrase.start - 1)
            determiners = [
                t.lower_ for t in phrase if t.i > boundary and (t.pos_ == 'DET' or t.lower_ in SINGULAR_DETERMINERS)
            ]
            singular = bool(determiners) and determiners[-1] in SINGULAR_DETERMINERS
            # `every file the audit needs`: a noun, then `the` and a noun, opens a relative clause
            the_index = next((t.i for t in reversed(phrase) if t.lower_ == 'the' and t.i > boundary), None)
            relative = the_index is not None and the_index > 0 and doc[the_index - 1].pos_ in ('NOUN', 'PROPN')
            singular = singular or (relative and left.tag_ in ('NN', 'NNP'))
            reduced_relative = IDENTIFIER.search(left.text) and left.i > 0 and doc[left.i - 1].pos_ in ('NOUN', 'DET')
            if (singular or reduced_relative) and token.lower_[:-1] in self.mind_verbs:
                hits[token.i] = f'{left.text} {token.text}'
        return hits

    def _modalSubjects(self, doc: Doc) -> dict[int, str]:
        hits: dict[int, str] = {}
        for token in doc[1 : len(doc) - 1]:
            left, verb = doc[token.i - 1], doc[token.i + 1]
            if token.lower_ not in MODALS or left.pos_ not in ('NOUN', 'PROPN') or self._canAct(left):
                continue
            if verb.lemma_.lower() in self.mind_verbs:
                hits[token.i] = f'{left.text} {token.text} {verb.text}'
        return hits

    def _canAct(self, subject: Token) -> bool:
        if subject.lower_ in ('that', 'which') and subject.head.dep_ == 'relcl':
            subject = subject.head.head
        if subject.ent_type_ == 'PERSON':
            return True
        if IDENTIFIER.search(subject.text):
            return False
        return subject.lower_ in self.animate_nouns or subject.lemma_.lower() in self.animate_nouns


if __name__ == '__main__':
    sys.exit(main())
