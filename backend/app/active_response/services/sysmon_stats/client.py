"""HTTP to sysmon-sync: the unauthenticated probe, a report, a withdraw, and what each answer means.

The same conventions as the default sync's pull (services/sysmon_default_sync.py): TLS verified (httpx's default, never
switched off), 10 s to connect and 30 s per read or write, a deadline for the whole exchange, answers read capped and
only uncompressed, and no redirect is ever followed, so the license key only goes to the configured host. The license
key goes in ``Authorization: Bearer`` (which proxies redact from their logs) and nowhere else: never in a log line, the
state or an audit row, where only its fingerprint appears.

Nothing in a log line or a message built here carries a value of a report: only status codes, reason codes (checked
against the contract's grammar), pattern indexes and allow-listed field names.
"""
import asyncio
import json
import re
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import List
from typing import Optional

import httpx

from app.active_response.schema.sysmon_stats import StatsOutcome
from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats.contract_v1 import ALLOW_LISTED
from app.active_response.services.sysmon_stats.contract_v1 import WITHDRAW_FORMAT
from app.version.services.version import CURRENT_VERSION

REASON_RE = re.compile(r"[a-z][a-z0-9-]{0,39}")
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
# A report the service refused for what was in it: CoPilot's redaction has a gap, so every report pauses (D6)
LATCH_REASONS = frozenset({"identity-leak", "command-line", "field-not-allowed"})
# The rest of the week is not sent either: the answer would be the same for every customer
WEEK_WIDE_REASONS = {
    "week-not-accepted": StatsOutcome.WEEK_NOT_ACCEPTED,
    "week-before-first-seen": StatsOutcome.WEEK_BEFORE_FIRST_SEEN,
    "customer-limit": StatsOutcome.CUSTOMER_LIMIT,
    "storage-quota": StatsOutcome.STORAGE_QUOTA,
}
IN_PROGRESS_MAX_WAIT = 10
BUSY_MAX_WAIT = 30
BUSY_RETRIES = 2


class Probe:
    ACCEPTING = "accepting"
    NOT_ACCEPTING = "not_accepting"
    UNKNOWN = "unknown"


@dataclass
class Answer:
    """One HTTP exchange: the status (None: no answer), the parsed JSON body (when it was JSON), the headers."""

    status: Optional[int]
    body: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ReportResult:
    """What a report attempt means for the customer's week, the tick and the pause."""

    outcome: StatsOutcome
    terminal: bool
    stop: bool = False
    http_status: Optional[int] = None
    reason: Optional[str] = None
    message: str = ""
    accepted: Optional[int] = None
    rejected: Optional[int] = None
    rejected_by_reason: Dict[str, int] = field(default_factory=dict)
    replaced: Optional[bool] = None
    problems: List[Dict[str, Any]] = field(default_factory=list)
    latch: bool = False
    week_wide: bool = False
    customer_retry_seconds: Optional[int] = None
    service_retry_seconds: Optional[int] = None
    # Whether it may have arrived (no answer): audited as "unknown"
    uncertain: bool = False


def headers(license_key: Optional[str]) -> Dict[str, str]:
    out = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": f"SOCFortress-CoPilot/{CURRENT_VERSION}",
    }
    if license_key:
        out["Authorization"] = f"Bearer {license_key}"
    return out


async def _raw(response: httpx.Response) -> AsyncIterator[bytes]:
    if response.is_stream_consumed:
        yield response.content
        return
    async for chunk in response.aiter_raw():
        yield chunk


async def _read_answer(response: httpx.Response) -> Optional[bytes]:
    """The answer's bytes, at most MAX_ANSWER_BYTES; None when it is compressed or larger."""
    encodings = [t.strip().lower() for v in response.headers.get_list("content-encoding") for t in v.split(",")]
    if any(e not in ("", "identity") for e in encodings):
        return None
    body = bytearray()
    async for chunk in _raw(response):
        body.extend(chunk)
        if len(body) > settings.MAX_ANSWER_BYTES:
            return None
    return bytes(body)


async def _post(url: str, body: bytes, hdrs: Dict[str, str], deadline: float, transport: Optional[httpx.AsyncBaseTransport]) -> Answer:
    try:
        async with asyncio.timeout(deadline):
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT, follow_redirects=False, transport=transport) as client:
                async with client.stream("POST", url, content=body, headers=hdrs) as response:
                    raw = await _read_answer(response)
                    parsed = None
                    if raw:
                        try:
                            value = json.loads(raw)
                            parsed = value if isinstance(value, dict) else None
                        except (ValueError, UnicodeDecodeError):
                            parsed = None
                    kept = {k.lower(): v for k, v in response.headers.items() if k.lower() in ("retry-after", "location")}
                    return Answer(status=response.status_code, body=parsed, headers=kept)
    except TimeoutError:
        return Answer(status=None, error=f"no complete answer within {deadline:g} s")
    except httpx.HTTPError as e:
        return Answer(status=None, error=type(e).__name__)


async def probe(base: str, transport: Optional[httpx.AsyncBaseTransport] = None) -> str:
    """Whether the service accepts reports, asked without a license key and with an empty body: it answers 404 "reports
    are not enabled" before any authentication while reports are off, and 401 once they are on. No credential and no
    data leaves this CoPilot."""
    url, error = settings.endpoint_url(base, settings.REPORT_PATH)
    if url is None:
        return Probe.UNKNOWN
    answer = await _post(url, b"{}", headers(None), settings.PROBE_DEADLINE, transport)
    if answer.status == 404 and (answer.body or {}).get("detail") == settings.NOT_ENABLED_DETAIL:
        return Probe.NOT_ACCEPTING
    if answer.status == 401:
        return Probe.ACCEPTING
    return Probe.UNKNOWN


def retry_after(value: Optional[str], default: int, now: Optional[datetime] = None) -> int:
    """Retry-After as whole seconds (1..86400) or an HTTP date; else the default."""
    if value:
        text = value.strip()
        if text.isdigit():
            return max(1, min(86400, int(text)))
        try:
            moment = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            moment = None
        if moment is not None:
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            seconds = int((moment - (now or datetime.now(timezone.utc))).total_seconds())
            return max(1, min(86400, seconds))
    return default


def _reason(body: Optional[Dict[str, Any]]) -> Optional[str]:
    value = (body or {}).get("reason")
    if value is None:
        return None
    return value if isinstance(value, str) and REASON_RE.fullmatch(value) else "unknown"


def _problems(entries: Any) -> List[Dict[str, Any]]:
    """The 422's or 200's pattern problems, type-checked: an int index, a reason in the contract's grammar, a field only
    when it is allow-listed."""
    out: List[Dict[str, Any]] = []
    if not isinstance(entries, list):
        return out
    for entry in entries[:70]:
        if not isinstance(entry, dict):
            continue
        index = entry.get("index")
        if type(index) is not int:
            continue
        reason = entry.get("reason")
        problem: Dict[str, Any] = {
            "index": index,
            "reason": reason if isinstance(reason, str) and REASON_RE.fullmatch(reason) else "unknown",
        }
        name = entry.get("field")
        if isinstance(name, str) and (name in ALLOW_LISTED or name == "rule_name"):
            problem["field"] = name
        out.append(problem)
    return out


def _counts(value: Any) -> Dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items() if isinstance(k, str) and REASON_RE.fullmatch(k) and type(v) is int}


def _int(value: Any) -> Optional[int]:
    return value if type(value) is int else None


def classify_report(answer: Answer) -> ReportResult:
    """What a report's answer means (README, "How CoPilot reports")."""
    status, body = answer.status, answer.body or {}
    reason = _reason(body)
    detail = body.get("detail") if isinstance(body.get("detail"), str) else None

    def r(outcome: StatsOutcome, terminal: bool, message: str, **kw) -> ReportResult:
        return ReportResult(outcome=outcome, terminal=terminal, http_status=status, reason=reason, message=message, **kw)

    if status is None:
        return r(
            StatsOutcome.NETWORK_ERROR,
            False,
            f"No answer from the SOCFortress service ({answer.error or 'network error'}); the report may have arrived.",
            stop=True,
            uncertain=True,
        )
    if status == 200 and body.get("result") == "stored":
        patterns = body.get("patterns") if isinstance(body.get("patterns"), dict) else {}
        return r(
            StatsOutcome.SENT,
            True,
            "Stored by SOCFortress.",
            accepted=_int(patterns.get("accepted")),
            rejected=_int(patterns.get("rejected")),
            rejected_by_reason=_counts(body.get("rejected_by_reason")),
            replaced=body.get("replaced") if isinstance(body.get("replaced"), bool) else None,
            problems=_problems(body.get("rejected_patterns")),
        )
    if status in _REDIRECTS:
        return r(StatsOutcome.REDIRECT_REFUSED, False, f"The SOCFortress service redirected (HTTP {status}): not followed.", stop=True)
    if status == 400:
        if reason == "client-disconnect":
            return r(StatsOutcome.NETWORK_ERROR, False, "The SOCFortress service saw the connection drop (HTTP 400).")
        return r(StatsOutcome.REFUSED_BAD_REQUEST, True, f"SOCFortress refused the request (HTTP 400, {reason or 'no reason'}).")
    if status == 401:
        return r(StatsOutcome.UNAUTHORIZED, False, "The SOCFortress service got no license key (HTTP 401).", stop=True)
    if status == 403:
        if detail == "invalid or expired license":
            return r(StatsOutcome.LICENSE_REJECTED, False, "SOCFortress rejected this CoPilot's license (HTTP 403).", stop=True)
        if detail == "reports from this license are refused":
            return r(StatsOutcome.LICENSE_BLOCKED, False, "SOCFortress refuses reports from this license (HTTP 403).", stop=True)
        return r(StatsOutcome.WAF_REFUSED, True, "The SOCFortress firewall refused the report (HTTP 403); this week is skipped.")
    if status == 404:
        if detail == settings.NOT_ENABLED_DETAIL:
            return r(StatsOutcome.SERVICE_NOT_ACCEPTING, False, "SOCFortress is not accepting noise reports yet.", stop=True)
        return r(StatsOutcome.HTTP_ERROR, False, "The SOCFortress service has no report route (HTTP 404).", stop=True)
    if status == 405:
        return r(StatsOutcome.HTTP_ERROR, False, "The SOCFortress service refused the method (HTTP 405).", stop=True)
    if status == 408:
        return r(
            StatsOutcome.BODY_TIMEOUT,
            False,
            "The SOCFortress service did not get the report in time (HTTP 408).",
            stop=True,
            customer_retry_seconds=900,
        )
    if status == 409 and reason == "withdrawn":
        return r(StatsOutcome.WITHDRAWN, True, "SOCFortress dropped the report: this customer's reports were withdrawn (HTTP 409).")
    if status == 413:
        return r(StatsOutcome.TOO_LARGE, True, "SOCFortress refused the report as too large (HTTP 413).")
    if status == 415:
        return r(StatsOutcome.REFUSED_CONTENT_TYPE, True, "SOCFortress refused the content type (HTTP 415).")
    if status == 422:
        problems = _problems(body.get("patterns"))
        if reason in WEEK_WIDE_REASONS:
            return r(
                WEEK_WIDE_REASONS[reason],
                True,
                f"SOCFortress refused the report ({reason}).",
                stop=True,
                week_wide=True,
                problems=problems,
            )
        if reason in LATCH_REASONS:
            return r(
                StatsOutcome.REFUSED,
                True,
                f"SOCFortress refused the report for its content ({reason}): reports are paused until CoPilot is updated or an admin resumes them.",
                stop=True,
                latch=True,
                problems=problems,
            )
        return r(StatsOutcome.REFUSED, True, f"SOCFortress refused the report ({reason or 'no reason'}).", problems=problems)
    if status == 429:
        if reason == "in-progress":
            return r(StatsOutcome.BUSY, False, "SOCFortress is still processing another report of this license (HTTP 429).", stop=True)
        return r(
            StatsOutcome.RATE_LIMITED,
            False,
            "SOCFortress is rate-limiting this CoPilot's reports (HTTP 429).",
            stop=True,
            service_retry_seconds=retry_after(answer.headers.get("retry-after"), 3600),
        )
    if status == 503:
        if reason == "busy":
            return r(StatsOutcome.BUSY, False, "SOCFortress is busy (HTTP 503).", stop=True)
        return r(
            StatsOutcome.SERVICE_UNAVAILABLE,
            False,
            "The SOCFortress service is unavailable (HTTP 503).",
            stop=True,
            service_retry_seconds=retry_after(answer.headers.get("retry-after"), 300),
        )
    if status == 507:
        return r(
            StatsOutcome.STORAGE_FULL,
            False,
            "SOCFortress's report storage is full (HTTP 507).",
            stop=True,
            service_retry_seconds=3600,
        )
    return r(StatsOutcome.HTTP_ERROR, False, f"The SOCFortress service answered HTTP {status}.", stop=True)


async def post_report(
    base: str,
    payload: bytes,
    license_key: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
    sleep=asyncio.sleep,
) -> ReportResult:
    """Send one report (the exact bytes, at once) and classify the answer. 429 "in-progress" is retried once after its
    Retry-After (at most 10 s), 503 "busy" at most twice (at most 30 s each)."""
    url, error = settings.endpoint_url(base, settings.REPORT_PATH)
    if url is None:
        return ReportResult(outcome=StatsOutcome.ERROR, terminal=False, stop=True, message=error or "invalid URL")
    busy_retries = 0
    in_progress_retried = False
    while True:
        answer = await _post(url, payload, headers(license_key), settings.REPORT_DEADLINE, transport)
        result = classify_report(answer)
        reason = result.reason
        if answer.status == 429 and reason == "in-progress" and not in_progress_retried:
            in_progress_retried = True
            await sleep(min(IN_PROGRESS_MAX_WAIT, retry_after(answer.headers.get("retry-after"), 5)))
            continue
        if answer.status == 503 and reason == "busy" and busy_retries < BUSY_RETRIES:
            busy_retries += 1
            await sleep(min(BUSY_MAX_WAIT, retry_after(answer.headers.get("retry-after"), 30)))
            continue
        return result


@dataclass
class WithdrawResult:
    withdrawn: bool
    http_status: Optional[int]
    reports_deleted: Optional[int] = None
    retry_seconds: Optional[int] = None
    stop: bool = False
    bug: bool = False
    message: str = ""


def withdraw_body(customer: str) -> bytes:
    return json.dumps({"format": WITHDRAW_FORMAT, "customer": customer}, separators=(",", ":")).encode("ascii")


async def post_withdraw(
    base: str,
    customer: str,
    license_key: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> WithdrawResult:
    """Ask SOCFortress to delete every stored report of one customer pseudonym."""
    url, error = settings.endpoint_url(base, settings.WITHDRAW_PATH)
    if url is None:
        return WithdrawResult(False, None, stop=True, message=error or "invalid URL")
    answer = await _post(url, withdraw_body(customer), headers(license_key), settings.WITHDRAW_DEADLINE, transport)
    body = answer.body or {}
    if answer.status == 200 and body.get("result") == "withdrawn":
        deleted = body.get("reports_deleted")
        return WithdrawResult(True, 200, reports_deleted=deleted if type(deleted) is int else None, message="Withdrawn.")
    if answer.status in (400, 422):
        return WithdrawResult(False, answer.status, bug=True, message=f"SOCFortress refused the withdraw (HTTP {answer.status}).")
    if answer.status is None:
        return WithdrawResult(False, None, stop=True, message=f"No answer from the SOCFortress service ({answer.error}).")
    default = 3600 if answer.status == 429 else 300
    return WithdrawResult(
        False,
        answer.status,
        stop=True,
        retry_seconds=retry_after(answer.headers.get("retry-after"), default) if answer.status in (429, 503) else None,
        message=f"The SOCFortress service answered HTTP {answer.status} to the withdraw.",
    )
