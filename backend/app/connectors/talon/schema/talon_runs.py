"""The run view's answer, ``GET /api/talon/v2/runs/{job_id}/timeline`` (talon-analyst SPEC §5.4, D51;
plan M5-9a step 5).

An allowlist, not a projection of Phoenix's span: these models are the *only* fields a timeline
can carry (``extra="forbid"``), each built from one named Phoenix field or attribute by
``services/talon_runs.py`` and checked there. Never a span's input or output, its messages, its
``status_message``, its events, ``talon.scrub_*`` or any attribute not named here: they hold
transcripts as tokens (FR-PHX-3), and a model-written value has no place in CoPilot's UI.
"""
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class TimelineSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span_id: str
    trace_id: str
    parent_id: Optional[str] = None
    kind: str
    name: str
    start_time: str
    end_time: str
    duration_ms: int
    status_code: str
    stage: Optional[str] = None
    role: Optional[str] = None
    model: Optional[str] = None
    tool: Optional[str] = None
    #: A reader's label for ``tool`` (``TOOL_LABELS``), when it has one.
    tool_label: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None


class RunTimeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    customer_code: str
    spans: List[TimelineSpan]
    #: More spans exist than were read: over 10 pages, over 1000 spans, a page with more than
    #: 100, or a page over the byte cap.
    truncated: bool
    #: Spans Phoenix returned that weren't this job's and customer's, didn't parse or repeated one
    #: already shown: never shown.
    dropped: int
    #: Why there is nothing to show, when that is known (``"no trace data"``).
    note: Optional[str] = None
