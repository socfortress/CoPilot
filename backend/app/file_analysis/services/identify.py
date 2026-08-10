"""Content-based identification: type, hashes, entropy.

**The declared extension is never trusted to decide what a file is.** libmagic
reads the content, and where the two disagree that disagreement is itself a
finding -- renaming a PE to ``invoice.pdf`` is a delivery technique, not a
filing error (#974 §A).

libmagic is already a backend dependency (``python-magic`` in requirements,
``libmagic1`` in the image), so this costs nothing new.
"""

from __future__ import annotations

import hashlib
import os
from typing import NamedTuple
from typing import Optional

from loguru import logger

from app.file_analysis.utils.entropy import HIGH_ENTROPY_THRESHOLD
from app.file_analysis.utils.entropy import is_natively_compressed
from app.file_analysis.utils.entropy import shannon_entropy

# The EICAR anti-malware test string. Present so an operator can prove the whole
# pipeline works end to end -- submission, analysis, verdict, Graylog -- without
# ever handling real malware.
EICAR_SIGNATURE = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class Identification(NamedTuple):
    magic_type: str
    mime_type: str
    md5: str
    sha1: str
    sha256: str
    size: int
    entropy: float


def identify(data: bytes) -> Identification:
    """Derive type, hashes and entropy from the bytes alone.

    Takes no filename by design: nothing here may be influenced by what the
    sample claims to be. Name-versus-content conflicts are handled separately
    by :func:`detect_extension_mismatch`, where the conflict is the finding.
    """
    magic_type, mime_type = _magic(data)

    return Identification(
        magic_type=magic_type,
        mime_type=mime_type,
        md5=hashlib.md5(data).hexdigest(),
        sha1=hashlib.sha1(data).hexdigest(),
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        entropy=round(shannon_entropy(data), 4),
    )


def _magic(data: bytes) -> tuple:
    """Return (description, mime) from libmagic, degrading rather than failing.

    A missing or broken libmagic must not take the module down: identification
    falls back to a generic type, the extension-based routing in the registry
    still works, and the job completes with a weaker result instead of an error.
    """
    try:
        import magic as libmagic
    except ImportError:  # pragma: no cover - libmagic1 ships in the image
        logger.warning("file_analysis: python-magic unavailable, falling back to generic identification")
        return ("unknown", "application/octet-stream")

    try:
        description = libmagic.from_buffer(data, mime=False) or "unknown"
        mime = libmagic.from_buffer(data, mime=True) or "application/octet-stream"
    except Exception as exc:
        logger.warning(f"file_analysis: libmagic failed: {exc}")
        return ("unknown", "application/octet-stream")

    return (str(description)[:512], str(mime)[:255])


def contains_eicar(data: bytes) -> bool:
    """True when the sample carries the EICAR test signature."""
    # Bounded scan: EICAR is a 68-byte string that by specification sits at the
    # start of the file, and scanning a 100 MB sample for it would be waste.
    return EICAR_SIGNATURE in data[:4096]


def high_entropy_for_type(entropy: float, mime_type: str) -> bool:
    """Whether entropy is high *given what the file claims to be*.

    A JPEG at 7.9 is a JPEG. A Word document at 7.9 is carrying something.
    """
    if is_natively_compressed(mime_type):
        return False
    return entropy >= HIGH_ENTROPY_THRESHOLD


def detect_extension_mismatch(data: bytes, mime_type: str, file_name: str) -> Optional[str]:
    """Report a conflict between what the name claims and what the bytes are.

    The content side is resolved with **no filename**, so the answer comes from
    the bytes alone and cannot be talked into agreeing by the name it is being
    checked against. The name then either belongs to that format or it does not.

    An earlier version also resolved the extension to an inspector and compared
    the two, which silently missed the case that matters most: a PDF delivered
    as ``invoice.txt`` raised nothing, because no inspector claims ``.txt`` and
    a missing second opinion read as agreement. Asking whether the extension is
    one the *identified format* actually uses has no such hole.

    Returns ``None`` when the two agree, when there is no extension, or when the
    content is too generic for any inspector to claim -- in that last case there
    is no format to contradict the name.
    """
    extension = os.path.splitext(file_name or "")[1].lower().lstrip(".")
    if not extension:
        return None

    from app.file_analysis.services.inspectors import select_inspector

    by_content = select_inspector(data, mime_type, "")
    if by_content is None:
        return None

    if extension in {e.lower() for e in by_content.extensions}:
        return None

    return f".{extension} does not match the identified content: {by_content.name} ({mime_type})"
