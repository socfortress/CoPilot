"""The SOC side of Talon portal chat (talon-analyst SPEC D97, §5.3 "Portal chat: CoPilot's side";
plan PC-3): the review proxy and the lookup meter.

**The review proxy** (``/api/talon/v2/portal_review/…`` → talon-analyst's ``/v2/portal-review/…``,
FR-API-43, -44): a reviewer reads a customer's portal threads and transcripts, read-only, with the
SOC identity (``talon_identity_headers``). The review rule is talon-analyst's (FR-CHAT-9): an admin
with the customer, or an analyst or responder with the customer **and unrestricted tag access**
(a portal user sees every alert of their customer, so a transcript can show any of them). CoPilot
applies the same rule first: a customer the caller lacks, or restricted tags, is ``review_forbidden``
on the list, and ``thread_not_found`` on a transcript (talon-analyst answers the same for a thread
the caller may not review). talon-analyst audits every review read.

**The lookup meter** (``/api/talon/v2/portal/ioc_lookups``, D97 (r), (cc)): talon-analyst's
``talon.tools.portal_meter`` reserves one of the customer's IOC enrichment lookups before each
portal intel or OpenCTI call, so the portal's own lookups and Talon's share one daily limit in
CoPilot's own counter (``customer_portal_ioc_lookup``). The Talon service account only. It checks
that ``user_id`` is a ``customer_user`` with access to ``customer_code`` (else 404, nothing
written), then runs the portal's own rules under the customer's settings lock
(``ioc_enrichment.reserve_lookup``: 403 ``ioc_off``, 409 ``ioc_in_progress`` within ``IN_PROGRESS``,
429 ``ioc_limit``) and writes one lookup row, the value hashed as the portal hashes its own. It
writes nothing else and executes nothing (INV-ACT-1, D48).
"""
import uuid
from typing import Any
from typing import Dict
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.connectors.talon.services.identity import ALL
from app.connectors.talon.services.identity import TAGS_HEADER
from app.connectors.talon.services.identity import UNTAGGED_HEADER
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.identity import talon_identity_headers
from app.connectors.talon.services.talon_service_account import is_talon_service_account
from app.connectors.talon.services.talon_v2 import relay
from app.connectors.talon.utils.portal_errors import NO_STORE
from app.connectors.talon.utils.portal_errors import coded
from app.connectors.talon.utils.portal_errors import relay_refusal
from app.connectors.talon.utils.v2_client import MAX_MESSAGES_BODY_BYTES
from app.connectors.talon.utils.v2_client import V2Answer
from app.connectors.talon.utils.v2_client import v2_request
from app.customer_portal.services import ioc_enrichment
from app.customer_portal.services import ioc_enrichment_sources as sources
from app.db.universal_models import CustomerPortalIocLookup
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler

SERVICE_ONLY = "Only the Talon service account may reserve portal chat lookups"
#: ``customer_portal_ioc_lookup.reserved_by`` of the rows this meter reserves (the portal's own are NULL).
METER = "talon"
#: The longest indicator value metered (the portal's own IOC values are bounded the same way).
MAX_VALUE_CHARS = 2048


def _answer(result: V2Answer) -> JSONResponse:
    if result.status is not None and 200 <= result.status < 300:
        return relay(result)
    return relay_refusal(result.status, result.body)


# ── the review proxy ──────────────────────────────────────────────────────────


def may_review(identity: Dict[str, str]) -> bool:
    """The tag half of the review rule: an admin, or unrestricted tag access (``*`` and untagged)."""
    return identity.get("X-Talon-Role") == "admin" or (identity.get(TAGS_HEADER) == ALL and identity.get(UNTAGGED_HEADER) == "true")


async def review_threads(user: User, session: AsyncSession, customer_code: Optional[str], params: Dict[str, Any]) -> Response:
    """FR-API-43: one customer's portal threads, for a reviewer of that customer."""
    if not customer_code:
        return coded("invalid_request")
    if not is_talon_customer_code(customer_code) or not await customer_access_handler.check_customer_access(user, customer_code, session):
        return coded("review_forbidden")
    identity = await talon_identity_headers(user, session)
    if not may_review(identity):
        return coded("review_forbidden")
    await session.close()
    query = {"customer_code": customer_code, **{k: v for k, v in params.items() if v is not None}}
    return _answer(await v2_request("GET", "/v2/portal-review/threads", identity, params=query))


async def review_messages(user: User, session: AsyncSession, thread_id: str, params: Dict[str, Any]) -> Response:
    """FR-API-44: one portal thread's transcript, for a reviewer of its customer (talon-analyst
    knows the thread's customer and decides; CoPilot refuses restricted tags first)."""
    try:
        canonical = str(uuid.UUID(thread_id)) if len(thread_id) <= 64 else None
    except ValueError:
        canonical = None
    if canonical is None:
        return coded("thread_not_found")
    identity = await talon_identity_headers(user, session)
    if not may_review(identity):
        return coded("thread_not_found")
    await session.close()
    query = {k: v for k, v in params.items() if v is not None}
    return _answer(
        await v2_request(
            "GET",
            f"/v2/portal-review/threads/{canonical}/messages",
            identity,
            params=query,
            max_body_bytes=MAX_MESSAGES_BODY_BYTES,
        ),
    )


# ── the lookup meter ──────────────────────────────────────────────────────────


async def require_service_account(user: User, session: AsyncSession) -> None:
    if not await is_talon_service_account(user, session):
        logger.warning(f"Refused {getattr(user, 'username', '?')} on the Talon portal lookup meter: not the Talon service account")
        raise HTTPException(status_code=403, detail=SERVICE_ONLY)


async def is_portal_user_of(user_id: int, customer_code: str, session: AsyncSession) -> bool:
    """``user_id`` is a ``customer_user`` assigned to ``customer_code`` (``user_customer_access``)."""
    portal_user = await session.get(User, user_id)
    if portal_user is None or portal_user.role_id != RoleEnum.customer_user.value:
        return False
    if getattr(portal_user, "disabled_at", None) is not None:  # a disabled account's session ended (#1296)
        return False
    found = await session.execute(
        select(UserCustomerAccess.customer_code).where(
            UserCustomerAccess.user_id == user_id,
            UserCustomerAccess.customer_code == customer_code,
        ),
    )
    return customer_code in set(found.scalars().all())


#: The meter's refusals by the portal's own rules' statuses.
_REFUSALS = {403: "ioc_off", 409: "ioc_in_progress", 429: "ioc_limit"}


async def reserve(user: User, session: AsyncSession, body: Dict[str, Any]) -> Response:
    """``POST /talon/v2/portal/ioc_lookups`` ``{customer_code, user_id, value}`` → ``201 {lookup_id}``."""
    await require_service_account(user, session)
    customer_code, user_id, value = body.get("customer_code"), body.get("user_id"), body.get("value")
    if (
        set(body) != {"customer_code", "user_id", "value"}
        or not isinstance(customer_code, str)
        or not is_talon_customer_code(customer_code)
        or isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or not 1 <= user_id <= 2_147_483_647
        or not isinstance(value, str)
        or not 0 < len(value) <= MAX_VALUE_CHARS
    ):
        return coded("invalid_request")
    exists = (await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))).scalars().all()
    if customer_code not in set(exists) or not await is_portal_user_of(user_id, customer_code, session):
        return coded("not_found")
    digest = ioc_enrichment.value_digest(sources.classify(value)[1])
    try:
        lookup_id = await ioc_enrichment.reserve_lookup(customer_code, digest, session, user_id=user_id, reserved_by=METER)
    except HTTPException as e:
        code = _REFUSALS.get(e.status_code)
        if code is None:
            raise
        return coded(code)
    logger.info(f"Talon portal chat: lookup {lookup_id} reserved for customer {customer_code}, portal user {user_id}")
    return JSONResponse({"lookup_id": lookup_id}, status_code=201, headers=NO_STORE)


async def complete(user: User, session: AsyncSession, lookup_id: int, body: Dict[str, Any]) -> Response:
    """``POST /talon/v2/portal/ioc_lookups/{lookup_id}/complete`` ``{answered}`` → ``204``.

    ``answered: true`` sets ``completed_at``; ``false`` deletes the row (a lookup no source answered
    costs nothing). Only a lookup this meter reserved (``reserved_by``) and still open, locked
    while it changes: a completed one, or one of the portal's own, is never touched."""
    await require_service_account(user, session)
    answered = body.get("answered")
    if set(body) != {"answered"} or not isinstance(answered, bool):
        return coded("invalid_request")
    # Only a row this meter reserved and that is still open, locked while it changes: never one of
    # the portal's own lookups, and never one completed in between (review of #1327, L4).
    row = (
        (
            await session.execute(
                select(CustomerPortalIocLookup)
                .where(
                    CustomerPortalIocLookup.id == lookup_id,
                    CustomerPortalIocLookup.reserved_by == METER,
                    CustomerPortalIocLookup.completed_at.is_(None),
                )
                .with_for_update(),
            )
        )
        .scalars()
        .first()
    )
    if row is None:
        await session.rollback()
        return coded("not_found")
    if answered:
        row.completed_at = ioc_enrichment._now()
    else:
        await session.delete(row)
    await session.commit()
    return Response(status_code=204, headers=NO_STORE)
