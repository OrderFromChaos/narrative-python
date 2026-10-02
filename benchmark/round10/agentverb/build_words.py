"""Build skill/words.json, the word lists for skill/agentverbs.py, from a WordNet 3.0 database directory.

A noun is animate when its first or second sense by frequency is a person or an animal. A verb counts as
mental when its most frequent sense is cognition, communication or perception. The verb list has
every verb, so a sentence-initial imperative is not read as a subject. agentverbs.py adds
and removes words by hand on top of these lists, which come from WordNet's classes alone.

Usage:
    $ python3 build_words.py ~/nltk_data/corpora/wordnet ../../../skill/words.json
    animate nouns: 16519, mind verbs: 1919
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


ANIMATE_CLASSES = frozenset({'noun.person', 'noun.animal'})
MIND_CLASSES = frozenset({'verb.cognition', 'verb.communication', 'verb.perception'})
NOUN_SENSES_READ = 2


def main() -> None:
    wordnet_dir, words_json_path = Path(sys.argv[1]), Path(sys.argv[2])
    class_names = (wordnet_dir / 'lexnames').read_text(encoding='utf-8').splitlines()
    noun_classes = readSynsetClasses(wordnet_dir / 'data.noun', class_names)
    verb_classes = readSynsetClasses(wordnet_dir / 'data.verb', class_names)

    animate = sorted(
        entry.lemma
        for entry in readIndex(wordnet_dir / 'index.noun')
        if ANIMATE_CLASSES & {noun_classes[offset] for offset in entry.offsets[:NOUN_SENSES_READ]}
    )
    verb_entries = readIndex(wordnet_dir / 'index.verb')
    mind = sorted(entry.lemma for entry in verb_entries if verb_classes[entry.offsets[0]] in MIND_CLASSES)
    verbs = sorted(entry.lemma for entry in verb_entries)

    notice = (wordnet_dir / 'LICENSE').read_text(encoding='utf-8')
    words = {'source': 'WordNet 3.0', 'license': notice, 'animate_nouns': animate, 'mind_verbs': mind, 'verbs': verbs}
    words_json_path.write_text(json.dumps(words, indent=0) + '\n', encoding='utf-8')
    print(f'animate nouns: {len(animate)}, mind verbs: {len(mind)}')


def readSynsetClasses(data_path: Path, class_names: list[str]) -> dict[str, str]:
    """Map each synset offset in a WordNet data file to its lexicographer class, such as noun.person.

    Returns:
        Offset to class name.
    """
    classes: dict[str, str] = {}
    for line in data_path.read_text(encoding='utf-8').splitlines():
        if line.startswith(' '):
            continue
        offset, class_number = line.split(' ', 2)[:2]
        classes[offset] = class_names[int(class_number)].split()[1]
    return classes


def readIndex(index_path: Path) -> list[IndexEntry]:
    """Read a WordNet index file: each lemma with its synset offsets, most frequent sense first.

    Returns:
        One entry per single-word lemma. The check reads one token at a time, so a multi-word lemma
        never matches.
    """
    entries: list[IndexEntry] = []
    for line in index_path.read_text(encoding='utf-8').splitlines():
        if line.startswith(' '):
            continue
        fields = line.split()
        if '_' in fields[0]:
            continue
        pointer_count = int(fields[3])
        offsets = fields[4 + pointer_count + 2 :]
        entries.append(IndexEntry(fields[0], offsets))
    return entries


### vocabulary #########################################################################################


@dataclass(frozen=True)
class IndexEntry:
    lemma: str
    offsets: list[str]


main()
