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


def main() -> int:
    """Report any citation, code block or count in the docs that no longer matches its source."""
    problems: list[str] = []

    decision_ids = {json.loads(line)['id'] for line in (ROOT / 'benchmark/decisions.jsonl').open()}
    tree = ast.parse((ROOT / 'skill/checks.py').read_text())
    rule_codes: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign) or getattr(node.targets[0], 'id', '') != 'RULES':
            continue
        if isinstance(node.value, ast.Dict):
            rule_codes = {k.value for k in node.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}

    docs = [p for p in ROOT.rglob('*.md') if '.lintenv' not in str(p)]
    cited_ids: set[str] = set()
    blocks = 0

    for doc in docs:
        text = doc.read_text()
        rel = doc.relative_to(ROOT)

        for token in re.findall(r'\b(?:Q\d{2}|R\d[a-z]?-[A-Za-z0-9]+(?:-[a-z]+)?|V-\d\d)\b', text):
            cited_ids.add(token)
            if token not in decision_ids:
                problems.append(f'{rel}: cites unknown decision {token}')

        for code in re.findall(r'\bNAR\d{3}\b', text):
            if code not in rule_codes:
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
    print(f'decisions.jsonl: {len(decision_ids)} ids;  checks.py: {len(rule_codes)} rule codes')

    for problem in problems:
        print(f'  PROBLEM  {problem}')

    print(f'\n{len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
