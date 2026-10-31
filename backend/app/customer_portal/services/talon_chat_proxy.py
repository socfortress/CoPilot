"""The Customer Portal's proxy to talon-analyst's portal chat routes (talon-analyst SPEC D97, §5.3
"Portal chat: CoPilot's side", §8 FR-API-33 to -42; plan PC-3).

**Who.** A ``customer_user`` only (the route's scope, and the database role in
``portal_identity_headers``). Their identity is computed here on every request from CoPilot's own
rules: ``X-Talon-Role: customer``, their own customers, tags ``*`` / untagged ``true``, and
``X-Talon-Read-Only``. Nothing from the browser carries it: the body names at most the customer of
a new thread, which must be one of the user's own.

**The switch, on every request** (``talon_chat.enabled_customers``, availability's rule): a route
that names a customer checks that customer; a route that names a thread checks the thread's
customer, which CoPilot reads from talon-analyst first (the thread's read-back, one turn); a route
that names a draft checks the draft's customer, read back the same way. Off is ``portal_off`` before
anything is forwarded. talon-analyst reads the same switch itself before every model request, so a
thread turned off mid-turn stops at its next request there.

**Forwarded:** to talon-analyst's ``/v2/portal/…`` and nothing else (``v2_client.check_identity_path``
refuses any other path for a portal identity). Path ids are checked as UUIDs here, so nothing but
an id reaches the path. JSON answers pass through; the chat stream passes through byte for byte,
error chunks and their ``code`` included. Refusals are ``{"detail", "code"}`` (``portal_errors``).

**Counts nothing:** the message caps are talon-analyst's count alone (FR-COST-4 "Portal chat").
"""
import json
import uuid
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.models.users import User
from app.connectors.talon.services.identity import CUSTOMERS_HEADER
from app.connectors.talon.services.identity import PortalIdentityRefused
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.identity import portal_identity_headers
from app.connectors.talon.services.talon_v2 import relay
from app.connectors.talon.utils.portal_errors import coded
from app.connectors.talon.utils.portal_errors import relay_refusal
from app.connectors.talon.utils.v2_client import MAX_MESSAGES_BODY_BYTES
from app.connectors.talon.utils.v2_client import V2Answer
from app.connectors.talon.utils.v2_client import V2StreamingResponse
from app.connectors.talon.utils.v2_client import open_v2_stream
from app.connectors.talon.utils.v2_client import v2_request
from app.customer_portal.schema.talon_chat import ChatMessage
from app.customer_portal.schema.talon_chat import Feedback
from app.customer_portal.schema.talon_chat import SubmitMessage
from app.customer_portal.schema.talon_chat import ThreadCreate
from app.customer_portal.schema.talon_chat import ThreadRename
from app.customer_portal.services import talon_chat
from app.customer_portal.services.languages import portal_locale
from app.incidents.models import Alert

#: The largest request body read from the portal (a message, a title, a draft's question).
MAX_BODY_BYTES = 1024 * 1024

M = TypeVar("M", bound=BaseModel)


@dataclass(frozen=True)
class Portal:
    """A portal user's request, checked: their identity headers and the customers whose chat is on."""

    identity: Dict[str, str]
    customers: Tuple[str, ...]
    enabled: Tuple[str, ...]


async def begin(user: User, session: AsyncSession) -> Union[Portal, JSONResponse]:
    """The identity, then the switch for the user's customers. With none on, ``portal_off``."""
    try:
        identity = await portal_identity_headers(user, session)
    except PortalIdentityRefused as e:
        return coded(e.code)
    customers = tuple(identity[CUSTOMERS_HEADER].split(","))
    enabled = tuple(code for code in await talon_chat.enabled_customers(user, session) if code in customers)
    if not enabled:
        return coded("portal_off")
    return Portal(identity=identity, customers=customers, enabled=enabled)


def check_customer(portal: Portal, customer_code: Any) -> Optional[JSONResponse]:
    """A customer named by the request or read back from talon-analyst: the user's, and switched on."""
    if not isinstance(customer_code, str) or customer_code not in portal.customers:
        return coded("customer_not_accessible")
    if customer_code not in portal.enabled:
        return coded("portal_off")
    return None


def object_id(value: str) -> Optional[str]:
    """A thread or draft id as talon-analyst's (a UUID), in its canonical form, or None."""
    try:
        return str(uuid.UUID(value)) if isinstance(value, str) and len(value) <= 64 else None
    except ValueError:
        return None


async def read_json(request: Request) -> Union[Any, JSONResponse]:
    """The request's JSON body, at most ``MAX_BODY_BYTES``: ``body_too_large``, or
    ``invalid_request`` for anything that isn't JSON. Never echoes the body."""
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > MAX_BODY_BYTES:
                return coded("body_too_large")
        except ValueError:
            return coded("invalid_request")
    chunks: List[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            return coded("body_too_large")
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks))
    except (ValueError, RecursionError):  # ValueError includes JSON and Unicode errors
        return coded("invalid_request")


async def read_body(request: Request, model: Type[M]) -> Union[M, JSONResponse]:
    """The request's JSON body as ``model``, or the coded refusal (``invalid_request`` for any shape
    that doesn't validate)."""
    raw = await read_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    try:
        return model.model_validate(raw)
    except ValidationError:
        return coded("invalid_request")


def answer(result: V2Answer) -> JSONResponse:
    """A talon-analyst JSON answer as CoPilot's: a 2xx as its bytes, a refusal with its code."""
    if result.status is not None and 200 <= result.status < 300:
        return relay(result)
    return relay_refusal(result.status, result.body)


def parsed(result: V2Answer) -> Optional[Dict[str, Any]]:
    """A 2xx answer's JSON object, or None."""
    if result.status is None or not 200 <= result.status < 300:
        return None
    try:
        payload = json.loads(result.body)
    except (ValueError, RecursionError):
        return None
    return payload if isinstance(payload, dict) else None


async def release(session: AsyncSession) -> None:
    """Everything the route reads from CoPilot's database has been read: the session goes back
    before talon-analyst is asked (a turn takes minutes), as the SOC's v2 proxy does."""
    await session.close()


# ── threads ───────────────────────────────────────────────────────────────────


async def thread_customer(portal: Portal, thread_id: str, params: Optional[Dict[str, Any]] = None) -> Union[V2Answer, JSONResponse]:
    """Read the thread back (one turn, or the caller's page) and check its customer's switch.
    Returns the read-back to relay, or the refusal."""
    result = await v2_request(
        "GET",
        f"/v2/portal/threads/{thread_id}/messages",
        portal.identity,
        params=params if params is not None else {"limit": 1},
        max_body_bytes=MAX_MESSAGES_BODY_BYTES,
    )
    payload = parsed(result)
    if payload is None:
        return coded("failed") if result.status is not None and 200 <= result.status < 300 else answer(result)
    thread = payload.get("thread")
    customer_code = thread.get("customer_code") if isinstance(thread, dict) else None
    if customer_code not in portal.customers:  # talon-analyst never answers another's thread; checked anyway
        return coded("thread_not_found")
    if customer_code not in portal.enabled:
        return coded("portal_off")
    return result


async def list_threads(user: User, session: AsyncSession, params: Dict[str, Any]) -> Response:
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    await release(session)
    return answer(await v2_request("GET", "/v2/portal/threads", portal.identity, params={k: v for k, v in params.items() if v is not None}))


async def create_thread(user: User, session: AsyncSession, request: Request) -> Response:
    body = await read_body(request, ThreadCreate)
    if isinstance(body, JSONResponse):
        return body
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    if not is_talon_customer_code(body.customer_code):
        return coded("customer_not_accessible")
    refused = check_customer(portal, body.customer_code)
    if refused is not None:
        return refused
    if body.alert_id is not None:
        # talon-analyst checks it too ("Ask Talon about this alert"); any reason is the same answer.
        alert_customer = (await session.execute(select(Alert.customer_code).where(Alert.id == body.alert_id))).scalar_one_or_none()
        if alert_customer != body.customer_code:
            return coded("alert_not_found")
    language = await thread_language(user, session, body.language)
    await release(session)
    payload = {"customer_code": body.customer_code, "title": body.title, "alert_id": body.alert_id, "language": language}
    return answer(await v2_request("POST", "/v2/portal/threads", portal.identity, json_body=payload))


async def thread_language(user: User, session: AsyncSession, asked: Optional[str]) -> str:
    """A new thread's language: the one the portal shows when it is among the user's available
    portal languages (``available_for_user``), else the user's portal language (``portal_locale``).
    Never a value the server doesn't offer the user."""
    language, available = await portal_locale(user, session)
    return asked if isinstance(asked, str) and asked in available else language


async def _with_thread(user: User, session: AsyncSession, thread_id: str) -> Union[Tuple[Portal, str], JSONResponse]:
    canonical = object_id(thread_id)
    if canonical is None:
        return coded("thread_not_found")
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    await release(session)
    checked = await thread_customer(portal, canonical)
    if isinstance(checked, JSONResponse):
        return checked
    return portal, canonical


async def rename_thread(user: User, session: AsyncSession, thread_id: str, request: Request) -> Response:
    body = await read_body(request, ThreadRename)
    if isinstance(body, JSONResponse):
        return body
    checked = await _with_thread(user, session, thread_id)
    if isinstance(checked, JSONResponse):
        return checked
    portal, canonical = checked
    return answer(await v2_request("PATCH", f"/v2/portal/threads/{canonical}", portal.identity, json_body={"title": body.title}))


async def archive_thread(user: User, session: AsyncSession, thread_id: str) -> Response:
    checked = await _with_thread(user, session, thread_id)
    if isinstance(checked, JSONResponse):
        return checked
    portal, canonical = checked
    return answer(await v2_request("DELETE", f"/v2/portal/threads/{canonical}", portal.identity))


async def thread_messages(user: User, session: AsyncSession, thread_id: str, params: Dict[str, Any]) -> Response:
    """FR-API-37: the page asked for is the read-back that checks the thread's customer."""
    canonical = object_id(thread_id)
    if canonical is None:
        return coded("thread_not_found")
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    await release(session)
    checked = await thread_customer(portal, canonical, {k: v for k, v in params.items() if v is not None})
    if isinstance(checked, JSONResponse):
        return checked
    return relay(checked)


async def feedback(user: User, session: AsyncSession, thread_id: str, request: Request) -> Response:
    body = await read_body(request, Feedback)
    if isinstance(body, JSONResponse):
        return body
    checked = await _with_thread(user, session, thread_id)
    if isinstance(checked, JSONResponse):
        return checked
    portal, canonical = checked
    result = await v2_request("POST", f"/v2/portal/threads/{canonical}/feedback", portal.identity, json_body=body.model_dump())
    if result.status == 204:
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
    return answer(result)


# ── chat ──────────────────────────────────────────────────────────────────────


def message_text(body: Dict[str, Any]) -> Optional[Tuple[str, Optional[str]]]:
    """``(text, message id)`` from either body, or None. From a ``SubmitMessage``, only the newest
    message, which must be the user's, and only its text parts: everything else in the request is
    the browser's and never forwarded (talon-analyst ignores it too)."""
    try:
        own = ChatMessage.model_validate(body)
        return own.message, own.message_id
    except ValidationError:
        pass
    try:
        submit = SubmitMessage.model_validate(body)
    except ValidationError:
        return None
    newest = submit.messages[-1]
    if newest.role != "user":
        return None
    text = "".join(part.text for part in newest.parts if part.type == "text" and isinstance(part.text, str))
    for message_id in (newest.id, None):
        try:
            own = ChatMessage(message=text, message_id=message_id)
        except ValidationError:
            continue
        return own.message, own.message_id
    return None


def submit_message(thread_id: str, text: str, message_id: Optional[str]) -> Dict[str, Any]:
    """The ``SubmitMessage`` CoPilot sends talon-analyst, built here from the text alone."""
    return {
        "trigger": "submit-message",
        "id": thread_id,
        "messages": [{"id": message_id or f"copilot-{uuid.uuid4().hex}", "role": "user", "parts": [{"type": "text", "text": text}]}],
    }


async def chat(user: User, session: AsyncSession, thread_id: str, request: Request) -> Response:
    """FR-API-38: one portal turn, streamed through unchanged. Refused before the stream with a code."""
    raw = await read_json(request)
    if isinstance(raw, JSONResponse):
        return raw
    message = message_text(raw) if isinstance(raw, dict) else None
    if message is None:
        return coded("invalid_request")
    checked = await _with_thread(user, session, thread_id)
    if isinstance(checked, JSONResponse):
        return checked
    portal, canonical = checked
    opened = await open_v2_stream(f"/v2/portal/chat/{canonical}", portal.identity, submit_message(canonical, *message))
    if isinstance(opened, V2Answer):
        return relay_refusal(opened.status, opened.body)
    return V2StreamingResponse(opened)


# ── drafts ────────────────────────────────────────────────────────────────────


async def read_draft(portal: Portal, draft_id: str) -> Union[Tuple[V2Answer, Dict[str, Any]], JSONResponse]:
    """FR-API-39 as the user, then the draft's customer: the user's and switched on."""
    result = await v2_request("GET", f"/v2/portal/drafts/{draft_id}", portal.identity)
    draft = parsed(result)
    if draft is None:
        return coded("failed") if result.status is not None and 200 <= result.status < 300 else answer(result)
    customer_code = draft.get("customer_code")
    if not isinstance(customer_code, str) or customer_code not in portal.customers:
        return coded("draft_not_found")
    if customer_code not in portal.enabled:
        return coded("portal_off")
    return result, draft


async def get_draft(user: User, session: AsyncSession, draft_id: str) -> Response:
    canonical = object_id(draft_id)
    if canonical is None:
        return coded("draft_not_found")
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    await release(session)
    checked = await read_draft(portal, canonical)
    if isinstance(checked, JSONResponse):
        return checked
    return relay(checked[0])


async def discard_draft(user: User, session: AsyncSession, draft_id: str) -> Response:
    """FR-API-41 ``discarded``: the customer drops a draft (talon-analyst allows it from ``pending`` only)."""
    canonical = object_id(draft_id)
    if canonical is None:
        return coded("draft_not_found")
    portal = await begin(user, session)
    if isinstance(portal, JSONResponse):
        return portal
    await release(session)
    checked = await read_draft(portal, canonical)
    if isinstance(checked, JSONResponse):
        return checked
    return answer(await v2_request("POST", f"/v2/portal/drafts/{canonical}/outcome", portal.identity, json_body={"outcome": "discarded"}))
