"""Watch a Talon v2 chat stream for approval cards, without touching it (plan M5-11a, "the mirror").

The chat proxy forwards talon-analyst's stream byte for byte (``V2StreamingResponse``). To mirror
a proposal as soon as its card appears, ``ApprovalTappedStream`` hands every forwarded chunk to an
``ApprovalScanner`` and yields the chunk itself, unchanged, whatever the scanner makes of it. When
the stream ends, however it ends (finished, cut off upstream, or the browser leaving), it calls
``on_end`` once with the ``approvalId`` of each ``tool-approval-request`` chunk it saw.

The ids are only a hint of *which* records to read: the mirror is filled from talon-analyst's
``GET /v2/actions/{id}`` alone (``services/talon_action_sync.py``), never from this stream, its
``tool-input-available`` arguments or the model's text. A card the scanner misses (a line it
couldn't parse, a stream cut short) is mirrored when the browser's card reads
``GET /api/talon/actions/{id}``.

The scanner never raises into the stream: a failure only stops it watching.
"""
import json
import re
from typing import Any
from typing import AsyncIterator
from typing import Callable
from typing import List
from typing import Optional
from typing import Sequence

from loguru import logger

#: The Vercel AI chunk type of an approval card (talon-analyst ``talon.api.vercel``).
APPROVAL_CHUNK = "tool-approval-request"
#: A record id as talon-analyst writes it (a lowercase UUID).
APPROVAL_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
#: The longest line or event the scanner reads. An approval chunk is about 120 bytes; a longer
#: line (a large tool input) is skipped, not buffered without bound.
MAX_LINE_BYTES = 64 * 1024
#: talon-analyst sends at most 3 proposals a turn; more than this is not a real turn.
MAX_IDS = 16


class ApprovalScanner:
    """An incremental SSE reader that keeps only the ``approvalId`` of approval chunks.

    Lines end with LF, CRLF or a lone CR; ``data:`` lines are joined per event; an event ends at a
    blank line (and, at ``close``, at the end of the stream). Comments and other fields are ignored.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._data: List[bytes] = []
        self._data_size = 0
        self._skip_line = False  # inside a line longer than MAX_LINE_BYTES
        self._skip_event = False  # an event with such a line: its data is incomplete
        self.approval_ids: List[str] = []

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk
        while True:
            line = self._next_line()
            if line is None:
                break
            self._line(line)
        if len(self._buffer) > MAX_LINE_BYTES:
            self._buffer.clear()
            self._skip_line = True
            self._skip_event = True

    def close(self) -> None:
        """The stream ended: a last line without its end, and a last event without its blank line."""
        if self._buffer and not self._skip_line:
            self._line(bytes(self._buffer))
        self._buffer.clear()
        self._dispatch()

    def _next_line(self) -> Optional[bytes]:
        lf = self._buffer.find(b"\n")
        cr = self._buffer.find(b"\r")
        if lf < 0 and cr < 0:
            return None
        if cr >= 0 and (lf < 0 or cr < lf):
            if cr == len(self._buffer) - 1:
                return None  # maybe CRLF split across chunks: wait for the next byte
            end, skip = cr, 2 if self._buffer[cr + 1 : cr + 2] == b"\n" else 1
        else:
            end, skip = lf, 1
        line = bytes(self._buffer[:end])
        del self._buffer[: end + skip]
        if self._skip_line:  # the end of an over-long line: drop it
            self._skip_line = False
            return b"\x00"  # never a field name: ignored by _line, keeps the event marked skipped
        return line

    def _line(self, line: bytes) -> None:
        if not line:
            self._dispatch()
            return
        if line.startswith(b":"):
            return
        name, _, value = line.partition(b":")
        if name != b"data":
            return
        if value.startswith(b" "):
            value = value[1:]
        self._data_size += len(value) + 1
        if self._data_size > MAX_LINE_BYTES:
            self._skip_event = True
            return
        self._data.append(value)

    def _dispatch(self) -> None:
        data, skipped = self._data, self._skip_event
        self._data, self._data_size, self._skip_event = [], 0, False
        if skipped or not data:
            return
        payload = b"\n".join(data)
        if APPROVAL_CHUNK.encode() not in payload:
            return
        try:
            event = json.loads(payload.decode("utf-8"))
        except ValueError:
            return
        if not isinstance(event, dict) or event.get("type") != APPROVAL_CHUNK:
            return
        approval_id = event.get("approvalId")
        if isinstance(approval_id, str) and APPROVAL_ID.fullmatch(approval_id) and approval_id not in self.approval_ids:
            if len(self.approval_ids) < MAX_IDS:
                self.approval_ids.append(approval_id)


class ApprovalTappedStream:
    """A ``V2Stream`` whose bytes pass through unchanged while ``ApprovalScanner`` reads them.

    Same interface as ``v2_client.V2Stream`` (``chunks()``, ``aclose()``), so ``V2StreamingResponse``
    takes it as is. ``on_end(ids)`` is called once, when the stream ends however it ends, before the
    upstream is closed; it must not block (it schedules the mirror's sync) and never raises into the
    stream.
    """

    def __init__(self, stream: Any, on_end: Callable[[Sequence[str]], None]) -> None:
        self._stream = stream
        self._on_end = on_end
        self._scanner: Optional[ApprovalScanner] = ApprovalScanner()
        self._ended = False

    @property
    def closed(self) -> bool:
        return bool(getattr(self._stream, "closed", False))

    async def chunks(self) -> AsyncIterator[bytes]:
        try:
            async for chunk in self._stream.chunks():
                self._observe(chunk)
                yield chunk
        finally:
            await self.aclose()

    def _observe(self, chunk: bytes) -> None:
        if self._scanner is None:
            return
        try:
            self._scanner.feed(chunk)
        except Exception as e:  # noqa: BLE001 - watching must never break the stream
            logger.error(f"Talon v2: the approval tap stopped: {type(e).__name__}")
            self._scanner = None

    def _end(self) -> None:
        if self._ended:
            return
        self._ended = True
        scanner, self._scanner = self._scanner, None
        if scanner is None:
            return
        try:
            scanner.close()
            if scanner.approval_ids:
                self._on_end(list(scanner.approval_ids))
        except Exception as e:  # noqa: BLE001 - the card's own GET mirrors it anyway
            logger.error(f"Talon v2: the approval tap could not hand its cards on: {type(e).__name__}")

    async def aclose(self) -> None:
        self._end()
        await self._stream.aclose()
