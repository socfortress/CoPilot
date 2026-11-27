"""Index patterns as snapshots read them.

A pattern is a comma-separated list of parts, in OpenSearch's multi-target syntax:
``fortinet-*,palo_alto-*,wazuh-*,-wazuh-monitoring-*``.

- Whitespace around a part is ignored, and so is an empty part (``a-*,,b-*``, a trailing comma).
- A part starting with ``-`` excludes; every other part includes.
- ``*`` is the only wildcard, as in OpenSearch: ``.`` and every other character match only
  themselves.

An index is selected when it matches at least one inclusion and no exclusion, wherever the
exclusion stands in the list. OpenSearch reads the list left to right instead: an exclusion
removes only what the parts before it matched, and a later part can add an index back
(``app/siem/services/events.py:index_in_pattern`` follows that for Event Search). The two agree
whenever the exclusions come after the inclusions, which is how patterns are usually written.

A snapshot schedule resolves its pattern here, against the cluster's index names, and gives the
indexer the names it found: the indexer never reads the schedule's pattern itself.
"""

from typing import Iterable
from typing import List
from typing import NamedTuple
from typing import Optional

EXAMPLE_PATTERN = "wazuh-*,-wazuh-monitoring-*"
# index_snapshot_schedules.index_pattern is VARCHAR(255) (migration 8c419faae3e5): a longer pattern
# would fail at the database, or be cut short where MySQL isn't strict.
MAX_INDEX_PATTERN_LENGTH = 255


class IndexPattern(NamedTuple):
    """A pattern's parts, in the order written, exclusions without their ``-``."""

    inclusions: tuple[str, ...]
    exclusions: tuple[str, ...]


def parse_index_pattern(pattern: Optional[str]) -> IndexPattern:
    inclusions: List[str] = []
    exclusions: List[str] = []
    for raw in (pattern or "").split(","):
        part = raw.strip()
        if not part:
            continue
        if part.startswith("-"):
            excluded = part[1:].strip()
            # A bare "-" excludes nothing; index_pattern_problem refuses it when a pattern is saved.
            if excluded:
                exclusions.append(excluded)
        else:
            inclusions.append(part)
    return IndexPattern(tuple(inclusions), tuple(exclusions))


def glob_matches(name: str, part: str) -> bool:
    """Whether ``name`` matches ``part``: ``*`` is any run of characters, none included, and every
    other character matches only itself.

    No regex: the literal pieces between the stars are found in order, each at its first place
    after the one before, which matches whenever any placement does. Each piece is searched for
    once, so no pattern (``*a*a*a*a*a*b``) makes it backtrack the way a regex engine would.
    """
    pieces = part.split("*")
    if len(pieces) == 1:
        return name == part
    first, *middle, last = pieces
    start, end = len(first), len(name) - len(last)
    if end < start or not name.startswith(first) or not name.endswith(last):
        return False
    for piece in middle:
        found = name.find(piece, start, end)
        if found < 0:
            return False
        start = found + len(piece)
    return True


def _matches_any(name: str, parts: Iterable[str]) -> bool:
    return any(glob_matches(name, part) for part in parts)


def resolve_index_pattern(pattern: Optional[str], indices: Iterable[str]) -> List[str]:
    """The names in ``indices`` that ``pattern`` selects, in their original order."""
    parsed = parse_index_pattern(pattern)
    if not parsed.inclusions:
        return []
    return [name for name in indices if _matches_any(name, parsed.inclusions) and not _matches_any(name, parsed.exclusions)]


def expand_requested_indices(requested: Iterable[str], indices: Iterable[str]) -> List[str]:
    """A manual snapshot's index list, expanded so that its write indices can be left out.

    Each entry may itself be a comma list. A part with a wildcard expands to the matching names in
    ``indices``; a part without one is kept as written, matched or not (an alias, or a name the
    indexer resolves itself), as it always was. Exclusions apply to both, wherever they stand.
    """
    parsed = parse_index_pattern(",".join(requested))
    names = list(indices)
    expanded: List[str] = []
    seen = set()
    for part in parsed.inclusions:
        found = [name for name in names if glob_matches(name, part)] if "*" in part else [part]
        for name in found:
            if name not in seen and not _matches_any(name, parsed.exclusions):
                seen.add(name)
                expanded.append(name)
    return expanded


def index_pattern_problem(pattern: Optional[str]) -> Optional[str]:
    """Why ``pattern`` can't be a schedule's (it could never select an index, or can't be stored), or None."""
    if len(pattern or "") > MAX_INDEX_PATTERN_LENGTH:
        return f"The pattern is {len(pattern)} characters long; a schedule can store at most {MAX_INDEX_PATTERN_LENGTH}"
    parts = [part.strip() for part in (pattern or "").split(",")]
    if not any(parts):
        return f"Enter an index pattern, for example {EXAMPLE_PATTERN}"
    if "-" in parts:
        return "A '-' must be followed by the pattern to exclude, for example -wazuh-monitoring-*"
    if not parse_index_pattern(pattern).inclusions:
        return f"The pattern only excludes indices: add at least one part to include, for example {EXAMPLE_PATTERN}"
    return None


def checked_index_pattern(pattern: str) -> str:
    """``pattern`` unchanged, or a ValueError saying why it can never select an index (a 422)."""
    problem = index_pattern_problem(pattern)
    if problem:
        raise ValueError(problem)
    return pattern
