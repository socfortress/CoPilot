"""Inspector registry.

Adding coverage for a new file family is one new module plus one ``@register``
decorator -- never an ``if/elif`` in the analysis service. This mirrors the
notification ``channels/`` registry, which is the established shape in this
codebase for "one file per pluggable thing".

Selection is deliberately ordered strongest-signal-first:

1. **magic prefix** — the sample's own leading bytes. Authoritative, and works
   even when libmagic is missing or reports something generic.
2. **content probe** — an inspector's own ``claims()``, for containers that can
   only be told apart by looking inside. An OOXML document is a zip, and MIME
   routing alone would send it to the archive inspector.
3. **MIME type** — what libmagic derived from content.
4. **extension** — consulted *only* when the content type is generic. Content
   always decides the container; the extension can only disambiguate between
   things that are all genuinely plain text, because libmagic cannot tell a
   PowerShell script from a CSV.

A file renamed to hide its type therefore still routes to the right inspector,
which is the behaviour the issue's test list pins down.
"""

from __future__ import annotations

import os
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from loguru import logger

from app.file_analysis.services.inspectors.base import Inspector

# Content types carrying no format information -- the only situation in which an
# extension is allowed a say.
GENERIC_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/x-script",
        "application/octet-stream",
        "application/x-empty",
        "inode/x-empty",
        "",
    },
)

_REGISTRY: Dict[str, Inspector] = {}


def register(cls: Type[Inspector]) -> Type[Inspector]:
    """Class decorator adding an inspector to the registry."""
    if cls.name in _REGISTRY:
        raise ValueError(f"Duplicate file analysis inspector name '{cls.name}'")
    _REGISTRY[cls.name] = cls()
    return cls


def all_inspectors() -> List[Inspector]:
    return list(_REGISTRY.values())


def get_inspector(name: str) -> Optional[Inspector]:
    return _REGISTRY.get(name)


def select_inspector(data: bytes, mime_type: str, file_name: str) -> Optional[Inspector]:
    """Pick the inspector for a sample, or ``None`` when nothing claims it.

    ``None`` is a normal outcome, not an error: the job still completes with
    identification, hashes and entropy, and its verdict is ``unknown`` rather
    than ``clean`` -- see ``scoring.verdict_for``.
    """
    head = data[:512] if data else b""
    mime = (mime_type or "").lower()

    for inspector in _REGISTRY.values():
        for prefix in inspector.magic_prefixes:
            if head.startswith(prefix):
                return inspector

    for inspector in _REGISTRY.values():
        try:
            if inspector.claims(data, mime, file_name):
                return inspector
        except Exception as exc:
            # A probe must never decide routing by crashing. Log and move on so
            # a malformed sample falls through to MIME and extension routing
            # rather than failing the whole job.
            logger.debug(f"file_analysis: {inspector.name} content probe raised on {file_name}: {exc}")

    for inspector in _REGISTRY.values():
        if mime in {m.lower() for m in inspector.mime_types}:
            return inspector

    if mime in GENERIC_MIME_TYPES:
        extension = os.path.splitext(file_name or "")[1].lower().lstrip(".")
        if extension:
            for inspector in _REGISTRY.values():
                if extension in {e.lower() for e in inspector.extensions}:
                    return inspector

    return None


# Imported for their side effect: each module registers itself on import, so the
# registry is populated by the time select_inspector is first called. Placed at
# the bottom because every inspector imports from this module's base.
from app.file_analysis.services.inspectors import archive  # noqa: E402,F401
from app.file_analysis.services.inspectors import binary  # noqa: E402,F401
from app.file_analysis.services.inspectors import office  # noqa: E402,F401
from app.file_analysis.services.inspectors import pdf  # noqa: E402,F401
from app.file_analysis.services.inspectors import script  # noqa: E402,F401
