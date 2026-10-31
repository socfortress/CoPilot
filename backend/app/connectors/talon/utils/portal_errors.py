"""The machine-coded errors of Talon portal chat (talon-analyst SPEC §8 "Portal chat API" Errors, D97).

Every error answer of CoPilot's portal chat, review and meter routes is ``{"detail": <text>, "code":
<code>}`` at the top level (not FastAPI's ``HTTPException`` body, which CoPilot's handler turns into
``{"success": false, "message": …}``), with a code from talon-analyst's fixed table, so the portal
localizes by ``code`` and the text is only the English fallback. The texts are fixed and never echo
input.

talon-analyst's own refusals pass through with their status and code (``relay_refusal``). Only a
code from the table is passed on; anything else (no answer, CoPilot's API key refused, a 5xx
without a known code, a body that isn't the expected shape) is CoPilot's ``failed``.
"""
import json
from typing import Dict
from typing import Optional
from typing import Tuple

from fastapi.responses import JSONResponse
from loguru import logger

#: code -> (HTTP status, English text). The chunk-only and tool-result codes are listed so both sides
#: use one table; CoPilot itself answers only the HTTP ones.
ERRORS: Dict[str, Tuple[int, str]] = {
    "invalid_request": (422, "invalid request"),
    "invalid_headers": (400, "invalid identity headers"),
    "not_portal_role": (403, "this route is for portal users"),
    "portal_role_refused": (403, "this route isn't available to portal users"),
    "customer_not_accessible": (403, "customer not accessible"),
    "portal_off": (403, "portal chat is turned off for this customer"),
    "settings_unavailable": (503, "portal chat settings can't be read right now"),
    "thread_not_found": (404, "thread not found"),
    "thread_archived": (409, "this thread is archived"),
    "access_removed": (403, "access to this thread's customer was removed"),
    "thread_limit": (409, "too many open conversations; close one first"),
    "new_thread_limit": (409, "too many new conversations today"),
    "alert_not_found": (404, "alert not found"),
    "body_too_large": (413, "the request is too large"),
    "message_too_long": (413, "the message is too long"),
    "busy_thread": (409, "a reply is still streaming"),
    "busy_user": (409, "you already have a reply streaming"),
    "busy": (429, "too many replies are streaming, try again shortly"),
    "turn_limit": (429, "the reply reached its limit"),
    "timeout": (504, "the reply took too long"),
    "budget_customer": (429, "budget exhausted: the customer's daily budget (or monthly)"),
    "budget_portal": (429, "budget exhausted: the daily portal chat budget"),
    "budget_portal_user": (429, "budget exhausted: your daily portal chat budget"),
    "messages_customer": (429, "the daily message limit for portal chat is reached"),
    "messages_user": (429, "your daily message limit for portal chat is reached"),
    "budget_unavailable": (503, "refused: budget check unavailable"),
    "failed": (502, "Talon request failed"),
    "draft_not_found": (404, "draft not found"),
    "draft_expired": (409, "this draft expired"),
    "draft_conflict": (409, "this draft was already decided"),
    "read_only": (403, "this account can view this customer's data but not change it"),
    "review_forbidden": (403, "you can't review this customer's portal chats"),
    "soc_requests_off": (403, "questions to the SOC are turned off for this customer"),
    "soc_request_limit": (429, "the daily limit of questions to the SOC is reached"),
    "soc_request_cooldown": (429, "a question was just sent about this; try again in a few minutes"),
    "invalid_question": (422, "the question can't be sent as it is"),
    "not_found": (404, "the alert or case was not found"),
    "internal_failure": (500, "the question couldn't be sent; try again"),
    "ioc_off": (403, "threat-intel lookups are off for this customer"),
    "ioc_in_progress": (409, "this indicator is being checked already; try again in a moment"),
    "ioc_limit": (429, "today's threat-intel lookups are used up"),
}

#: Every coded answer is the caller's own and must not be kept by a browser or a proxy.
NO_STORE = {"Cache-Control": "no-store"}
#: The longest talon-analyst ``detail`` passed on as it is (its texts are short and fixed).
MAX_DETAIL_CHARS = 200


def text_of(code: str) -> str:
    return ERRORS[code][1]


def status_of(code: str) -> int:
    return ERRORS[code][0]


def coded(code: str, status: Optional[int] = None) -> JSONResponse:
    """CoPilot's own refusal: ``{detail, code}`` with the table's text and status."""
    default_status, text = ERRORS[code]
    return JSONResponse({"detail": text, "code": code}, status_code=status or default_status, headers=NO_STORE)


def _talon_error(body: bytes) -> Optional[Tuple[str, str]]:
    """``(detail, code)`` of a talon-analyst error body, when it is one of the table's codes."""
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):  # ValueError includes UnicodeDecodeError
        return None
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    if not isinstance(code, str) or code not in ERRORS:
        return None
    detail = payload.get("detail")
    # talon-analyst's text is the table's; a different or odd one is replaced by the table's.
    if not isinstance(detail, str) or not detail.isprintable() or not 0 < len(detail) <= MAX_DETAIL_CHARS:
        detail = text_of(code)
    return detail, code


def relay_refusal(status: Optional[int], body: bytes) -> JSONResponse:
    """A talon-analyst answer that isn't a 2xx, as CoPilot's: its status and coded body, or ``failed``.

    Never a 401: that is CoPilot's API key refused, an operator's problem, and the portal reads a 401
    as its own session ending."""
    if status is None:
        return coded("failed")
    if status == 401:
        logger.error("Talon portal chat: talon-analyst refused CoPilot's API key (401)")
        return coded("failed")
    if not 400 <= status < 600:
        logger.error(f"Talon portal chat: unexpected upstream status {status}")
        return coded("failed")
    known = _talon_error(body)
    if known is None:
        logger.error(f"Talon portal chat: talon-analyst answered {status} without a known code")
        if status >= 500:
            return coded("failed")
        return JSONResponse({"detail": text_of("failed"), "code": "failed"}, status_code=status, headers=NO_STORE)
    detail, code = known
    return JSONResponse({"detail": detail, "code": code}, status_code=status, headers=NO_STORE)
