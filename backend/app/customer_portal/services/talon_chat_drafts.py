"""Filing a Talon portal chat draft as a question to the SOC (talon-analyst SPEC D97 (o), (aa), (bb);
§5.3 "Portal chat: CoPilot's side" the submit route; §8 FR-API-39 to -41; plan PC-3).

Talon's ``ask_the_soc`` tool only drafts a question; it files nothing. The customer edits the draft
in the portal, picks the urgency and (for an alert) where it goes, and submits it here. CoPilot then:

0. **A lookup-only pass, before the switch**: a request this user already filed from this draft,
   with its comment, is reported ``submitted`` even while the chat is off (it records a filing
   that happened; nothing new is filed).
1. **Reads the draft back** as the user (FR-API-39): its customer (the user's, with the chat on)
   and its target come from talon-analyst's record, never from the body.
2. **Looks first, on every path**: a ``customer_portal_soc_request`` with this ``talon_draft_id``
   and its comment means the draft was filed already, so it is reported ``submitted`` with that
   request's id and nothing is filed. CoPilot's own refusal rules (the cooldown, the daily limit)
   never run for a filed draft, so they can't mislabel it. A row with the id, no comment and older
   than ``ORPHAN_AFTER`` is an **orphan** (the filing died between the reservation and the comment):
   it is deleted and the draft filed again; a case created by that filing stays linked to the alert
   and is reused. A younger such row is another request filing it: ``draft_conflict``.
3. **Claims** the draft (FR-API-40, ``pending → submitting``), then looks again.
4. **Files only on ``claimed: true``**, through the portal's own ``soc_requests`` service, as the
   customer: its switch, daily limit, cooldown, ``READ_ONLY`` and ``clean_question`` apply to the
   customer's edited question, with ``talon_draft_id`` set in ``_reserve``'s first insert (unique,
   so a second filing is impossible; a conflict there means another request filed it: that row
   is reported once its comment is written, else ``draft_conflict`` with no outcome). The target
   must belong to the draft's customer (a user of two customers can't move a draft to the other's
   alert or case): otherwise ``not_found``. An alert draft with ``file_on: "case"`` (the default) goes on the alert's open case
   or a new case from the alert, ``"alert"`` on the alert itself; a case draft on the case.
5. **Posts the outcome** (FR-API-41): ``submitted`` with the request's id, or ``failed`` with the
   refusal's code, retried a few times. A lost outcome strands nothing: the next submit finds the
   request in step 2 and reports it.
"""
import asyncio
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union

from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import User
from app.auth.services.read_only import is_read_only_for
from app.connectors.talon.services.identity import CUSTOMERS_HEADER
from app.connectors.talon.services.identity import PortalIdentityRefused
from app.connectors.talon.services.identity import portal_identity_headers
from app.connectors.talon.utils.portal_errors import NO_STORE
from app.connectors.talon.utils.portal_errors import coded
from app.connectors.talon.utils.v2_client import v2_request
from app.customer_portal.schema.soc_requests import AskOnAlertRequest
from app.customer_portal.schema.soc_requests import AskOnCaseRequest
from app.customer_portal.schema.soc_requests import clean_question
from app.customer_portal.schema.talon_chat import DraftSubmit
from app.customer_portal.services import soc_requests
from app.customer_portal.services.talon_chat_proxy import Portal
from app.customer_portal.services.talon_chat_proxy import answer
from app.customer_portal.services.talon_chat_proxy import begin
from app.customer_portal.services.talon_chat_proxy import object_id
from app.customer_portal.services.talon_chat_proxy import parsed
from app.customer_portal.services.talon_chat_proxy import read_body
from app.customer_portal.services.talon_chat_proxy import read_draft
from app.db.universal_models import CustomerPortalSocRequest
from app.incidents.models import Alert
from app.incidents.models import Case
from app.time_utils import now_utc

#: A reservation with a draft id and no comment this old is an orphan (SPEC §5.3).
ORPHAN_AFTER = timedelta(minutes=5)
#: Outcome posts: attempts and the pause between them.
OUTCOME_ATTEMPTS = 3
OUTCOME_PAUSE_SECONDS = 0.5
#: The failures FR-API-41 accepts.
FAILURE_CODES = frozenset(
    {"soc_requests_off", "soc_request_limit", "soc_request_cooldown", "read_only", "invalid_question", "not_found", "internal_failure"},
)


def _now():
    return now_utc().replace(tzinfo=None)


def submitted(request_id: int) -> JSONResponse:
    return JSONResponse({"request_id": request_id}, status_code=200, headers=NO_STORE)


# ── looking first ─────────────────────────────────────────────────────────────


#: ``look``'s answer for a draft another request is filing now (or a row that isn't this customer's).
IN_PROGRESS = "in_progress"


async def look(draft_id: str, customer_code: str, session: AsyncSession) -> Union[int, str, None]:
    """The request this draft was filed as (its id), ``IN_PROGRESS`` when another request is
    filing it now, or None (nothing, or an orphan just deleted).

    The orphan delete is conditional (no comment, older than ``ORPHAN_AFTER``, in the statement
    itself): a filing that wrote its comment in between keeps its row, and is looked at again."""
    for _ in range(3):
        await session.commit()  # a fresh snapshot: another request may have filed it meanwhile
        row = (
            (await session.execute(select(CustomerPortalSocRequest).where(CustomerPortalSocRequest.talon_draft_id == draft_id)))
            .scalars()
            .first()
        )
        if row is None:
            return None
        if row.customer_code != customer_code:
            # A draft id is a UUID talon-analyst made for one customer's thread: never another's request.
            logger.error(f"Talon draft {draft_id}: a SOC request of another customer holds its id; not reported")
            return IN_PROGRESS
        if row.comment_id is not None:
            return row.id
        cutoff = _now() - ORPHAN_AFTER
        if row.requested_at is None or row.requested_at > cutoff:
            return IN_PROGRESS
        deleted = await session.execute(
            delete(CustomerPortalSocRequest).where(
                CustomerPortalSocRequest.id == row.id,
                CustomerPortalSocRequest.comment_id.is_(None),
                CustomerPortalSocRequest.requested_at < cutoff,
            ),
        )
        await session.commit()
        if deleted.rowcount:
            logger.warning(f"Talon draft {draft_id}: deleted orphaned SOC request {row.id} (no comment after {ORPHAN_AFTER})")
            return None
        # rowcount 0: the row changed in between (its comment was written, or it is gone): look again.
    return IN_PROGRESS


async def filed_row(draft_id: str, session: AsyncSession) -> Optional[CustomerPortalSocRequest]:
    await session.commit()
    return (
        (await session.execute(select(CustomerPortalSocRequest).where(CustomerPortalSocRequest.talon_draft_id == draft_id)))
        .scalars()
        .first()
    )


# ── the outcome ───────────────────────────────────────────────────────────────


async def post_outcome(portal: Portal, draft_id: str, payload: Dict[str, Any]) -> bool:
    """FR-API-41, as the user. Retried on no answer or a 5xx; a refusal is final (logged)."""
    for attempt in range(OUTCOME_ATTEMPTS):
        result = await v2_request("POST", f"/v2/portal/drafts/{draft_id}/outcome", portal.identity, json_body=payload)
        if result.status is not None and 200 <= result.status < 300:
            return True
        if result.status is not None and 400 <= result.status < 500:
            logger.error(f"Talon draft {draft_id}: talon-analyst refused the outcome {payload.get('outcome')} ({result.status})")
            return False
        if attempt + 1 < OUTCOME_ATTEMPTS:
            await asyncio.sleep(OUTCOME_PAUSE_SECONDS)
    logger.error(f"Talon draft {draft_id}: the outcome {payload.get('outcome')} could not be posted; the next submit reports it")
    return False


async def report_submitted(portal: Portal, draft_id: str, request_id: int) -> JSONResponse:
    await post_outcome(portal, draft_id, {"outcome": "submitted", "copilot_ref": str(request_id)})
    return submitted(request_id)


async def report_failed(portal: Portal, draft_id: str, code: str) -> JSONResponse:
    await post_outcome(portal, draft_id, {"outcome": "failed", "failure": code})
    return coded(code)


# ── filing ────────────────────────────────────────────────────────────────────


def _failure_code(error: HTTPException) -> str:
    code = getattr(error, "code", None)
    if code in FAILURE_CODES:
        return code
    if error.status_code in (403, 404):  # the alert or case is gone, or no longer the user's
        return "not_found"
    return "internal_failure"


async def target_customer(kind: Any, target_id: int, session: AsyncSession) -> Optional[str]:
    """The ``customer_code`` of the draft's alert or case, or None."""
    model = Alert if kind == "alert" else Case if kind == "case" else None
    if model is None:
        return None
    return (await session.execute(select(model.customer_code).where(model.id == target_id))).scalar_one_or_none()


async def file(
    draft_id: str,
    customer_code: str,
    target: Dict[str, Any],
    body: DraftSubmit,
    user: User,
    session: AsyncSession,
) -> Union[int, str]:
    """File the claimed draft as the customer: the request's id, or a failure code
    (``draft_conflict``: another request holds the draft id and hasn't finished; no outcome)."""
    kind, target_id = target.get("kind"), target.get("id")
    if isinstance(target_id, bool) or not isinstance(target_id, int) or target_id < 1:
        return "not_found"
    # The target must be the draft's own customer's, not only one the user may see: a user of two
    # customers must never have an ACME draft filed on a GLOBEX alert (review of #1327, M1).
    if await target_customer(kind, target_id, session) != customer_code:
        return "not_found"
    try:
        if kind == "alert":
            ask = AskOnAlertRequest(question=body.question, urgency=body.urgency, target=body.file_on or "case")
            filed = await soc_requests.ask_on_alert(target_id, ask, user, session, talon_draft_id=draft_id)
        else:
            ask = AskOnCaseRequest(question=body.question, urgency=body.urgency)
            filed = await soc_requests.ask_on_case(target_id, ask, user, session, talon_draft_id=draft_id)
    except ValidationError:
        return "invalid_question"
    except soc_requests.DraftAlreadyFiled:
        # Another request filed it between the look and the insert: report it only once its comment
        # is written; until then it is that request's to report.
        existing = await filed_row(draft_id, session)
        if existing is not None and existing.customer_code == customer_code and existing.comment_id is not None:
            return existing.id
        return "draft_conflict"
    except HTTPException as e:
        await session.rollback()
        return _failure_code(e)
    except Exception:  # noqa: BLE001 - the SOC's plumbing never reaches the customer
        logger.exception(f"Talon draft {draft_id}: filing failed")
        await session.rollback()
        return "internal_failure"
    return filed.id


async def already_filed(user: User, session: AsyncSession, draft_id: str) -> Union[JSONResponse, Dict[str, str], None]:
    """The lookup-only pass, before the switch (review of #1327, L3): a request this user filed from
    this draft, with its comment, on one of their customers, is reported ``submitted`` even while
    the chat is off. It records a filing that already happened and files nothing; talon-analyst's
    outcome route is exempt from the switch for the same reason. Returns the answer, the identity
    for the next steps, or the identity refusal."""
    try:
        identity = await portal_identity_headers(user, session)
    except PortalIdentityRefused as e:
        return coded(e.code)
    row = await filed_row(draft_id, session)
    customers = identity[CUSTOMERS_HEADER].split(",")
    if row is not None and row.comment_id is not None and row.customer_code in customers and row.requested_by_user_id == user.id:
        portal = Portal(identity=identity, customers=tuple(customers), enabled=())
        return await report_submitted(portal, draft_id, row.id)
    return identity


async def submit(user: User, session: AsyncSession, draft_id: str, request: Request) -> Response:
    """``POST /customer_portal/talon_chat/drafts/{id}/submit`` → ``{request_id}``, or a coded refusal."""
    body = await read_body(request, DraftSubmit)
    if isinstance(body, JSONResponse):
        return body
    try:
        body = body.model_copy(update={"question": clean_question(body.question)})
    except ValueError:
        return coded("invalid_question")
    canonical = object_id(draft_id)
    if canonical is None:
        return coded("draft_not_found")
    filed_before = await already_filed(user, session, canonical)
    if isinstance(filed_before, JSONResponse):
        return filed_before
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    await session.commit()  # the reads are done; no transaction stays open while talon-analyst answers

    checked = await read_draft(portal, canonical)
    if isinstance(checked, JSONResponse):
        return checked
    _, draft = checked
    customer_code = draft["customer_code"]
    target = draft.get("target") if isinstance(draft.get("target"), dict) else {}

    # (1) Look first: a filed draft is reported, whatever else holds now.
    found = await look(canonical, customer_code, session)
    if isinstance(found, int):
        return await report_submitted(portal, canonical, found)
    if found == IN_PROGRESS:
        return coded("draft_conflict")

    if await is_read_only_for(user, customer_code, session):
        return coded("read_only")

    # (2) Claim; then look again, whatever the claim said.
    claim_body: Dict[str, Any] = {"urgency": body.urgency}
    if target.get("kind") == "alert":
        claim_body["file_on"] = body.file_on or "case"
    await session.commit()
    claim = await v2_request("POST", f"/v2/portal/drafts/{canonical}/claim", portal.identity, json_body=claim_body)
    found = await look(canonical, customer_code, session)
    if isinstance(found, int):
        return await report_submitted(portal, canonical, found)
    claimed = parsed(claim)
    if claimed is None:
        return answer(claim) if claim.status is None or not 200 <= claim.status < 300 else coded("failed")
    if found == IN_PROGRESS or claimed.get("claimed") is not True:
        return coded("draft_conflict")

    # (3) File, as the customer, on the draft's own target; (4) the outcome.
    result = await file(canonical, customer_code, target, body, user, session)
    if isinstance(result, int):
        return await report_submitted(portal, canonical, result)
    if result == "draft_conflict":
        return coded("draft_conflict")
    return await report_failed(portal, canonical, result)
