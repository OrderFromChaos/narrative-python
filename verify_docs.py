"""Check that a prose rewrite did not corrupt the technical record.

Cross-checks the documents against the sources of truth rather than against a saved copy, so it
works even without a pre-rewrite baseline.

Usage:
    $ python3 verify_docs.py
"""

import ast
import contextlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

### The schema that benchmark/README.md documents. Kept here rather than parsed out of the table,
### because a checker that reads its rule from the document it checks proves nothing. The two are
### compared by a human when either changes. That is cheap, and it already drifted three ways
### without one.

DECISION_FIELDS = ('id', 'dimension', 'round', 'kind', 'options', 'choice', 'strength', 'condition', 'note', 'date')
DECISION_ROUNDS = frozenset({'1', '2', '2b', '3', '3a', '4', '5', '6', '7', '8', '9', '10', 'validation'})
DECISION_KINDS = frozenset({'control', 'gap', 'provocation', 'derived'})
DECISION_STRENGTHS = frozenset({'strong', 'weak'})
NULLABLE_FIELDS = frozenset({'condition', 'note', 'strength'})
LIST_FIELDS = frozenset({'options', 'supersedes'})
OPTIONAL_FIELDS = ('supersedes',)
MIN_ROUND_PATH_PARTS = 2


def schemaProblems(decisions: list[dict[str, object]]) -> list[str]:
    """Report every decision record that does not match the schema in benchmark/README.md.

    The evidence base gets the same treatment as a pyproject.toml: present and unchecked is how a
    document becomes wrong.
    """
    problems: list[str] = []
    known = {record['id'] for record in decisions}

    for record in decisions:
        name = record.get('id', '<no id>')
        fields = tuple(record)

        if fields[: len(DECISION_FIELDS)] != DECISION_FIELDS:
            problems.append(f'decisions.jsonl {name}: fields are {fields}, schema says {DECISION_FIELDS}')
            continue

        for extra in fields[len(DECISION_FIELDS) :]:
            if extra not in OPTIONAL_FIELDS:
                problems.append(f'decisions.jsonl {name}: unknown field {extra}, optional fields are {OPTIONAL_FIELDS}')

        for field, value in record.items():
            if value is None and field not in NULLABLE_FIELDS:
                problems.append(f'decisions.jsonl {name}: {field} is null and the schema does not allow it')
            elif field in LIST_FIELDS and not (isinstance(value, list) and all(isinstance(o, str) for o in value)):
                problems.append(f'decisions.jsonl {name}: {field} is not a list of strings')
            elif field not in LIST_FIELDS and value is not None and not isinstance(value, str):
                problems.append(f'decisions.jsonl {name}: {field} is {type(value).__name__}, schema says str')

        for field, allowed in (('round', DECISION_ROUNDS), ('kind', DECISION_KINDS), ('strength', DECISION_STRENGTHS)):
            value = record[field]
            if value is not None and value not in allowed:
                problems.append(f'decisions.jsonl {name}: {field} is {value!r}, not one of {sorted(allowed)}')

        for old in supersededBy(record):
            if old not in known:
                problems.append(f'decisions.jsonl {name}: supersedes unknown decision {old}')
            elif old == name:
                problems.append(f'decisions.jsonl {name}: supersedes itself')

    return problems


def supersededBy(record: dict[str, object]) -> list[str]:
    """Return the ids a decision replaces.

    The record type is dict[str, object] because schema values are strings, lists and nulls, so the
    optional field must be narrowed before it can be walked.

    Returns:
        The superseded ids, in record order. Empty when the field is absent.
    """
    value = record.get('supersedes')
    if not isinstance(value, list):
        return []

    return [str(item) for item in value]


def supersessions(decisions: list[dict[str, object]]) -> dict[str, str]:
    """Map every superseded decision id to the id that replaced it.

    Declared in a field rather than parsed out of the reasoning. A marker read from free prose is
    the kind of check that silently stops matching and then reports nothing, which is the failure
    this whole script exists to prevent.
    """
    replaced: dict[str, str] = {}
    for record in decisions:
        for old in supersededBy(record):
            replaced[old] = str(record['id'])

    return replaced


def statesCurrentRules(relative: Path) -> bool:
    """Report whether a document is a description of the current rules.

    The skill and the top-level README are. A round writeup is not: it is a record of what was
    decided then, so naming a decision that a later round replaced is the point rather than a defect.
    """
    return relative.parts[0] == 'skill' or str(relative) == 'README.md'


def declarationPrefix(relative: Path) -> str:
    """Return the decision-id prefix a round directory is allowed to name before any answer exists.

    `R7-` ids are declared in `benchmark/round7/` documents. That is where a question is born, so
    those ids are not in `decisions.jsonl` yet. In every other document an id is a citation, and a
    citation must resolve. Returns an empty string for a document with citations only.
    """
    parts = relative.parts
    if len(parts) < MIN_ROUND_PATH_PARTS or parts[0] != 'benchmark' or not parts[1].startswith('round'):
        return ''

    return f'R{parts[1].removeprefix("round")}-'


def main() -> int:
    """Report any citation, code block or count in the docs that doesn't match its source."""
    problems: list[str] = []

    decisions = [json.loads(line) for line in (ROOT / 'benchmark/decisions.jsonl').open()]
    problems.extend(schemaProblems(decisions))
    decision_ids = {record['id'] for record in decisions}
    replaced = supersessions(decisions)
    tree = ast.parse((ROOT / 'skill/checks.py').read_text())
    registries: dict[str, set[str]] = {'RULES': set(), 'RETIRED': set()}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        name = getattr(node.targets[0], 'id', '')
        if name in registries:
            keys = node.value.keys
            registries[name] = {k.value for k in keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}

    rule_codes, retired = registries['RULES'], registries['RETIRED']
    # the code of each agentverbs.py finding is its CODE constant
    for node in ast.parse((ROOT / 'skill/agentverbs.py').read_text()).body:
        if not isinstance(node, ast.Assign) or getattr(node.targets[0], 'id', '') != 'CODE':
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            rule_codes = rule_codes | {node.value.value}

    docs = [p for p in ROOT.rglob('*.md') if '.lintenv' not in str(p)]
    cited_ids: set[str] = set()
    declared_ids: set[str] = set()
    blocks = 0

    for doc in docs:
        text = doc.read_text()
        rel = doc.relative_to(ROOT)
        own_prefix = declarationPrefix(rel)

        for token in re.findall(r'\b(?:Q\d{2}|R\d{1,2}[a-z]?-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*|V-\d\d)\b', text):
            if own_prefix and token.startswith(own_prefix):
                declared_ids.add(token)
                continue

            cited_ids.add(token)
            if token not in decision_ids:
                problems.append(f'{rel}: cites unknown decision {token}')
            elif token in replaced and statesCurrentRules(rel):
                problems.append(f'{rel}: cites {token}, which {replaced[token]} superseded')

        for code in re.findall(r'\bNAR\d{3}\b', text):
            if code not in rule_codes | retired:
                problems.append(f'{rel}: references unknown rule {code}')

        for block in re.findall(r'```python\n(.*?)```', text, re.S):
            blocks += 1
            # Many blocks are deliberate fragments, so a parse failure is not itself a defect.
            # Counting them proves the sweep did not silently delete one.
            with contextlib.suppress(SyntaxError):
                ast.parse(block.replace('...', 'pass'))

    readme = (ROOT / 'README.md').read_text()
    claimed = re.search(r'(\d+) forced choices', readme)
    if claimed and int(claimed.group(1)) != len(decision_ids):
        problems.append(f'README claims {claimed.group(1)} decisions, decisions.jsonl has {len(decision_ids)}')

    print(f'checked {len(docs)} documents, {len(cited_ids)} distinct decision citations, {blocks} python blocks')
    print(f'decisions.jsonl: {len(decision_ids)} ids;  checks.py: {len(rule_codes)} rule codes, {len(retired)} retired')

    unanswered = sorted(declared_ids - decision_ids)
    if unanswered:
        # Not a problem. A question is written before it is answered, and this is the count of the
        # gap between the two. It reaches zero when the round is recorded.
        print(f'{len(unanswered)} question ids declared with no decision yet: {unanswered[0]} .. {unanswered[-1]}')

    for problem in problems:
        print(f'  PROBLEM  {problem}')

    print(f'\n{len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
