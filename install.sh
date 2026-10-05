#!/usr/bin/env bash
# Install the narrative skill into a Claude Code skills directory.
#
# Usage:
#     $ ./install.sh
#     $ ./install.sh ~/.config/claude/skills/narrative
#
# This file is the list of what the skill contains. A file in the destination that this list does
# not name is removed, because a file left by an earlier version keeps rules the skill has withdrawn.
# The prune removes regular files only, and refuses a destination that holds no SKILL.md.
#
# It also writes INSTALLED: the commit installed from, and when. verify.py prints it first, so a
# stale install shows in every run.

set -euo pipefail

FILES=(
    SKILL.md
    architecture.md
    tooling.md
    checks.py
    verify.py
    agentverbs.py
    words.json
    requirements-lock.txt
    pyproject-snippet.toml
)

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source_dir="$repo_dir/skill"
destination="${1:-$HOME/.claude/skills/narrative}"

for name in "${FILES[@]}"; do
    if [[ ! -f "$source_dir/$name" ]]; then
        echo "install.sh: $source_dir/$name is missing" >&2
        exit 2
    fi
done

# The prune deletes from the destination, so a directory that is not an install of this skill and is
# not empty is refused rather than pruned.
if [[ -d "$destination" && ! -f "$destination/SKILL.md" ]]; then
    if [[ -n "$(ls -A "$destination")" ]]; then
        echo "install.sh: $destination holds files and no SKILL.md, so it is not an install" >&2
        exit 2
    fi
fi

mkdir -p "$destination"

for name in "${FILES[@]}"; do
    cp "$source_dir/$name" "$destination/$name"
done

version="$(git -C "$repo_dir" rev-parse --short HEAD 2>/dev/null || echo 'unknown commit')"
if [[ -n "$(git -C "$repo_dir" status --porcelain -- skill 2>/dev/null || true)" ]]; then
    version+=' with uncommitted changes'
fi
printf '%s, installed %s\n' "$version" "$(date -u +%Y-%m-%dT%H:%MZ)" > "$destination/INSTALLED"

shopt -s nullglob dotglob
for path in "$destination"/*; do
    name="$(basename "$path")"
    for kept in "${FILES[@]}" INSTALLED; do
        if [[ "$name" == "$kept" ]]; then
            continue 2
        fi
    done
    if [[ -d "$path" ]]; then
        echo "left directory $name in place; remove it by hand"
        continue
    fi
    rm -f -- "$path"
    echo "removed $name"
done
shopt -u nullglob dotglob

echo "installed ${#FILES[@]} files to $destination: $(cat "$destination/INSTALLED")"
