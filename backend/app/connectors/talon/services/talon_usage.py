"""CoPilot's proxy of talon-analyst's usage and budgets APIs (talon-analyst SPEC §13.5 FR-COST-4 and
FR-COST-5 as built, §8 "Usage and budgets", D51; plan M5-9a, decisions B, D and G).

Every route is on ``talon_v2_proxy_router``: admin or analyst by token (a responder's carries
``analyst``), then the "Talon v2" setting (404 while off). Identity is the five headers
``_identity_then_release`` computes from the user, after which the request's session is closed.

- ``GET /talon/v2/usage``: the query is checked as talon-analyst checks it (same fixed texts), and
  ``customer_code`` must also pass the grammar and ``enforce_customer_access`` here. Only ``from``,
  ``to``, ``group_by`` and ``customer_code`` are forwarded. For an admin's ``group_by=user``, each
  group whose key is a CoPilot user id gains that user's ``username``. **Decision G:** talon-analyst
  filters aggregate usage by customer, not by alert tags (D41 applies to one investigation's cost);
  that is accepted and recorded, not something CoPilot narrows.
- ``GET /talon/v2/usage/investigations/{job_id}`` (decision D, per job): the ``ai_analyst_job`` row
  must exist, its alert must pass ``_ensure_alert_access`` (customer and tags) and be the job's
  customer's; the row's own id is what is sent upstream. Unknown and refused answer the same 404.
- ``GET /talon/v2/usage/threads/{thread_id}``: a UUID, relayed; talon-analyst enforces owner-only.
- ``GET /talon/v2/budgets`` and ``PUT /talon/v2/budgets/{code}`` (decision B): an admin's, by the
  role in the database as well as the token (a demoted admin's old token is refused). The ``PUT``
  checks the customer as a new thread's is checked (``check_thread_customer``), takes a strict body
  (``daily_usd`` and ``monthly_usd``, each null, ``"unlimited"`` or a decimal string), reads the old
  values first, and is audited (``talon_budget.update``) with the old and new values, failures too.

Answers: talon-analyst's 2xx body is relayed; its refusals keep their status with its short fixed
text (``refusal_reason``) or ``Talon request failed``; a 401 (CoPilot's API key) or no answer is a
502. CoPilot's own refusals are ``{"detail": <fixed text>}``. Every answer is ``no-store``.
"""
import json
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Any
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.talon_runs import JobRefused
from app.connectors.talon.services.talon_runs import authorize_job
from app.connectors.talon.services.talon_v2 import FAILED
from app.connectors.talon.services.talon_v2 import NO_STORE
from app.connectors.talon.services.talon_v2 import _identity_then_release
from app.connectors.talon.services.talon_v2 import check_thread_customer
from app.connectors.talon.services.talon_v2 import relay
from app.connectors.talon.utils.v2_client import V2Answer
from app.connectors.talon.utils.v2_client import v2_request
from app.db.db_session import get_db_session
from app.middleware.customer_access import customer_access_handler

#: talon-analyst ``api/usage.py``: ``GROUP_BY``, ``MAX_DAYS``, ``DATE_PATTERN`` and its texts.
GROUP_BY = frozenset({"customer", "model", "provider", "role", "stage", "day", "user"})
MAX_DAYS = 366
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
CUSTOMER_CODE_MAX = 64
INVALID = "invalid request"
NOT_ACCESSIBLE = "customer not accessible"
INVALID_CUSTOMER = "invalid customer_code"
JOB_NOT_FOUND = "investigation not found"
THREAD_NOT_FOUND = "thread not found"
ADMIN_ONLY = "Only an admin may read or set Talon budgets"

#: A budget amount: a positive decimal, at most 12 places (``customer_budget``'s Numeric(20, 12)),
#: at most talon-analyst's ``MAX_BUDGET_USD``. No sign, exponent or whitespace.
USD_AMOUNT = re.compile(r"(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,12})?")
MAX_BUDGET_USD = 1_000_000_000
UNLIMITED = "unlimited"
BUDGET_FIELDS = ("daily_usd", "monthly_usd")
MAX_BUDGET_BODY_BYTES = 4096


def refusal(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status, headers=dict(NO_STORE))


def is_admin(user: User) -> bool:
    """By the role in the database, not the token's scope (a token outlives a demotion)."""
    return user.role_id == RoleEnum.admin


# ── GET /usage ────────────────────────────────────────────────────────────────


def _day(value: Optional[str]) -> Optional[date]:
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def usage_query_problem(params: Mapping[str, Optional[str]]) -> Optional[Tuple[int, str]]:
    """Why talon-analyst would refuse this ``GET /v2/usage`` query, with its status and text, or
    None. The same checks in the same order (``api/usage.py``: the query's parsing, then
    ``_window``, then ``checked_customer``)."""
    first, last = _day(params.get("from")), _day(params.get("to"))
    group_by = params.get("group_by")
    code = params.get("customer_code")
    if first is None or last is None:
        return 422, INVALID
    if group_by is not None and group_by not in GROUP_BY:
        return 422, INVALID
    if code is not None and len(code) > CUSTOMER_CODE_MAX:
        return 422, INVALID
    if first > last:
        return 400, "from is after to"
    if (last - first).days + 1 > MAX_DAYS:
        return 400, f"the range is longer than {MAX_DAYS} days"
    if last == date.max:
        return 400, "to is out of range"
    if code is not None and not is_talon_customer_code(code):
        return 400, INVALID_CUSTOMER
    return None


async def _usernames(ids) -> Dict[str, str]:
    """CoPilot's usernames for these user ids (strings of digits), in a session of its own."""
    numbers = sorted({int(i) for i in ids})
    if not numbers:
        return {}
    async with get_db_session() as session:
        result = await session.execute(select(User.id, User.username).where(User.id.in_(numbers)))
        return {str(row.id): row.username for row in result.all()}


async def with_usernames(answer: V2Answer) -> JSONResponse:
    """An admin's ``group_by=user`` report, each group keyed by a CoPilot user id given its
    ``username`` (None for a key that isn't one: the investigations' ``null``, an unknown id)."""
    try:
        payload = json.loads(answer.body)
        groups = payload["groups"]
        if not isinstance(groups, list) or not all(isinstance(group, dict) for group in groups):
            raise TypeError("groups")
    except (ValueError, KeyError, TypeError):
        logger.error("Talon v2 usage: talon-analyst's group_by=user answer isn't a report")
        return refusal(502, FAILED)
    ids = [group.get("key") for group in groups]
    names = await _usernames(i for i in ids if isinstance(i, str) and i.isdigit() and len(i) <= 18)
    for group in groups:
        key = group.get("key")
        group["username"] = names.get(key) if isinstance(key, str) else None
    return JSONResponse(payload, status_code=answer.status, headers=dict(NO_STORE))


async def usage(user: User, session: AsyncSession, params: Mapping[str, Optional[str]]) -> JSONResponse:
    problem = usage_query_problem(params)
    if problem is not None:
        return refusal(*problem)
    code = params.get("customer_code")
    if code is not None:
        try:
            await customer_access_handler.enforce_customer_access(user, code, session)
        except HTTPException:
            return refusal(403, NOT_ACCESSIBLE)
    admin = is_admin(user)
    identity = await _identity_then_release(user, session)
    forwarded = {k: params.get(k) for k in ("from", "to", "group_by", "customer_code") if params.get(k) is not None}
    got = await v2_request("GET", "/v2/usage", identity, params=forwarded)
    if admin and params.get("group_by") == "user" and got.status is not None and 200 <= got.status < 300:
        return await with_usernames(got)
    return relay(got)


# ── GET /usage/investigations/{job_id} ────────────────────────────────────────


async def investigation_usage(user: User, session: AsyncSession, job_id: str) -> JSONResponse:
    """One investigation's cost (decision D): CoPilot's job and alert rows decide who sees it."""
    try:
        job = await authorize_job(user, session, job_id)
    except JobRefused:
        await session.close()
        return refusal(404, JOB_NOT_FOUND)
    except HTTPException as e:
        await session.close()
        return refusal(e.status_code, "This role may not see Talon usage")
    identity = await _identity_then_release(user, session)
    return relay(await v2_request("GET", f"/v2/usage/investigations/{job.job_id}", identity))


# ── GET /usage/threads/{thread_id} ────────────────────────────────────────────


async def thread_usage(user: User, session: AsyncSession, thread_id: str) -> JSONResponse:
    try:
        thread = uuid.UUID(thread_id)
    except (ValueError, TypeError, AttributeError):
        await session.close()
        return refusal(404, THREAD_NOT_FOUND)
    identity = await _identity_then_release(user, session)
    return relay(await v2_request("GET", f"/v2/usage/threads/{thread}", identity))


# ── budgets ───────────────────────────────────────────────────────────────────


async def budgets(user: User, session: AsyncSession, customer_code: Optional[str]) -> JSONResponse:
    if not is_admin(user):
        await session.close()
        return refusal(403, ADMIN_ONLY)
    if customer_code is not None and (len(customer_code) > CUSTOMER_CODE_MAX or not is_talon_customer_code(customer_code)):
        await session.close()
        return refusal(400, INVALID_CUSTOMER)
    identity = await _identity_then_release(user, session)
    params = {"customer_code": customer_code} if customer_code is not None else None
    return relay(await v2_request("GET", "/v2/budgets", identity, params=params))


class BodyProblem(ValueError):
    """The PUT body isn't a budget override (a fixed text, never the value)."""


def _amount(value: Any, name: str) -> Optional[str]:
    if value is None or value == UNLIMITED:
        return value
    if not isinstance(value, str) or not USD_AMOUNT.fullmatch(value):
        raise BodyProblem(f"{name} must be null, 'unlimited' or a positive USD amount such as 25 or 12.50")
    amount = Decimal(value)
    if amount <= 0 or amount > MAX_BUDGET_USD:
        raise BodyProblem(f"{name} must be a positive USD amount up to {MAX_BUDGET_USD}")
    return value


async def read_body(request: Request) -> bytes:
    """The request's body, read no further than ``MAX_BUDGET_BODY_BYTES``."""
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BUDGET_BODY_BYTES:
            raise BodyProblem("the body is too large")
    return bytes(body)


def parse_budget_body(raw: bytes) -> Dict[str, Optional[str]]:
    """``{"daily_usd": …, "monthly_usd": …}``, both present (the body replaces both), nothing else."""
    if len(raw) > MAX_BUDGET_BODY_BYTES:
        raise BodyProblem("the body is too large")
    try:
        body = json.loads(raw)
    except ValueError:
        raise BodyProblem("the body must be JSON") from None
    if not isinstance(body, dict) or set(body) != set(BUDGET_FIELDS):
        raise BodyProblem("the body must have exactly daily_usd and monthly_usd")
    return {name: _amount(body[name], name) for name in BUDGET_FIELDS}


def _limits(answer: V2Answer, code: str) -> Optional[Dict[str, Any]]:
    """The customer's current daily and monthly ceilings from ``GET /v2/budgets``: what the audit
    records as the old value. None if the answer doesn't hold them."""
    try:
        payload = json.loads(answer.body)
        (entry,) = [c for c in payload["customers"] if isinstance(c, dict) and c.get("customer_code") == code]
        return {
            window: {"limit_usd": entry[window].get("limit_usd"), "source": entry[window].get("source")} for window in ("daily", "monthly")
        }
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


async def put_budget(user: User, session: AsyncSession, customer_code: str, request: Request) -> JSONResponse:
    """An admin's override for one customer, audited with the old and new values, failures too."""
    audit: Dict[str, Any] = {
        "action": AuditAction.TALON_BUDGET_UPDATE,
        "actor_user_id": user.id,
        "actor_username": user.username,
        "entity_type": "talon_budget",
        "entity_id": customer_code[:CUSTOMER_CODE_MAX],
        "request": request,
    }

    async def failed(status: int, detail: str, *, new_value: Optional[dict] = None, old_value: Optional[dict] = None) -> JSONResponse:
        await record_audit_event(
            **audit,
            result=AuditResult.FAILURE,
            old_value=old_value,
            new_value=new_value,
            details=f"Talon budget not set: {detail}",
        )
        return refusal(status, detail)

    if not is_admin(user):
        await session.close()
        return await failed(403, ADMIN_ONLY)
    try:
        await check_thread_customer(user, session, customer_code)
    except HTTPException as e:
        await session.close()
        return await failed(e.status_code, NOT_ACCESSIBLE if e.status_code == 403 else str(e.detail))
    audit["customer_code"] = customer_code
    try:
        body = parse_budget_body(await read_body(request))
    except BodyProblem as e:
        await session.close()
        return await failed(422, str(e))
    identity = await _identity_then_release(user, session)

    before = await v2_request("GET", "/v2/budgets", identity, params={"customer_code": customer_code})
    old = _limits(before, customer_code) if before.status == 200 else None
    if old is None:
        # Without the old values the change can't be audited as it must be: nothing is changed.
        if before.status is not None and 400 <= before.status < 500 and before.status != 401:
            response = relay(before)
            return await failed(response.status_code, json.loads(response.body)["detail"], new_value=body)
        return await failed(502, FAILED, new_value=body)

    got = await v2_request("PUT", f"/v2/budgets/{customer_code}", identity, json_body=body)
    response = relay(got)
    if got.status is not None and 200 <= got.status < 300 and response.status_code < 300:
        await record_audit_event(
            **audit,
            result=AuditResult.SUCCESS,
            old_value=old,
            new_value=body,
            details=f"Talon budget set for customer '{customer_code}'",
        )
        return response
    try:
        detail = json.loads(response.body)["detail"]
    except (ValueError, KeyError, TypeError):
        detail = FAILED
    await record_audit_event(
        **audit,
        result=AuditResult.FAILURE,
        old_value=old,
        new_value=body,
        details=f"Talon budget not set: talon-analyst answered {got.status}",
    )
    return refusal(response.status_code, detail if isinstance(detail, str) else FAILED)
