"""CoPilot's client for copilot-prowler, and the module's pure helpers (#1328).

Pinned here: nothing is sent without a token of at least 32 characters or to a URL with a user,
query or fragment; every runner failure becomes a reason of CoPilot's (a runner's 401 is
``token_rejected``, never passed on); a compressed body is refused before it is inflated; bodies are
capped; a job id that isn't the runner's shape never reaches a URL; schedules and times read right.
"""

import asyncio
import gzip
import json
from datetime import datetime

import httpx
import pytest

from app.cloud_assessment import utils
from app.cloud_assessment.services import runner_client
from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerError

TOKEN = "k" * 32


def client(handler, token=TOKEN, url="http://runner.test") -> RunnerClient:
    return RunnerClient(url, token, transport=httpx.MockTransport(handler))


def call(coroutine_factory, handler, **kwargs):
    async def inner():
        async with client(handler, **kwargs) as runner:
            return await coroutine_factory(runner)

    return asyncio.run(inner())


def reason(coroutine_factory, handler, **kwargs) -> RunnerError:
    with pytest.raises(RunnerError) as error:
        call(coroutine_factory, handler, **kwargs)
    return error.value


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (401, "unauthorized", "token_rejected"),
        (503, "not_configured", "runner_not_configured"),
        (429, "busy", "busy"),
        (429, "too_many_jobs", "busy"),
        (404, "not_found", "not_found"),
        (422, "invalid_request", "refused"),
        (400, "tenant_domain_required", "refused"),
        (500, "internal", "bad_response"),
        (502, None, "bad_response"),
    ],
)
def test_every_runner_failure_has_a_reason_of_copilot_s(status, code, expected):
    error = reason(lambda r: r.health(), lambda request: httpx.Response(status, json={"detail": "x", "code": code} if code else None))
    assert error.reason == expected and (error.code == code or code is None)


def test_nothing_is_sent_without_a_long_enough_token():
    sent = []
    error = reason(lambda r: r.health(), lambda request: sent.append(request) or httpx.Response(200), token="short")
    assert error.reason == "not_configured" and sent == []


@pytest.mark.parametrize("url", ["ftp://runner", "http://user:pass@runner", "http://runner?x=1", "http://runner#f", "runner:8080", ""])
def test_a_runner_url_with_more_than_a_host_is_refused(url, monkeypatch):
    monkeypatch.setenv(runner_client.URL_ENV, url)
    monkeypatch.setenv(runner_client.TOKEN_ENV, TOKEN)
    found = RunnerClient.from_env()
    if url:
        assert found.problem() == "bad_url"
    else:
        assert found.base_url == runner_client.DEFAULT_URL  # unset: the compose service
    asyncio.run(found.__aexit__(None, None, None))


def test_the_token_is_sent_and_the_body_asked_for_uncompressed():
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return httpx.Response(
            200,
            json={
                "runner_version": "0.1.0",
                "prowler_version": "5.52.0",
                "powershell": True,
                "providers": ["aws", "evil"],
                "max_concurrent": 2,
                "running": 0,
            },
        )

    health = call(lambda r: r.health(), handler)
    assert seen["authorization"] == f"Bearer {TOKEN}" and seen["accept-encoding"] == "identity"
    assert health["providers"] == ["aws"]


def test_a_compressed_body_is_refused_before_it_is_inflated():
    bomb = gzip.compress(b"{" + b" " * 10_000_000 + b"}")
    error = reason(lambda r: r.health(), lambda request: httpx.Response(200, content=bomb, headers={"content-encoding": "gzip"}))
    assert error.reason == "bad_response"


def test_a_body_past_its_cap_is_refused(monkeypatch):
    monkeypatch.setattr(runner_client, "MAX_JSON_BYTES", 100)
    error = reason(lambda r: r.health(), lambda request: httpx.Response(200, json={"padding": "x" * 1000}))
    assert error.reason == "bad_response"


def test_unreachable_and_slow_runners_are_named():
    def refused(request):
        raise httpx.ConnectError("refused")

    def slow(request):
        raise httpx.ReadTimeout("slow")

    assert reason(lambda r: r.health(), refused).reason == "unreachable"
    assert reason(lambda r: r.health(), slow).reason == "timeout"


@pytest.mark.parametrize("job_id", ["../health", "A" * 32, "a" * 31, "a" * 32 + "/x"])
def test_a_job_id_that_isn_t_the_runner_s_shape_never_reaches_a_url(job_id):
    sent = []
    error = reason(lambda r: r.scan_status(job_id), lambda request: sent.append(request) or httpx.Response(200))
    assert error.reason == "not_found" and sent == []


def test_a_malformed_job_answer_is_refused():
    error = reason(lambda r: r.scan_status("a" * 32), lambda request: httpx.Response(200, json={"job_id": "a" * 32, "status": "exploded"}))
    assert error.reason == "bad_response"


def test_a_job_answer_for_another_job_is_refused():
    def handler(request):
        return httpx.Response(200, json={"job_id": "b" * 32, "status": "running"})

    assert reason(lambda r: r.scan_status("a" * 32), handler).reason == "bad_response"


def test_findings_are_read_a_line_at_a_time():
    lines = [json.dumps({"n": index}) for index in range(5)] + ["not json", ""]

    async def read(runner):
        async with runner.findings("a" * 32) as items:
            return [item async for item in items]

    found = call(read, lambda request: httpx.Response(200, content=("\n".join(lines)).encode()))
    assert found == [{"n": 0}, {"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}, None]


def test_a_findings_line_past_its_cap_is_refused(monkeypatch):
    monkeypatch.setattr(runner_client, "MAX_FINDING_LINE_BYTES", 50)

    async def read(runner):
        async with runner.findings("a" * 32) as items:
            return [item async for item in items]

    assert reason(read, lambda request: httpx.Response(200, content=b"x" * 500)).reason == "bad_response"


def test_deleting_a_job_the_runner_forgot_is_fine():
    assert call(lambda r: r.delete_scan("a" * 32), lambda request: httpx.Response(404, json={"detail": "x", "code": "not_found"})) is None


def test_the_compliance_catalog_is_kept_an_hour():
    runner_client.clear_catalog_cache()
    asked = []

    def handler(request):
        asked.append(request.url.path)
        return httpx.Response(200, json={"frameworks": []})

    async def twice(runner):
        await runner.compliance_catalog("aws")
        return await runner.compliance_catalog("aws")

    call(twice, handler)
    assert asked == ["/v1/compliance/aws"]
    runner_client.clear_catalog_cache()


# --- utils ----------------------------------------------------------------------------------------


def test_clean_text_drops_controls_replaces_surrogates_and_cuts():
    assert utils.clean_text("a\x00b\x1bc\x7fd\x9fe\tf\ng", 100) == "abcde\tf\ng"
    assert utils.clean_text("x\ud800y", 10) == "x�y"
    assert utils.clean_text("abcdef", 4) == "abc…"
    assert utils.clean_text(None, 4) == "" and utils.clean_text(True, 4) == "" and utils.clean_text(12, 4) == "12"


def test_only_http_urls_without_whitespace_are_links():
    assert utils.url_list(
        ["https://a.example/x", "http://b.example", "javascript:alert(1)", "https://c.example/a b", "https://a.example/x"],
    ) == [
        "https://a.example/x",
        "http://b.example",
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-23T10:00:00Z", datetime(2026, 11, 23, 10, 0)),
        ("2026-11-23T10:00:00.123456", datetime(2026, 11, 23, 10, 0, 0, 123456)),
        ("2026-11-23T12:00:00+02:00", datetime(2026, 11, 23, 10, 0)),
        ("yesterday", None),
        (12, None),
    ],
)
def test_prowler_times_are_read_as_utc(value, expected):
    assert utils.parse_time(value) == expected


NOW = datetime(2026, 11, 25, 10, 30)  # a Wednesday


def test_daily_and_weekly_slots():
    assert utils.last_slot("daily", 2, None, NOW) == datetime(2026, 11, 25, 2, 0)
    assert utils.last_slot("daily", 11, None, NOW) == datetime(2026, 11, 24, 11, 0)
    assert utils.last_slot("weekly", 2, 0, NOW) == datetime(2026, 11, 23, 2, 0)  # Monday
    assert utils.last_slot("weekly", 11, 2, NOW) == datetime(2026, 11, 18, 11, 0)  # today, later: last week's
    assert utils.next_slot("weekly", 11, 2, NOW) == datetime(2026, 11, 25, 11, 0)
    assert utils.last_slot("off", 2, None, NOW) is None


def test_a_schedule_is_due_once_a_slot_after_it_was_set():
    set_at = datetime(2026, 11, 25, 9, 0)
    assert utils.schedule_due("daily", 2, None, NOW, set_at, None) is False  # today's slot was before it was set
    assert utils.schedule_due("daily", 2, None, datetime(2026, 11, 26, 2, 5), set_at, None) is True
    assert utils.schedule_due("daily", 2, None, datetime(2026, 11, 26, 2, 5), set_at, datetime(2026, 11, 26, 2, 1)) is False
    assert (
        utils.schedule_due("daily", 2, None, datetime(2026, 11, 29, 2, 5), set_at, datetime(2026, 11, 26, 2, 1)) is True
    )  # days missed: once


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "a\u200bb", "a\nb"])
def test_names_are_refused_when_empty_long_or_hiding_characters(name):
    with pytest.raises(ValueError):
        utils.check_name(name)
