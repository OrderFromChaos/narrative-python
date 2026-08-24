"""Version comparison, with no third-party dependency.

The standard library has no public version parser, so this module implements
the part of PEP 440 that a minimum-version policy needs: a numeric release
tuple, plus an ordering for the ``dev`` / pre-release / release / ``post``
suffixes. Local version labels (``+abc``) are ignored during comparison, as
PEP 440 requires. Anything the regular expression does not accept raises
`InvalidVersion`, which the caller reports rather than guessing at.

The sort key holds one suffix rank, so a version that mixes two suffixes
(``1.0.post1.dev2``) sorts by the stronger one. Such versions are rare in a
lockfile, and the simplification never changes the order of two plain
releases.
"""

from __future__ import annotations

import re
from typing import Final

__all__ = ["InvalidVersion", "compare_versions", "is_below", "parse_version"]

_VERSION = re.compile(
    r"""
    ^\s*v?
    (?:(?P<epoch>\d+)!)?
    (?P<release>\d+(?:\.\d+)*)
    (?P<pre>[-_.]?(?P<pre_label>a|b|c|rc|alpha|beta|pre|preview)[-_.]?(?P<pre_number>\d+)?)?
    (?P<post>
        -(?P<post_bare>\d+)
        | [-_.]?(?:post|rev|r)[-_.]?(?P<post_number>\d+)?
    )?
    (?P<dev>[-_.]?dev[-_.]?(?P<dev_number>\d+)?)?
    (?:\+[a-z0-9]+(?:[-_.][a-z0-9]+)*)?
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Sort ranks for the suffix groups. A development release comes before the
# release itself, a pre-release also before it, and a post-release after it.
_DEV: Final = -2
_PRE: Final = -1
_FINAL: Final = 0
_POST: Final = 1

_PRE_ALIASES: Final[dict[str, str]] = {
    "alpha": "a",
    "beta": "b",
    "c": "rc",
    "pre": "rc",
    "preview": "rc",
}

SortKey = tuple[int, tuple[int, ...], int, str, int]


class InvalidVersion(ValueError):
    """A version string could not be read."""

    def __init__(self, version: str) -> None:
        super().__init__(f"cannot read version {version!r}")
        self.version = version


def parse_version(version: str) -> SortKey:
    """Turn a version string into a tuple that sorts correctly.

    Raises:
        InvalidVersion: The string is not a recognised version.
    """
    match = _VERSION.match(version)
    if match is None:
        raise InvalidVersion(version)

    epoch = int(match["epoch"] or 0)
    release = tuple(int(part) for part in match["release"].split("."))

    if match["pre"] is not None:
        label = match["pre_label"].lower()
        label = _PRE_ALIASES.get(label, label)
        return (epoch, release, _PRE, label, int(match["pre_number"] or 0))
    if match["post"] is not None:
        number = match["post_bare"] or match["post_number"] or 0
        return (epoch, release, _POST, "", int(number))
    if match["dev"] is not None:
        return (epoch, release, _DEV, "", int(match["dev_number"] or 0))
    return (epoch, release, _FINAL, "", 0)


def compare_versions(left: str, right: str) -> int:
    """Return -1, 0 or 1 as ``left`` sorts before, with, or after ``right``.

    Raises:
        InvalidVersion: Either string is not a recognised version.
    """
    left_key = parse_version(left)
    right_key = parse_version(right)
    padded_left = _padded(left_key, len(right_key[1]))
    padded_right = _padded(right_key, len(left_key[1]))
    if padded_left < padded_right:
        return -1
    if padded_left > padded_right:
        return 1
    return 0


def is_below(version: str, minimum: str) -> bool:
    """Report whether ``version`` is older than ``minimum``.

    Raises:
        InvalidVersion: Either string is not a recognised version.
    """
    return compare_versions(version, minimum) < 0


def _padded(key: SortKey, width: int) -> SortKey:
    """Pad the release tuple so that ``1.2`` and ``1.2.0`` compare as equal."""
    epoch, release, rank, label, number = key
    if len(release) >= width:
        return key
    return (epoch, release + (0,) * (width - len(release)), rank, label, number)
