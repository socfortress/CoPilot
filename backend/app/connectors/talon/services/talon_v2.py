"""CoPilot's side of talon-analyst's v2 chat: the "Talon v2" setting, its gate, and the thread and
chat proxy (talon-analyst SPEC §5.3 D54 and the M5-5 row, §8 "v2 API"; plan M5-5a).

**The setting** (``talon_connector_settings``, one row per Talon connector, off when missing) is
the only switch: off, every declared proxy route answers 404 ``{"detail": "Not Found"}`` exactly
like a route that doesn't exist (``require_talon_v2``; a method no route declares still answers 405), and nothing of v1 changes. Turning it on is an
admin's, audited, and refused while talon-analyst itself answers ``GET /v2/threads`` with 404
(its ``TALON_V2_API`` is off).

**Identity.** Every upstream request carries the five headers from ``identity.py``, computed from
the JWT's user; the browser's own headers are never forwarded (``v2_client``).

**Answers.** talon-analyst's 2xx bodies pass through with their status. Its refusals keep their
status (409 means a decision is pending, 403 that a customer was taken away: the UI needs both) with
``{"detail": <its short fixed reason, or "Talon request failed">}`` (``refusal_reason``), never its
body as such. Two exceptions, both a 502: no answer at all (no connector, unreachable), and an
upstream 401, which means CoPilot's API key is wrong and must never reach the browser as a 401
(the frontend reads a 401 as the user's own session ending).
"""
import json
import uuid
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings
from app.connectors.talon.schema.talon_v2 import TalonV2AvailabilityResponse
from app.connectors.talon.schema.talon_v2 import TalonV2ChatRequest
from app.connectors.talon.schema.talon_v2 import TalonV2SettingsResponse
from app.connectors.talon.schema.talon_v2 import TalonV2ThreadCreate
from app.connectors.talon.schema.talon_v2 import TalonV2ThreadRename
from app.connectors.talon.services import talon_action_sync
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.identity import talon_identity_headers
from app.connectors.talon.utils import phoenix_client
from app.connectors.talon.utils.approval_tap import ApprovalTappedStream
from app.connectors.talon.utils.universal import refusal_reason
from app.connectors.talon.utils.v2_client import MAX_MESSAGES_BODY_BYTES
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.talon.utils.v2_client import V2Answer
from app.connectors.talon.utils.v2_client import V2StreamingResponse
from app.connectors.talon.utils.v2_client import open_v2_stream
from app.connectors.talon.utils.v2_client import v2_request
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc

FAILED = "Talon request failed"


# ── the setting ───────────────────────────────────────────────────────────────


async def get_settings_row(session: AsyncSession, connector_name: str = TALON_CONNECTOR) -> Optional[TalonConnectorSettings]:
    result = await session.execute(select(TalonConnectorSettings).where(TalonConnectorSettings.connector_name == connector_name))
    return result.scalars().first()


async def is_v2_enabled(session: AsyncSession, connector_name: str = TALON_CONNECTOR) -> bool:
    """Whether the setting is on. A missing row is off."""
    row = await get_settings_row(session, connector_name)
    return bool(row is not None and row.v2_enabled)


def require_talon_v2(connector_name: str = TALON_CONNECTOR):
    """A route dependency: 404 ``{"detail": "Not Found"}`` while the setting is off.

    Starlette's own exception, not FastAPI's: CoPilot's handler for the latter answers
    ``{"success": false, "message": …}`` and logs an error row, while an unknown path answers
    ``{"detail": "Not Found"}`` and logs nothing. Off, these routes look exactly like that.
    Placed after the scope check, so a caller without a token learns nothing about the setting.
    """

    async def _require_talon_v2(session: AsyncSession = Depends(get_db)) -> None:
        if not await is_v2_enabled(session, connector_name):
            raise StarletteHTTPException(status_code=404)

    return _require_talon_v2


async def get_availability(session: AsyncSession, connector_name: str = TALON_CONNECTOR) -> TalonV2AvailabilityResponse:
    """The setting, and whether the run view can be offered (plan M5-9a): v2 on and the "Talon
    Phoenix" connector holding a URL and a key. Reads CoPilot's own rows only: never Phoenix (whether
    the key is a viewer's is checked when a run view is asked for)."""
    enabled = await is_v2_enabled(session, connector_name)
    run_view = enabled and await phoenix_client.is_configured()
    return TalonV2AvailabilityResponse(
        success=True,
        message="Talon v2 chat is on" if enabled else "Talon v2 chat is off",
        enabled=enabled,
        run_view=run_view,
    )


def _settings_response(row: Optional[TalonConnectorSettings], connector_name: str, message: str) -> TalonV2SettingsResponse:
    return TalonV2SettingsResponse(
        success=True,
        message=message,
        connector_name=connector_name,
        v2_enabled=bool(row is not None and row.v2_enabled),
        updated_by_user_id=row.updated_by_user_id if row is not None else None,
        updated_at=row.updated_at if row is not None else None,
    )


def require_admin(user: User) -> None:
    """The setting is an admin's: by the user's role in the database, not only the token's scope
    (a token issued before a demotion still carries ``admin``). The same database truth the proxy
    sends as ``X-Talon-Role``."""
    if user.role_id != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only an admin may read or change the Talon v2 setting")


async def get_v2_settings(user: User, session: AsyncSession, connector_name: str = TALON_CONNECTOR) -> TalonV2SettingsResponse:
    require_admin(user)
    row = await get_settings_row(session, connector_name)
    return _settings_response(row, connector_name, "Talon v2 setting retrieved")


def probe_problem(answer: V2Answer) -> Optional[Tuple[int, str]]:
    """Why talon-analyst's answer to ``GET /v2/threads`` forbids turning v2 on, or None if it allows it.

    Fail closed: only a 2xx turns it on. A 404 means talon-analyst's ``TALON_V2_API`` is off; any
    other answer (a wrong API key, a header it refuses, no answer) would make every v2 request fail.
    Never a 401 or 403: those would read as the admin's own session or rights.
    """
    if answer.status is None:
        return 502, "talon-analyst could not be reached, so the Talon v2 setting stays off"
    if 200 <= answer.status < 300:
        return None
    if answer.status == 404:
        return 409, "talon-analyst's v2 API is off (TALON_V2_API): turn it on there before turning on Talon v2 here"
    return 502, f"talon-analyst refused the v2 check (HTTP {answer.status}), so the Talon v2 setting stays off"


async def update_v2_settings(
    user: User,
    session: AsyncSession,
    v2_enabled: bool,
    request: Optional[Request] = None,
    connector_name: str = TALON_CONNECTOR,
) -> TalonV2SettingsResponse:
    """Turn the setting on or off (admin only, at the route). Turning it on first asks talon-analyst
    for the admin's own threads; it stays off unless that answers 2xx. Audited either way."""
    require_admin(user)
    row = await get_settings_row(session, connector_name)
    old = bool(row is not None and row.v2_enabled)
    audit = {
        "action": AuditAction.CONNECTOR_UPDATE,
        "actor_user_id": user.id,
        "actor_username": user.username,
        "entity_type": "connector",
        "entity_id": connector_name,
        "old_value": {"v2_enabled": old},
        "new_value": {"v2_enabled": v2_enabled},
        "request": request,
    }
    if v2_enabled:
        identity = await talon_identity_headers(user, session)
        problem = probe_problem(await v2_request("GET", "/v2/threads", identity, params={"limit": 1}, connector_name=connector_name))
        if problem is not None:
            status, detail = problem
            await record_audit_event(**audit, result=AuditResult.FAILURE, details=f"Talon v2 setting not turned on: {detail}")
            raise HTTPException(status_code=status, detail=detail)

    row = await _store(session, connector_name, v2_enabled, user.id)
    await record_audit_event(**audit, details=f"Talon v2 setting turned {'on' if v2_enabled else 'off'} for connector '{connector_name}'")
    return _settings_response(row, connector_name, f"Talon v2 turned {'on' if v2_enabled else 'off'}")


async def _store(session: AsyncSession, connector_name: str, v2_enabled: bool, user_id: int) -> TalonConnectorSettings:
    """Upsert the row. Two admins creating it at once: the loser updates the winner's row."""
    for attempt in range(2):
        row = await get_settings_row(session, connector_name)
        if row is None:
            row = TalonConnectorSettings(connector_name=connector_name)
            session.add(row)
        row.v2_enabled = v2_enabled
        row.updated_by_user_id = user_id
        row.updated_at = now_utc()
        try:
            await session.commit()
            return row
        except IntegrityError:
            await session.rollback()
            if attempt:
                raise
    raise AssertionError("unreachable")


# ── answers ───────────────────────────────────────────────────────────────────


def refused(status: Optional[int], body: bytes) -> JSONResponse:
    """A non-2xx upstream answer as CoPilot's answer: the same status, a fixed or short reason."""
    if status is None:
        return JSONResponse({"detail": FAILED}, status_code=502)
    if status == 401:  # CoPilot's API key: an operator's problem, never the user's session
        logger.error("Talon v2: talon-analyst refused CoPilot's API key (401)")
        return JSONResponse({"detail": FAILED}, status_code=502)
    if not 400 <= status < 600:
        logger.error(f"Talon v2: unexpected upstream status {status}")
        return JSONResponse({"detail": FAILED}, status_code=502)
    reason = refusal_reason(status, body)
    if status >= 500 or reason is None:
        logger.error(f"Talon v2: talon-analyst answered {status}")
    return JSONResponse({"detail": reason or FAILED}, status_code=status)


#: Every v2 JSON answer: a thread list, a title, a transcript is the user's own and must not be
#: kept by a browser or a proxy (talon-analyst sends the same on its own v2 answers).
NO_STORE = {"Cache-Control": "no-store"}


class RelayedJSONResponse(JSONResponse):
    """A JSON body relayed as the bytes it arrived as (already checked to parse)."""

    def render(self, content: Any) -> bytes:
        return content


def relay(answer: V2Answer) -> JSONResponse:
    """A JSON upstream answer as CoPilot's answer, never stored by a cache. A 2xx body is relayed
    as the bytes talon-analyst sent, once they parse as JSON (else a 502 with the fixed text)."""
    if answer.status is not None and 200 <= answer.status < 300:
        try:
            json.loads(answer.body)
        except (ValueError, RecursionError):  # not JSON, or nested past the recursion limit
            logger.error(f"Talon v2: talon-analyst answered {answer.status} with a body that isn't JSON")
            response = JSONResponse({"detail": FAILED}, status_code=502)
        else:
            response = RelayedJSONResponse(answer.body, status_code=answer.status)
    else:
        response = refused(answer.status, answer.body)
    response.headers.update(NO_STORE)
    return response


# ── threads ───────────────────────────────────────────────────────────────────


async def _identity_then_release(user: User, session: AsyncSession) -> Dict[str, str]:
    """The user's identity headers, then the request's session closed: everything a proxy route
    reads from the database has been read, and talon-analyst's answer may take seconds (a turn,
    minutes), so no pooled connection is held while waiting. (The connector row is read in a
    session of its own, opened and closed around that one read.)"""
    identity = await talon_identity_headers(user, session)
    await session.close()
    return identity


async def list_threads(user: User, session: AsyncSession, params: Dict[str, Any]) -> JSONResponse:
    identity = await _identity_then_release(user, session)
    return relay(await v2_request("GET", "/v2/threads", identity, params={k: v for k, v in params.items() if v is not None}))


async def check_thread_customer(user: User, session: AsyncSession, customer_code: str) -> None:
    """A new thread's customer: talon-analyst's grammar, the caller's access, and a real customer.

    In that order, so a scoped analyst asking for a customer they lack learns nothing about whether
    it exists (403 either way), and an admin, whose ``*`` talon-analyst accepts for any code, can't
    scope a thread to a typo. The code must match the customer row exactly: MySQL compares
    case-insensitively, while talon-analyst's tenant keys don't.
    """
    if not is_talon_customer_code(customer_code):
        raise HTTPException(status_code=400, detail="customer_code is not a valid customer code")
    await customer_access_handler.enforce_customer_access(user, customer_code, session)
    result = await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))
    if customer_code not in set(result.scalars().all()):
        raise HTTPException(status_code=400, detail="customer_code is not a customer")


async def create_thread(user: User, session: AsyncSession, body: TalonV2ThreadCreate) -> JSONResponse:
    if body.customer_code is not None:
        await check_thread_customer(user, session, body.customer_code)
    identity = await _identity_then_release(user, session)
    payload = {"title": body.title, "customer_code": body.customer_code}
    return relay(await v2_request("POST", "/v2/threads", identity, json_body=payload))


async def rename_thread(user: User, session: AsyncSession, thread_id: uuid.UUID, body: TalonV2ThreadRename) -> JSONResponse:
    identity = await _identity_then_release(user, session)
    return relay(await v2_request("PATCH", f"/v2/threads/{thread_id}", identity, json_body={"title": body.title}))


async def archive_thread(user: User, session: AsyncSession, thread_id: uuid.UUID) -> JSONResponse:
    identity = await _identity_then_release(user, session)
    answer = await v2_request("DELETE", f"/v2/threads/{thread_id}", identity)
    if answer.status is not None and 200 <= answer.status < 300:
        # talon-analyst withdrew the thread's pending proposals with it (M5-11): mirror that.
        talon_action_sync.resync_thread_later(str(thread_id), user.id)
    return relay(answer)


async def thread_messages(user: User, session: AsyncSession, thread_id: uuid.UUID, params: Dict[str, Any]) -> JSONResponse:
    """A page of the thread's earlier turns (talon-analyst M5-5t, SPEC §8 "Reading turns back"), as
    the AI SDK's UI messages, redacted by talon-analyst exactly as its stream is. Only ``limit`` and
    ``before`` are forwarded. A 403 keeps its fixed text: the thread's customer was removed, or the
    caller's alert access narrowed since the thread began."""
    identity = await _identity_then_release(user, session)
    answer = await v2_request(
        "GET",
        f"/v2/threads/{thread_id}/messages",
        identity,
        params={k: v for k, v in params.items() if v is not None},
        max_body_bytes=MAX_MESSAGES_BODY_BYTES,
    )
    return relay(answer)


# ── chat ──────────────────────────────────────────────────────────────────────


def submit_message(thread_id: uuid.UUID, body: TalonV2ChatRequest) -> Dict[str, Any]:
    """The AI SDK's ``SubmitMessage`` CoPilot sends: the thread id, and one user message of one text
    part. Built here, never taken from the browser: talon-analyst reads only the newest message's
    text anyway, and the history is the thread's."""
    return {
        "trigger": "submit-message",
        "id": str(thread_id),
        "messages": [
            {
                "id": body.message_id or f"copilot-{uuid.uuid4().hex}",
                "role": "user",
                "parts": [{"type": "text", "text": body.message}],
            },
        ],
    }


async def chat(user: User, session: AsyncSession, thread_id: uuid.UUID, body: TalonV2ChatRequest) -> Response:
    """One chat turn. A refusal before the stream keeps its status; a 2xx streams through as is."""
    identity = await _identity_then_release(user, session)
    opened = await open_v2_stream(f"/v2/chat/{thread_id}", identity, submit_message(thread_id, body))
    if isinstance(opened, V2Answer):
        return refused(opened.status, opened.body)
    # The bytes pass through unchanged; once the stream ends, however it ends, each approval card's
    # proposal is read back from talon-analyst as this user and mirrored (M5-11).
    user_id = user.id
    tapped = ApprovalTappedStream(opened, lambda ids: talon_action_sync.sync_later(ids, user_id))
    return V2StreamingResponse(tapped)
