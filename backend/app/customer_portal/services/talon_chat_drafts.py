"""Filing a Talon portal chat draft as a question to the SOC (talon-analyst SPEC D97 (o), (aa), (bb);
§5.3 "Portal chat: CoPilot's side" the submit route; §8 FR-API-39 to -41; plan PC-3).

Talon's ``ask_the_soc`` tool only drafts a question; it files nothing. The customer edits the draft
in the portal, picks the urgency and (for an alert) where it goes, and submits it here. CoPilot then:

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
   so a second filing is impossible; a conflict there means another request filed it, and that row
   is reported). An alert draft with ``file_on: "case"`` (the default) goes on the alert's open case
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


async def look(draft_id: str, customer_code: str, session: AsyncSession) -> Union[int, str, None]:
    """The request this draft was filed as (its id), ``"in_progress"`` when another request is
    filing it now, or None (nothing, or an orphan just deleted)."""
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
        return "in_progress"
    if row.comment_id is not None:
        return row.id
    if row.requested_at is not None and _now() - row.requested_at >= ORPHAN_AFTER:
        logger.warning(f"Talon draft {draft_id}: deleting orphaned SOC request {row.id} (no comment after {ORPHAN_AFTER})")
        await session.execute(delete(CustomerPortalSocRequest).where(CustomerPortalSocRequest.id == row.id))
        await session.commit()
        return None
    return "in_progress"


async def filed_row_id(draft_id: str, session: AsyncSession) -> Optional[int]:
    await session.commit()
    return (
        await session.execute(select(CustomerPortalSocRequest.id).where(CustomerPortalSocRequest.talon_draft_id == draft_id))
    ).scalar_one_or_none()


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


async def file(draft_id: str, target: Dict[str, Any], body: DraftSubmit, user: User, session: AsyncSession) -> Union[int, str]:
    """File the claimed draft as the customer: the request's id, or a failure code."""
    kind, target_id = target.get("kind"), target.get("id")
    if isinstance(target_id, bool) or not isinstance(target_id, int) or target_id < 1:
        return "not_found"
    try:
        if kind == "alert":
            ask = AskOnAlertRequest(question=body.question, urgency=body.urgency, target=body.file_on or "case")
            filed = await soc_requests.ask_on_alert(target_id, ask, user, session, talon_draft_id=draft_id)
        elif kind == "case":
            ask = AskOnCaseRequest(question=body.question, urgency=body.urgency)
            filed = await soc_requests.ask_on_case(target_id, ask, user, session, talon_draft_id=draft_id)
        else:
            return "not_found"
    except ValidationError:
        return "invalid_question"
    except soc_requests.DraftAlreadyFiled:
        existing = await filed_row_id(draft_id, session)
        return existing if existing is not None else "internal_failure"
    except HTTPException as e:
        await session.rollback()
        return _failure_code(e)
    except Exception:  # noqa: BLE001 - the SOC's plumbing never reaches the customer
        logger.exception(f"Talon draft {draft_id}: filing failed")
        await session.rollback()
        return "internal_failure"
    return filed.id


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
    if found == "in_progress":
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
    if found == "in_progress" or claimed.get("claimed") is not True:
        return coded("draft_conflict")

    # (3) File, as the customer, on the draft's own target; (4) the outcome.
    result = await file(canonical, target, body, user, session)
    if isinstance(result, int):
        return await report_submitted(portal, canonical, result)
    return await report_failed(portal, canonical, result)
