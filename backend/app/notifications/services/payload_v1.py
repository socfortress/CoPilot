"""The versioned notification payload: `copilot.notification.v1` and its `ai_report` block.

Automation (a Shuffle workflow, any webhook receiver) needs an investigation's findings as
data, not as an email to parse. The webhook's structured payload already carried a few fields,
and `include_full_report` merged the report's extras into it **flat**; that shape is an external
contract and is left exactly as it was. What this module adds beside it:

- ``schema: "copilot.notification.v1"`` on the structured payload, so a receiver can tell which
  shape it is reading;
- a **nested** ``ai_report`` object when the route asks for the report, with typed fields,
  capped strings and a bounded size (``MAX_AI_REPORT_V1_BYTES``).

**Loaded at delivery time.** The outbox serializes an event and may replay it hours later; the
block is never stored on the event. It is read from the database when the route is delivered,
through ``ai_report_context.select_report``: the report the event names (``context.report_id``,
which an ``ai_report_reviewed`` event carries) or else the alert's newest, the one choice the flat
fields and ``context.ai_report`` make too. A replayed event therefore carries the report as it is
at delivery, the way the flat fields always have.

**Authorization.** A report is customer data. ``ai_report_v1_for_route`` is the only entry point
a channel or the renderer should use. ``report_permitted_for_route`` is the rule it applies, and
the one the flat fields, the ``{{report}}`` token and ``context.ai_report`` follow too: on a
customer-scope route the customer's AI report setting (``is_ai_reports_enabled``, the predicate
the portal and ``dispatch_event`` use) must be on, whatever the trigger, manual and test sends
included. Internal routes are the SOC's own and are not gated, as everywhere else. A manual send
with "Include the AI investigation report" unticked carries none of it on any route. The report
must belong to the event's customer and to the alert the event is about, or there is no block.

**Never stored, never raises from the safe wrapper**: a failure costs the route its block, not
the notification.

**v1 is append-only.** Fields may be added; none is removed, renamed or retyped. A breaking
change is ``copilot.notification.v2``. ``docs/user/notifications.md`` ("Payload v1") is the
receivers' reference: keep it in step with ``build_ai_report_v1``.
"""

from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import AiAnalystIoc
from app.db.universal_models import AiAnalystReview
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.notifications import NotificationScope
from app.notifications.schema.notifications import NotificationTrigger
from app.notifications.services.ai_report_context import MAX_IOCS
from app.notifications.services.ai_report_context import named_report_id
from app.notifications.services.ai_report_context import select_report

SCHEMA_V1 = "copilot.notification.v1"

#: The line a Shuffle input carries the v1 JSON on: this marker, one space, then compact,
#: ASCII-only JSON to the end of the line (every newline and non-ASCII character inside a string
#: is escaped, so the JSON is always one line). It is the last line of the input.
SHUFFLE_JSON_MARKER = "COPILOT_NOTIFICATION_V1_JSON:"

#: Appended to a string that was cut. Counted inside the cap.
TRUNCATION_MARK = "…"

MAX_SUMMARY_CHARS = 2000
MAX_RECOMMENDED_ACTIONS_CHARS = 4000
MAX_IOC_DETAILS_CHARS = 500
#: `ai_analyst_ioc.ioc_value` is VARCHAR(512); the cap only matters for a hand-edited row.
MAX_IOC_VALUE_CHARS = 512
#: Type, verdict, score and the severities: short labels, capped against odd data.
MAX_LABEL_CHARS = 64
MAX_ALERT_NAME_CHARS = 512
MAX_ASSET_NAME_CHARS = 255
MAX_JOB_ID_CHARS = 64
#: A deep link is short (``COPILOT_URL`` plus ``/alerts/<id>``); the cap keeps an odd one, Talon's
#: own ``report_url`` say, from eating the size bound.
MAX_URL_CHARS = 512

#: How far ``enforce_size`` shortens the summary and the recommended actions before it gives up
#: any indicator: below this, the texts stop being worth more than the IOCs.
TEXT_FLOOR_CHARS = 500

#: A review verdict meaning the reviewer rejected the report (thumbs down).
REJECTED_VERDICT = "down"

#: The block's bound, measured as ``json.dumps(block)`` with its defaults (ASCII escapes and
#: ", " / ": " separators), which is the largest form any sender here produces (the compact
#: ``ai_report_v1_json`` and httpx's body are never larger). A webhook payload without the legacy
#: flat report fields (which are unbounded and predate v1) stays well under 64 KB with this block
#: in it. ``enforce_size`` guarantees it whatever the data.
MAX_AI_REPORT_V1_BYTES = 32 * 1024

#: The fixed fields ``enforce_size`` empties, in this order, if the block is still over its bound
#: once the texts and the indicators have given all they can. Unreachable with the caps above (the
#: worst case is about 31 KB with every character a twelve-byte escape), kept so the bound holds
#: whatever the caps become.
_FALLBACK_FIELDS: Tuple[Tuple[str, ...], ...] = (
    ("report_url",),
    ("alert", "name"),
    ("alert", "asset_name"),
    ("job_id",),
    ("review_verdict",),
    ("severity",),
    ("alert", "source"),
    ("summary",),
    ("recommended_actions",),
)


def _cap(value: Any, limit: int) -> Tuple[Optional[str], bool]:
    """`(text, was_cut)`. None stays None; anything else becomes a string of at most `limit` characters."""
    if value is None:
        return (None, False)
    text = str(value)
    if len(text) <= limit:
        return (text, False)
    return (text[: max(0, limit - len(TRUNCATION_MARK))] + TRUNCATION_MARK, True)


def _iso_utc(value: Optional[datetime]) -> Optional[str]:
    """ISO 8601 in UTC with a `Z`. CoPilot stores naive UTC; an aware value is converted."""
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat() + "Z"


def serialized_size(block: Optional[Dict[str, Any]]) -> int:
    """The block's size in bytes as ``MAX_AI_REPORT_V1_BYTES`` measures it."""
    return len(json.dumps(block).encode("utf-8"))


def ai_report_v1_json(block: Optional[Dict[str, Any]]) -> str:
    """The block as compact, ASCII-only JSON (``null`` for none): ``context.ai_report_v1_json``.

    Templates should embed this rather than ``{{ context.ai_report_v1 | tojson }}``: Jinja's
    ``tojson`` HTML-escapes ``<``, ``>``, ``&`` and ``'`` into six-byte escapes, which can take a
    32 KB block past the 64 KB rendered-body limit. This form is never larger than the bound.
    """
    return json.dumps(block, separators=(",", ":"))


def _ioc_v1(ioc: Any) -> Dict[str, Any]:
    value, cut_value = _cap(ioc.ioc_value, MAX_IOC_VALUE_CHARS)
    ioc_type, cut_type = _cap(ioc.ioc_type, MAX_LABEL_CHARS)
    verdict, cut_verdict = _cap(ioc.vt_verdict, MAX_LABEL_CHARS)
    score, cut_score = _cap(ioc.vt_score or None, MAX_LABEL_CHARS)
    details, cut_details = _cap(ioc.details or None, MAX_IOC_DETAILS_CHARS)
    return {
        "value": value,
        "type": ioc_type,
        "verdict": verdict,
        "score": score,
        "details": details,
        "truncated": any((cut_value, cut_type, cut_verdict, cut_score, cut_details)),
    }


def build_ai_report_v1(
    *,
    report: Any,
    iocs: List[Any],
    job_id: Optional[str],
    alert: Any,
    asset_name: Optional[str],
    reviewed: bool,
    review_verdict: Optional[str],
    report_url: Optional[str],
    review_rejected: bool = False,
) -> Dict[str, Any]:
    """The block, from rows already loaded and checked. Pure: no I/O, so it is tested directly.

    Unscoped: ``project_for_scope`` removes what a customer route may not see.

    Null means "CoPilot has no value"; an empty list means "none". Each capped string ends in
    ``TRUNCATION_MARK`` and its field is named in ``truncated_fields`` (an IOC's own fields are
    flagged by that IOC's ``truncated``). ``ioc_count`` is the report's true total and
    ``iocs_truncated`` says the list holds fewer.

    ``reviewed``: an analyst has reviewed the report **without rejecting it** (a review whose
    verdict isn't thumbs-down; a review with no verdict counts). ``review_rejected``: some review
    rejected it. A report can be both, when reviewers disagree.
    """
    truncated: List[str] = []

    def capped(name: str, value: Any, limit: int) -> Optional[str]:
        text, cut = _cap(value, limit)
        if cut:
            truncated.append(name)
        return text

    block: Dict[str, Any] = {
        "report_id": report.id,
        "job_id": capped("job_id", job_id, MAX_JOB_ID_CHARS),
        "severity": capped("severity", report.severity_assessment or None, MAX_LABEL_CHARS),
        "summary": capped("summary", report.summary or None, MAX_SUMMARY_CHARS),
        "recommended_actions": capped("recommended_actions", report.recommended_actions or None, MAX_RECOMMENDED_ACTIONS_CHARS),
        "created_at": _iso_utc(report.created_at),
        "report_url": capped("report_url", report_url or None, MAX_URL_CHARS),
        "alert": {
            "id": report.alert_id,
            "name": capped("alert.name", getattr(alert, "alert_name", None) or None, MAX_ALERT_NAME_CHARS),
            "source": capped("alert.source", getattr(alert, "source", None) or None, MAX_LABEL_CHARS),
            "asset_name": capped("alert.asset_name", asset_name or None, MAX_ASSET_NAME_CHARS),
        },
        "iocs": [_ioc_v1(i) for i in iocs[:MAX_IOCS]],
        "ioc_count": len(iocs),
        "iocs_truncated": len(iocs) > MAX_IOCS,
        "reviewed": bool(reviewed),
        "review_rejected": bool(review_rejected),
        "review_verdict": capped("review_verdict", review_verdict or None, MAX_LABEL_CHARS),
        "truncated_fields": truncated,
    }
    return enforce_size(block)


def _mark(block: Dict[str, Any], name: str) -> None:
    if name not in block["truncated_fields"]:
        block["truncated_fields"].append(name)


def _shrink_texts(block: Dict[str, Any], limit: int, floor: int) -> None:
    """Shorten the summary and the recommended actions, longest first, no further than `floor`
    characters, until the block fits. Each is cut to the longest length that fits (a binary
    search on the serialized size, which grows with the length), so no more is cut than needed."""
    names = ("summary", "recommended_actions")
    while serialized_size(block) > limit:
        candidates = [n for n in names if len(block.get(n) or "") > floor]
        if not candidates:
            return
        name = max(candidates, key=lambda n: len(block[n]))
        original = block[name]
        low, high = floor, len(original) - 1
        best = None
        while low <= high:
            mid = (low + high) // 2
            block[name], _ = _cap(original, mid)
            if serialized_size(block) <= limit:
                best, low = mid, mid + 1
            else:
                high = mid - 1
        if best is not None:
            block[name], _ = _cap(original, best)
        elif floor > len(TRUNCATION_MARK):
            block[name], _ = _cap(original, floor)
        else:
            # Not even the mark fits: no text at all. Each pass shortens or removes a text, so the
            # loop ends.
            block[name] = None
        _mark(block, name)


def _fit_iocs(block: Dict[str, Any], iocs: List[Dict[str, Any]], limit: int) -> None:
    """Keep as many indicators as fit, in their order, skipping any that doesn't.

    Sized without re-serializing the block per indicator: a JSON list is ``[`` + items joined
    by ``", "`` + ``]``, so each kept indicator adds its own size plus two bytes after the first.
    """
    block["iocs"] = []
    total = serialized_size(block)
    kept: List[Dict[str, Any]] = []
    for ioc in iocs:
        extra = len(json.dumps(ioc).encode("utf-8")) + (2 if kept else 0)
        if total + extra <= limit:
            kept.append(ioc)
            total += extra
    block["iocs"] = kept
    if len(kept) < len(iocs):
        block["iocs_truncated"] = True


def enforce_size(block: Dict[str, Any], limit: int = MAX_AI_REPORT_V1_BYTES) -> Dict[str, Any]:
    """Bring the block under `limit` bytes, whatever the characters in it.

    The per-field caps count characters; escaping can make one character twelve bytes, so the
    bytes are checked here, in this order:

    1. the summary and the recommended actions are shortened, longest first, down to
       ``TEXT_FLOOR_CHARS``, keeping every indicator;
    2. then indicators are kept greedily, in order, as many as fit (``iocs_truncated``);
    3. then the texts go below the floor;
    4. then, as a last resort, the fixed fields in ``_FALLBACK_FIELDS`` become null.

    Every cut is named in ``truncated_fields``. The bound always holds on return.
    """
    if serialized_size(block) <= limit:
        return block

    iocs = list(block["iocs"])
    _shrink_texts(block, limit, TEXT_FLOOR_CHARS)
    if serialized_size(block) <= limit:
        return block

    _fit_iocs(block, iocs, limit)
    if serialized_size(block) > limit:
        _shrink_texts(block, limit, 0)

    for path in _FALLBACK_FIELDS:
        if serialized_size(block) <= limit:
            break
        target = block
        for key in path[:-1]:
            target = target[key]
        if target.get(path[-1]) is not None:
            target[path[-1]] = None
            _mark(block, ".".join(path))

    if serialized_size(block) > limit:
        # Only the structure is left; it is a few hundred bytes. Never send an over-size block.
        raise AssertionError(f"ai_report block is {serialized_size(block)} bytes after enforce_size, over {limit}")
    return block


async def _first_asset_name(alert_id: int, session: AsyncSession) -> Optional[str]:
    from app.incidents.models import Asset

    result = await session.execute(select(Asset.asset_name).where(Asset.alert_linked == alert_id).order_by(Asset.id).limit(1))
    return result.scalars().first()


async def load_ai_report_v1(event: NotificationEvent, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """The block for `event`, unscoped (``job_id`` included), or None. Reads; never writes.

    None when ``select_report`` finds nothing to carry (not an alert, no report, a named report
    that is gone or another alert's, another customer's report), or the alert and the report
    disagree on the customer.
    """
    from app.incidents.models import Alert

    alert_id = event.entity_id
    context = event.context or {}
    report = await select_report(
        alert_id,
        session,
        report_id=named_report_id(context),
        customer_code=event.customer_code,
        entity_type=event.entity_type,
    )
    if report is None:
        return None

    alert = await session.get(Alert, alert_id)
    if alert is not None and alert.customer_code != report.customer_code:
        logger.warning(f"Alert {alert_id} and AI report {report.id} belong to different customers; no ai_report block.")
        return None
    asset_name = await _first_asset_name(alert_id, session) if alert is not None else None

    ioc_result = await session.execute(
        select(AiAnalystIoc).where(AiAnalystIoc.report_id == report.id).order_by(AiAnalystIoc.id),
    )
    iocs = list(ioc_result.scalars().all())

    # Every review's verdict, as stored when the route is delivered. A review event's own review
    # is committed before its notification is delivered (the outbox row is queued in the review's
    # transaction and drained after it), so it is among them.
    verdict_result = await session.execute(select(AiAnalystReview.overall_verdict).where(AiAnalystReview.report_id == report.id))
    verdicts = list(verdict_result.scalars().all())

    is_review = event.trigger == NotificationTrigger.AI_REPORT_REVIEWED
    return build_ai_report_v1(
        report=report,
        iocs=iocs,
        job_id=report.job_id or None,
        alert=alert,
        asset_name=asset_name,
        reviewed=any(v != REJECTED_VERDICT for v in verdicts),
        review_rejected=any(v == REJECTED_VERDICT for v in verdicts),
        # The sign-off this event is about, as it travelled on the event: a later edit of the
        # review does not re-notify, so the event's verdict is the one being announced.
        review_verdict=context.get("verdict") if is_review else None,
        report_url=event.link_url,
    )


async def safe_load_ai_report_v1(event: NotificationEvent, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """`load_ai_report_v1`, degrading to None instead of raising."""
    try:
        return await load_ai_report_v1(event, session)
    except Exception as e:  # noqa: BLE001 — a report must never break a dispatch
        logger.warning(f"Could not load the v1 AI report for alert {event.entity_id}: {type(e).__name__}: {e}")
        return None


#: Fields a customer route gets as null: the SOC's own bookkeeping and quality ratings.
_INTERNAL_ONLY_FIELDS = ("job_id", "review_verdict", "review_rejected")


def project_for_scope(block: Optional[Dict[str, Any]], scope: str) -> Optional[Dict[str, Any]]:
    """What a route of `scope` may see. A copy: the memoized block is shared by every route.

    A customer route gets ``job_id``, ``review_verdict`` and ``review_rejected`` as null: the job
    id is internal bookkeeping, and a review's verdict is the SOC's quality rating of the AI, which
    the customer portal never shows either. The report's own fields (severity, summary, recommended
    actions, created_at, the IOCs) are what the portal shows the customer; the alert's id, name,
    source and asset are the customer's own alert; ``reviewed`` is the one addition, a yes/no that
    an analyst has checked the report without rejecting it.
    """
    if block is None:
        return None
    projected = json.loads(json.dumps(block))
    if scope != NotificationScope.INTERNAL.value:
        for name in _INTERNAL_ONLY_FIELDS:
            projected[name] = None
        projected["truncated_fields"] = [f for f in projected["truncated_fields"] if f not in _INTERNAL_ONLY_FIELDS]
    return projected


async def _customer_permitted(event: NotificationEvent, session: AsyncSession, ctx: Any = None) -> bool:
    from app.customer_portal.services.ai_reports import is_ai_reports_enabled

    code = event.customer_code
    if not code:
        return False

    async def check() -> bool:
        try:
            return await is_ai_reports_enabled(code, session)
        except Exception as e:  # noqa: BLE001 — fail closed
            logger.warning(f"Could not read the AI report switch for {code}: {type(e).__name__}: {e}")
            return False

    if ctx is None:
        return await check()
    return await ctx.memoize(f"ai_reports_enabled:{code}", check)


async def report_permitted_for_route(
    route_scope: Optional[str],
    event: NotificationEvent,
    session: AsyncSession,
    ctx: Any = None,
) -> bool:
    """Whether a route may receive any of the alert's AI report: the v1 block, the flat fields
    `include_full_report` merges, the `{{report}}` token and `context.ai_report`.

    The customer's AI report setting governs every customer route, on every trigger and on manual
    and test sends; `dispatch_event`'s own gate covers only the AI triggers. Internal routes are
    the SOC's own and always may, except on a manual send that left the report out
    (`event.exclude_ai_report`). `route_scope` missing reads as customer: fail closed. Memoized
    per customer on the dispatch context.
    """
    if event.exclude_ai_report:
        # A manual send with "Include the AI investigation report" unticked: no report on any
        # route, whatever the route's own `include_full_report`.
        return False
    scope = route_scope or NotificationScope.CUSTOMER.value
    if scope == NotificationScope.INTERNAL.value:
        return True
    return await _customer_permitted(event, session, ctx)


async def ai_report_v1_for_route(
    route_scope: Optional[str],
    event: NotificationEvent,
    session: AsyncSession,
    ctx: Any = None,
) -> Optional[Dict[str, Any]]:
    """The block one route may receive, or None. The only way a channel or template gets it.

    `route_scope` missing reads as customer: fail closed. The read is memoized on the dispatch
    context, so several routes on one event share it; the projection is per route.
    """
    scope = route_scope or NotificationScope.CUSTOMER.value
    if not await report_permitted_for_route(scope, event, session, ctx):
        return None

    async def load() -> Optional[Dict[str, Any]]:
        return await safe_load_ai_report_v1(event, session)

    key = f"ai_report_v1:{event.entity_type}:{event.entity_id}:{named_report_id(event.context)}"
    block = await ctx.memoize(key, load) if ctx is not None else await load()
    return project_for_scope(block, scope)


def v1_envelope(event: NotificationEvent, ai_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The v1 fields a text-only channel carries as JSON: the webhook's structured fields without
    ``text`` (the message itself is the rest of the input), and the block. The envelope's own
    strings are capped like the block's, so the whole JSON stays bounded."""
    alert_name, _ = _cap((event.context or {}).get("alert_name"), MAX_ALERT_NAME_CHARS)
    summary, _ = _cap(event.summary, MAX_SUMMARY_CHARS)
    report_url, _ = _cap(event.link_url, MAX_URL_CHARS)
    envelope = {
        "schema": SCHEMA_V1,
        "customer_code": event.customer_code,
        "alert_id": event.entity_id,
        "alert_name": alert_name,
        "severity": event.severity.value,
        "summary": summary,
        "report_url": report_url,
        "ai_report": ai_report,
    }
    if event.trigger == NotificationTrigger.TALON_OPS_FINDING:
        # A Talon ops finding's own block (``services/ops_finding_v1.py``), never an AI report.
        envelope["ai_report"] = None
        envelope["ops_finding"] = (event.context or {}).get("ops_finding")
    return envelope


def sample_ai_report_v1() -> Dict[str, Any]:
    """A synthetic block for the template editor's preview: the shape a real one has, built by
    the same code, with made-up values (documentation addresses only)."""
    from types import SimpleNamespace

    report = SimpleNamespace(
        id=912,
        alert_id=4821,
        severity_assessment="High",
        summary="An encoded PowerShell command was launched by winword.exe.",
        recommended_actions="1. Isolate WKSTN-014.\n2. Reset the user's password.\n3. Block 203.0.113.7 at the firewall.",
        created_at=datetime(2026, 10, 1, 12, 0, 0),
    )
    iocs = [
        SimpleNamespace(
            ioc_value="203.0.113.7",
            ioc_type="ip",
            vt_verdict="malicious",
            vt_score="12/90",
            details="Contacted by the decoded command over HTTPS.",
        ),
        SimpleNamespace(ioc_value="update-check.example.com", ioc_type="domain", vt_verdict="unknown", vt_score=None, details=None),
    ]
    block = build_ai_report_v1(
        report=report,
        iocs=iocs,
        job_id=None,
        alert=SimpleNamespace(alert_name="Suspicious PowerShell execution on WKSTN-014", source="wazuh"),
        asset_name="WKSTN-014",
        reviewed=False,
        review_verdict=None,
        report_url="https://copilot.example.com/alerts/4821",
    )
    return project_for_scope(block, NotificationScope.CUSTOMER.value)
