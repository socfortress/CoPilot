"""Multi-pass script deobfuscation.

**Everything in this module is string transformation.** Nothing here executes,
evaluates, interprets or spawns anything. That is the invariant that lets Tier 1
run on the CoPilot host itself (#974 §B), and it is deliberately enforced by
this module importing nothing beyond ``base64``, ``binascii``, ``codecs`` and
``re`` -- there is no interpreter, no ``eval``, and no subprocess to reach for.

The approach is fixpoint rewriting: apply every known transform to the text,
and if anything changed, go round again. Real-world obfuscation stacks layers
(base64 inside a char-code array inside a reversed string), and one pass only
ever peels the outermost.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import re
from typing import List
from typing import NamedTuple

# A pass count high enough for the layering seen in the wild, low enough that a
# pathological sample cannot spin here. Hitting the ceiling is reported rather
# than silently accepted -- a sample that is still changing after this many
# rounds is itself worth flagging.
MAX_PASSES = 12

# Per-layer output cap. Decoding can expand, and a chain of expansions is a
# cheap way to exhaust memory on the analysis host.
MAX_DECODED_LENGTH = 2_000_000

# Below this length a base64-looking run is almost always a false positive
# (a variable name, a hash fragment, a GUID chunk).
MIN_BASE64_RUN = 24

# Prefix marking a region this module rewrote. Every transform must be
# idempotent -- applying it to its own output must produce no further change --
# or the fixpoint loop below cannot terminate before MAX_PASSES.
DECODED_MARKER = "/* decoded: "

_BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{%d,}={0,2}" % MIN_BASE64_RUN)
_HEX_RUN = re.compile(r"(?:0x[0-9A-Fa-f]{2}[,\s]+){8,}0x[0-9A-Fa-f]{2}")
_HEX_STRING = re.compile(r"(?:%[0-9A-Fa-f]{2}){8,}")
# PowerShell / JScript char-code arrays: [char]72+[char]105, String.fromCharCode(72,105)
_CHAR_CODE_CALL = re.compile(r"(?:String\.)?fromCharCode\s*\(([\d,\s]+)\)", re.IGNORECASE)
# Two chained casts are already a deliberate split of a keyword; requiring a
# longer run misses the common three-cast form ([char]105+[char]101+[char]120).
_CHAR_CAST_RUN = re.compile(r"(?:\[char\]\s*\d{1,7}\s*(?:\+|,)\s*){1,}\[char\]\s*\d{1,7}", re.IGNORECASE)
_CHAR_CAST_ONE = re.compile(r"\[char\]\s*(\d{1,7})", re.IGNORECASE)
# PowerShell string concatenation used purely to split a keyword: 'inv'+'oke'
_CONCAT_LITERALS = re.compile(r"(['\"])([^'\"\r\n]{0,64})\1\s*\+\s*(['\"])([^'\"\r\n]{0,64})\3")
# -join with an explicit reverse is the common "read it backwards" trick
_REVERSED_LITERAL = re.compile(r"(['\"])([^'\"\r\n]{8,256})\1\s*\[\s*-1\s*\.\.\s*-?\d+\s*\]")
_ESCAPED_UNICODE = re.compile(r"(?:\\u[0-9A-Fa-f]{4}){4,}")
_ESCAPED_HEX = re.compile(r"(?:\\x[0-9A-Fa-f]{2}){4,}")
# PowerShell format-operator obfuscation: "{1}{0}" -f 'oke','inv'
_FORMAT_OPERATOR = re.compile(
    r"(['\"])((?:\{\d+\})+)\1\s*-f\s*((?:['\"][^'\"\r\n]{0,64}['\"]\s*,\s*)*['\"][^'\"\r\n]{0,64}['\"])",
    re.IGNORECASE,
)


class DeobfuscationResult(NamedTuple):
    """Outcome of deobfuscating one blob of script text.

    ``layers`` names the transforms that actually fired, in the order they did.
    It is the audit trail for the ``script.obfuscated`` finding: an analyst
    seeing "base64 -> char_codes -> concat" learns more from that chain than
    from the decoded text alone.
    """

    text: str
    layers: List[str]
    passes: int
    hit_pass_limit: bool

    @property
    def changed(self) -> bool:
        return bool(self.layers)


def _truncate(text: str) -> str:
    return text[:MAX_DECODED_LENGTH]


def _looks_like_text(data: bytes) -> bool:
    """Heuristic: did a decode produce something worth substituting in?

    Decoding a random base64-looking run usually yields bytes that are not text
    at all. Substituting that back into the script buries the real content in
    noise, so a decode only counts when the result reads as text.
    """
    if not data:
        return False

    # Both encodings are tried and the better one wins rather than short-circuiting
    # on the first that does not raise. UTF-16LE text decodes *successfully* as
    # UTF-8 -- the interleaved NUL bytes are valid UTF-8 -- so a first-match rule
    # scores PowerShell's -EncodedCommand payload at ~50% printable and rejects
    # the single most common encoded payload shape on Windows samples.
    best = 0.0
    for encoding in ("utf-8", "utf-16-le"):
        try:
            decoded = data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        if not decoded:
            continue
        printable = sum(1 for ch in decoded if ch.isprintable() or ch in "\r\n\t")
        best = max(best, printable / len(decoded))

    return best >= 0.85


def _decode_bytes(data: bytes) -> str:
    """Decode already-validated bytes to text, preferring UTF-16LE when it fits.

    PowerShell's ``-EncodedCommand`` is UTF-16LE, which is the single most
    common encoded-payload shape on Windows samples.
    """
    # Mirrors the encoding choice _looks_like_text made: NUL-heavy output means
    # the bytes were UTF-16LE that merely happened to satisfy the UTF-8 decoder.
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-16-le", errors="replace")

    if decoded.count("\x00") * 2 >= len(decoded):
        try:
            return data.decode("utf-16-le")
        except UnicodeDecodeError:
            return decoded
    return decoded


def _expand_base64(text: str) -> str:
    def repl(match: re.Match) -> str:
        candidate = match.group(0)
        # Strip to a length base64 can actually represent; obfuscators pad
        # sloppily and strict decoding would reject the whole run.
        trimmed = candidate.rstrip("=")
        usable = trimmed[: len(trimmed) - (len(trimmed) % 4)] if len(trimmed) % 4 else trimmed
        if len(usable) < MIN_BASE64_RUN:
            return candidate
        try:
            raw = base64.b64decode(usable + "=" * (-len(usable) % 4), validate=True)
        except (binascii.Error, ValueError):
            return candidate
        if not _looks_like_text(raw):
            return candidate

        # The encoded run is *replaced*, not annotated. Appending the decoded
        # text while leaving the original in place makes this transform
        # non-idempotent: the run still matches on the next pass, decodes again,
        # and appends again. The fixpoint loop then never converges -- every
        # script containing base64 ran the full MAX_PASSES, grew its buffer on
        # each one, and came back falsely flagged script.deep_obfuscation.
        #
        # Nothing is lost by replacing: the original bytes are in MinIO, and the
        # marker keeps the layer visible in the recovered text.
        return f"{DECODED_MARKER}base64 */ {_decode_bytes(raw)}"

    return _BASE64_RUN.sub(repl, text)


def _expand_char_codes(text: str) -> str:
    def repl_call(match: re.Match) -> str:
        codes = [c.strip() for c in match.group(1).split(",") if c.strip()]
        try:
            decoded = "".join(chr(int(c)) for c in codes if 0 <= int(c) <= 0x10FFFF)
        except ValueError:
            return match.group(0)
        return f'"{decoded}"'

    def repl_cast(match: re.Match) -> str:
        codes = _CHAR_CAST_ONE.findall(match.group(0))
        try:
            decoded = "".join(chr(int(c)) for c in codes if 0 <= int(c) <= 0x10FFFF)
        except ValueError:
            return match.group(0)
        return f'"{decoded}"'

    text = _CHAR_CODE_CALL.sub(repl_call, text)
    return _CHAR_CAST_RUN.sub(repl_cast, text)


def _expand_hex_arrays(text: str) -> str:
    def repl(match: re.Match) -> str:
        codes = re.findall(r"0x([0-9A-Fa-f]{2})", match.group(0))
        try:
            raw = bytes(int(c, 16) for c in codes)
        except ValueError:
            return match.group(0)
        if not _looks_like_text(raw):
            return match.group(0)
        return f'"{_decode_bytes(raw)}"'

    return _HEX_RUN.sub(repl, text)


def _expand_percent_encoding(text: str) -> str:
    def repl(match: re.Match) -> str:
        codes = re.findall(r"%([0-9A-Fa-f]{2})", match.group(0))
        try:
            raw = bytes(int(c, 16) for c in codes)
        except ValueError:
            return match.group(0)
        if not _looks_like_text(raw):
            return match.group(0)
        return _decode_bytes(raw)

    return _HEX_STRING.sub(repl, text)


def _expand_escapes(text: str) -> str:
    def repl(match: re.Match) -> str:
        try:
            return codecs.decode(match.group(0), "unicode_escape")
        except (UnicodeDecodeError, ValueError):
            return match.group(0)

    text = _ESCAPED_UNICODE.sub(repl, text)
    return _ESCAPED_HEX.sub(repl, text)


def _join_concatenations(text: str) -> str:
    # One rewrite per pass: 'a'+'b'+'c' collapses over successive passes rather
    # than needing a greedier pattern that would swallow unrelated operators.
    return _CONCAT_LITERALS.sub(lambda m: f'"{m.group(2)}{m.group(4)}"', text)


def _resolve_reversals(text: str) -> str:
    return _REVERSED_LITERAL.sub(lambda m: f'"{m.group(2)[::-1]}"', text)


def _resolve_format_operator(text: str) -> str:
    def repl(match: re.Match) -> str:
        order = [int(i) for i in re.findall(r"\{(\d+)\}", match.group(2))]
        parts = re.findall(r"['\"]([^'\"\r\n]{0,64})['\"]", match.group(3))
        if any(i >= len(parts) for i in order):
            return match.group(0)
        return '"' + "".join(parts[i] for i in order) + '"'

    return _FORMAT_OPERATOR.sub(repl, text)


# Ordered because the cheap structural transforms (concat, reverse, format)
# frequently reveal the base64 run that the expensive one then decodes.
_TRANSFORMS = (
    ("concat", _join_concatenations),
    ("format_operator", _resolve_format_operator),
    ("reverse", _resolve_reversals),
    ("escapes", _expand_escapes),
    ("char_codes", _expand_char_codes),
    ("hex_array", _expand_hex_arrays),
    ("percent_encoding", _expand_percent_encoding),
    ("base64", _expand_base64),
)


def deobfuscate(text: str) -> DeobfuscationResult:
    """Peel obfuscation layers off ``text`` until it stops changing.

    Returns the rewritten text with decoded content appended inline, the list of
    transforms that fired, and whether the pass ceiling was reached.
    """
    if not text:
        return DeobfuscationResult(text="", layers=[], passes=0, hit_pass_limit=False)

    current = _truncate(text)
    layers: List[str] = []
    passes = 0

    for _ in range(MAX_PASSES):
        passes += 1
        before = current
        for name, transform in _TRANSFORMS:
            rewritten = _truncate(transform(current))
            if rewritten != current:
                current = rewritten
                if name not in layers:
                    layers.append(name)
        if current == before:
            return DeobfuscationResult(text=current, layers=layers, passes=passes, hit_pass_limit=False)

    return DeobfuscationResult(text=current, layers=layers, passes=passes, hit_pass_limit=True)
