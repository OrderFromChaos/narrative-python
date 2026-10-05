"""Write the skill documents' prose and comment examples as Python files, so agentverbs.py can read them.

Two files per document, each keeping the line numbers of its source:
- `SKILL.py`: the prose and headings as whole-line comments. Code blocks, table rows and blank lines
  become blank lines. Bold markers and list dashes are stripped, because the parser reads `**Term**`
  and `- item` as words.
- `SKILL_examples.py`: every comment example, from backticks in the prose and from code blocks, as a
  trailing comment. agentverbs.py skips backticked text in prose, and reads each trailing comment as a
  separate passage, so each example is checked alone.

Usage:
    $ python3 prose_as_comments.py OUT_DIR
    $ .lintenv/bin/python skill/agentverbs.py OUT_DIR
    OUT_DIR/SKILL.py:171: NAR017 'module must understand': agent verb on a subject that cannot act
"""

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DOCUMENTS = ('skill/SKILL.md', 'skill/architecture.md', 'skill/tooling.md')
# matches:
# a backticked `# vendor closes idle sockets at 60 s`
# rejects:
# a backticked `x = 1`
INLINE_COMMENT = re.compile(r'`#\s+([^`]+)`')
# matches:
# `x = 1  # sorted`
# `# sorted`
# rejects:
# `'#' in text`
CODE_COMMENT = re.compile(r'(?:^|\s)#\s+(.+)$')


def main() -> int:
    """Write the prose file and the examples file of each skill document into the directory given."""
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for document in DOCUMENTS:
        source = REPO / document
        markdown = source.read_text(encoding='utf-8')
        prose, examples = splitDocument(markdown)
        (out_dir / f'{source.stem}.py').write_text(prose)
        (out_dir / f'{source.stem}_examples.py').write_text(examples)
    return 0


def splitDocument(markdown: str) -> tuple[str, str]:
    """Split a Markdown document into its prose and its comment examples, one output line per input line.

    Raises:
        Nothing. Any text is accepted.
    """
    prose: list[str] = []
    examples: list[str] = []
    in_code = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            prose.append('')
            examples.append('')
            continue

        if in_code:
            found = CODE_COMMENT.search(line)
            comments = [found.group(1)] if found and not stripped.startswith('###') else []
        else:
            comments = INLINE_COMMENT.findall(line)
        examples.append(f'_ = 0  # {" / ".join(comments)}' if comments else '')

        if in_code or not stripped or stripped.startswith(('|', '---')):
            prose.append('')
            continue
        prose.append('# ' + stripped.lstrip('#').lstrip('-').strip().replace('**', ''))
    return '\n'.join(prose) + '\n', '\n'.join(examples) + '\n'


if __name__ == '__main__':
    sys.exit(main())
