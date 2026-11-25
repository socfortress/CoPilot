"""HTTP to sysmon-sync for the Sysmon noise statistics (client.py), against httpx.MockTransport.

Pinned: the exact method, path, headers and body of a report, a withdraw and the probe (which sends no license key);
every answer the README's "How CoPilot reports" names, classified; redirects never followed; capped and compressed
answers; Retry-After as seconds, an HTTP date or garbage; TLS verification never switched off; reason codes and field
names type-checked before they reach a log line.

Run with: cd backend && python -m pytest tests/test_sysmon_stats_client.py
"""
import asyncio
import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from email.utils import format_datetime

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.schema.sysmon_stats import StatsOutcome  # noqa: E402
from app.active_response.services.sysmon_stats import client as http  # noqa: E402

BASE = "https://sync.test"
KEY = "LICENSE-abcdef-0123456789-SECRET"
PAYLOAD = b'{"format":"socfortress-sysmon-report/1"}'


class Service:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    @property
    def transport(self):
        return httpx.MockTransport(self.handle)


def post(*answers, sleeps=None):
    service = Service(*answers)
    waits = sleeps if sleeps is not None else []

    async def sleep(seconds):
        waits.append(seconds)

    result = asyncio.run(http.post_report(BASE, PAYLOAD, KEY, service.transport, sleep=sleep))
    return result, service, waits


def j(status, body=None, headers=None):
    return httpx.Response(status, json=body if body is not None else {}, headers=headers)


def test_a_report_request_is_exactly_what_the_contract_asks():
    result, service, _ = post(
        j(
            200,
            {"result": "stored", "replaced": False, "patterns": {"received": 1, "accepted": 1, "rejected": 0}, "rejected_by_reason": {}},
        ),
    )
    assert result.outcome is StatsOutcome.SENT and result.terminal and result.accepted == 1 and result.replaced is False
    (request,) = service.requests
    assert request.method == "POST" and str(request.url) == f"{BASE}/v1/sysmon/report" and not request.url.query
    assert request.headers["authorization"] == f"Bearer {KEY}"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept-encoding"] == "identity"
    assert request.headers["user-agent"].startswith("SOCFortress-CoPilot/")
    assert "x-api-key" not in request.headers
    assert request.content == PAYLOAD


def test_the_probe_sends_no_license_key():
    for answer, verdict in (
        (j(404, {"detail": "reports are not enabled"}), http.Probe.NOT_ACCEPTING),
        (j(401, {"detail": "missing license key"}), http.Probe.ACCEPTING),
        (j(403, {"detail": "blocked by the firewall"}), http.Probe.UNKNOWN),
        (j(404, {"detail": "Not Found"}), http.Probe.UNKNOWN),
    ):
        service = Service(answer)
        assert asyncio.run(http.probe(BASE, service.transport)) == verdict
        (request,) = service.requests
        assert "authorization" not in request.headers and request.content == b"{}"
        assert str(request.url) == f"{BASE}/v1/sysmon/report"


STATUS_ROWS = [
    (j(400, {"detail": "bad", "reason": "invalid-json"}), StatsOutcome.REFUSED_BAD_REQUEST, True, False),
    (j(400, {"detail": "gone", "reason": "client-disconnect"}), StatsOutcome.NETWORK_ERROR, False, False),
    (j(401, {"detail": "missing license key"}), StatsOutcome.UNAUTHORIZED, False, True),
    (j(403, {"detail": "invalid or expired license"}), StatsOutcome.LICENSE_REJECTED, False, True),
    (j(403, {"detail": "reports from this license are refused"}), StatsOutcome.LICENSE_BLOCKED, False, True),
    (httpx.Response(403, text="<html>blocked</html>"), StatsOutcome.WAF_REFUSED, True, False),
    (j(404, {"detail": "reports are not enabled"}), StatsOutcome.SERVICE_NOT_ACCEPTING, False, True),
    (j(404, {"detail": "Not Found"}), StatsOutcome.HTTP_ERROR, False, True),
    (j(405, {}), StatsOutcome.HTTP_ERROR, False, True),
    (j(408, {"reason": "body-timeout"}), StatsOutcome.BODY_TIMEOUT, False, True),
    (j(409, {"reason": "withdrawn"}), StatsOutcome.WITHDRAWN, True, False),
    (j(413, {"reason": "too-large"}), StatsOutcome.TOO_LARGE, True, False),
    (j(415, {"reason": "content-type"}), StatsOutcome.REFUSED_CONTENT_TYPE, True, False),
    (j(422, {"reason": "week-not-accepted"}), StatsOutcome.WEEK_NOT_ACCEPTED, True, True),
    (j(422, {"reason": "week-before-first-seen"}), StatsOutcome.WEEK_BEFORE_FIRST_SEEN, True, True),
    (j(422, {"reason": "customer-limit"}), StatsOutcome.CUSTOMER_LIMIT, True, True),
    (j(422, {"reason": "storage-quota"}), StatsOutcome.STORAGE_QUOTA, True, True),
    (
        j(422, {"reason": "identity-leak", "patterns": [{"index": 3, "reason": "identity-leak", "field": "TargetFilename"}]}),
        StatsOutcome.REFUSED,
        True,
        True,
    ),
    (j(422, {"reason": "command-line", "patterns": [{"index": 0, "reason": "command-line"}]}), StatsOutcome.REFUSED, True, True),
    (j(422, {"reason": "field-not-allowed", "patterns": [{"index": 0, "reason": "field-not-allowed"}]}), StatsOutcome.REFUSED, True, True),
    (j(422, {"reason": "duplicate-pattern"}), StatsOutcome.REFUSED, True, False),
    (j(422, {"reason": "malformed"}), StatsOutcome.REFUSED, True, False),
    (j(429, {"reason": "rate-limit"}, {"Retry-After": "120"}), StatsOutcome.RATE_LIMITED, False, True),
    (j(503, {"reason": "license-unavailable"}, {"Retry-After": "300"}), StatsOutcome.SERVICE_UNAVAILABLE, False, True),
    (j(507, {"detail": "report storage full"}), StatsOutcome.STORAGE_FULL, False, True),
    (j(500, {"detail": "storage error"}), StatsOutcome.HTTP_ERROR, False, True),
    (j(502, {}), StatsOutcome.HTTP_ERROR, False, True),
    (httpx.ConnectError("refused"), StatsOutcome.NETWORK_ERROR, False, True),
]


@pytest.mark.parametrize("answer,outcome,terminal,stop", STATUS_ROWS, ids=[f"{i}-{row[1].value}" for i, row in enumerate(STATUS_ROWS)])
def test_every_answer_is_classified(answer, outcome, terminal, stop):
    result, _, _ = post(answer)
    assert result.outcome is outcome and result.terminal is terminal and result.stop is stop
    assert KEY not in result.message


def test_the_content_refusals_latch_and_the_week_wide_ones_mark_the_week():
    result, _, _ = post(
        j(
            422,
            {
                "reason": "identity-leak",
                "patterns": [
                    {"index": 3, "reason": "identity-leak", "field": "TargetFilename"},
                    {"index": "x"},
                    {"index": 4, "reason": "Bad Reason!", "field": "Secret"},
                ],
            },
        ),
    )
    assert result.latch and result.problems == [
        {"index": 3, "reason": "identity-leak", "field": "TargetFilename"},
        {"index": 4, "reason": "unknown"},
    ]
    assert post(j(422, {"reason": "customer-limit"}))[0].week_wide
    assert not post(j(422, {"reason": "malformed"}))[0].latch
    assert post(httpx.ConnectError("x"))[0].uncertain


def test_a_200_with_dropped_patterns_is_success_and_reported():
    body = {
        "result": "stored",
        "replaced": True,
        "week": "2026-W47",
        "patterns": {"received": 3, "accepted": 2, "rejected": 1},
        "rejected_by_reason": {"look-alike": 1, "Not A Reason": 3},
        "rejected_patterns": [{"index": 1, "reason": "look-alike", "field": "Image"}],
    }
    result, _, _ = post(j(200, body))
    assert result.outcome is StatsOutcome.SENT and result.rejected == 1 and result.replaced is True
    assert result.rejected_by_reason == {"look-alike": 1}


def test_in_progress_is_retried_once_and_busy_twice():
    stored = j(200, {"result": "stored", "patterns": {"accepted": 0, "rejected": 0}})
    result, service, waits = post(j(429, {"reason": "in-progress"}, {"Retry-After": "5"}), stored)
    assert result.outcome is StatsOutcome.SENT and len(service.requests) == 2 and waits == [5]
    result, service, waits = post(j(429, {"reason": "in-progress"}, {"Retry-After": "60"}))
    assert result.outcome is StatsOutcome.BUSY and len(service.requests) == 2 and waits == [10]
    result, service, waits = post(j(503, {"reason": "busy"}, {"Retry-After": "30"}))
    assert result.outcome is StatsOutcome.BUSY and len(service.requests) == 3 and waits == [30, 30]


def test_retry_after_parsing():
    now = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)
    assert http.retry_after("120", 300, now) == 120
    assert http.retry_after("0", 300, now) == 1
    assert http.retry_after("999999", 300, now) == 86400
    assert http.retry_after(format_datetime(now + timedelta(minutes=10), usegmt=True), 300, now) == 600
    assert http.retry_after("soon", 300, now) == 300
    assert http.retry_after(None, 3600, now) == 3600
    result, _, _ = post(j(429, {"reason": "rate-limit"}, {"Retry-After": "garbage"}))
    assert result.service_retry_seconds == 3600
    result, _, _ = post(j(503, {}))
    assert result.service_retry_seconds == 300


def test_a_redirect_is_never_followed():
    result, service, _ = post(httpx.Response(307, headers={"Location": f"{BASE}/v1/sysmon/report2"}))
    assert result.outcome is StatsOutcome.REDIRECT_REFUSED and len(service.requests) == 1


def test_compressed_and_oversized_answers_are_not_read():
    gz = httpx.Response(200, content=b"\x1f\x8b", headers={"Content-Encoding": "gzip"})
    result, _, _ = post(gz)
    assert result.outcome is StatsOutcome.HTTP_ERROR
    big = httpx.Response(200, content=b"{" + b" " * (70 * 1024) + b"}")
    assert post(big)[0].outcome is StatsOutcome.HTTP_ERROR


def test_tls_verification_is_never_switched_off(monkeypatch):
    seen = []
    real = httpx.AsyncClient

    class Spy(real):
        def __init__(self, *args, **kwargs):
            seen.append(kwargs)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(http.httpx, "AsyncClient", Spy)
    post(j(200, {"result": "stored"}))
    service = Service(j(200, {"result": "withdrawn", "reports_deleted": 1}))
    asyncio.run(http.post_withdraw(BASE, "cust_" + "0" * 32, KEY, service.transport))
    asyncio.run(http.probe(BASE, Service(j(401)).transport))
    assert len(seen) == 3
    for kwargs in seen:
        assert kwargs.get("verify", True) is True and kwargs["follow_redirects"] is False
        assert kwargs["timeout"] == httpx.Timeout(30.0, connect=10.0)


def test_an_answer_that_never_completes_hits_the_deadline(monkeypatch):
    monkeypatch.setattr(http.settings, "REPORT_DEADLINE", 0.05)

    async def slow(request):
        await asyncio.sleep(1)
        return j(200)

    result = asyncio.run(http.post_report(BASE, PAYLOAD, KEY, httpx.MockTransport(slow)))
    assert result.outcome is StatsOutcome.NETWORK_ERROR and result.uncertain


def test_an_unusable_url_sends_nothing():
    service = Service(j(200))
    for base in ("http://sync.test", "https://user:pw@sync.test", "https://sync.test?x=1", "not a url"):
        result = asyncio.run(http.post_report(base, PAYLOAD, KEY, service.transport))
        assert result.outcome is StatsOutcome.ERROR
    assert service.requests == []
    assert http.settings.endpoint_url("http://127.0.0.1:8080", "/v1/sysmon/report")[0] == "http://127.0.0.1:8080/v1/sysmon/report"


# ── withdraw ────────────────────────────────────────────────────────────────

CUST = "cust_" + "1" * 32


def withdraw(*answers):
    service = Service(*answers)
    return asyncio.run(http.post_withdraw(BASE, CUST, KEY, service.transport)), service


def test_a_withdraw_request_is_exactly_what_the_contract_asks():
    result, service = withdraw(j(200, {"result": "withdrawn", "scope": "customer", "reports_deleted": 2}))
    assert result.withdrawn and result.reports_deleted == 2
    (request,) = service.requests
    assert str(request.url) == f"{BASE}/v1/sysmon/report/withdraw" and request.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(request.content) == {"format": "socfortress-sysmon-withdraw/1", "customer": CUST}
    assert len(request.content) <= 4096


@pytest.mark.parametrize(
    "answer,bug,stop,retry",
    [
        (j(400, {"reason": "invalid-json"}), True, False, None),
        (j(422, {"reason": "malformed"}), True, False, None),
        (j(401), False, True, None),
        (j(403, {"detail": "invalid or expired license"}), False, True, None),
        (j(404, {"detail": "Not Found"}), False, True, None),
        (j(408), False, True, None),
        (j(429, {}, {"Retry-After": "90"}), False, True, 90),
        (j(503, {}), False, True, 300),
        (j(500), False, True, None),
        (httpx.ConnectError("refused"), False, True, None),
    ],
)
def test_a_withdraw_that_is_not_confirmed_stays_queued(answer, bug, stop, retry):
    result, _ = withdraw(answer)
    assert not result.withdrawn and result.bug is bug and result.stop is stop and result.retry_seconds == retry
