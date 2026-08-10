"""Shannon entropy over raw bytes.

Lives on its own, stdlib-only, because both identification and the binary
inspector need it and neither should have to import the other.

Entropy is a weak signal used only in combination: a value near 8.0 means the
bytes are incompressible, which is true of encrypted and packed content *and* of
every JPEG, ZIP and MP4. It earns a flag only where the container is not
natively compressed.
"""

from __future__ import annotations

import math
from collections import Counter

# Above this, a byte run carries essentially no structure.
HIGH_ENTROPY_THRESHOLD = 7.2

# Formats that are compressed by definition, where high entropy is the expected
# state and says nothing about the sample.
NATIVELY_COMPRESSED_MIME_PREFIXES = (
    "image/",
    "video/",
    "audio/",
    "application/zip",
    "application/x-7z",
    "application/x-rar",
    "application/gzip",
    "application/x-bzip",
    "application/x-xz",
    "application/x-tar",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument",
)


def shannon_entropy(data: bytes) -> float:
    """Entropy in bits per byte, 0.0 to 8.0. Empty input is 0.0."""
    if not data:
        return 0.0

    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def is_natively_compressed(mime_type: str) -> bool:
    mime = (mime_type or "").lower()
    return any(mime.startswith(prefix) for prefix in NATIVELY_COMPRESSED_MIME_PREFIXES)
