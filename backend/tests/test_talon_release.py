"""The talon-analyst release check (``services/talon_release.py``, ``utils/ghcr_client.py``): the
newest plain X.Y.Z tag of ``ghcr.io/socfortress/talon-analyst-api``, compared with the version Talon
runs, cached 12 h (a failure 15 min), and no request at all when switched off.

GHCR is an ``httpx.MockTransport`` under the real client (``talon_release_support``). No network.
"""
import asyncio
import gzip
import ssl
import time
from unittest.mock import patch

import httpx
import pytest

from app.connectors.talon.services import talon_release
from app.connectors.talon.utils import ghcr_client
from tests.talon_release_support import TAGS_PATH
from tests.talon_release_support import TOKEN
from tests.talon_release_support import Registry
from tests.talon_release_support import ghcr


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv(talon_release.ENABLED_ENV, raising=False)
    talon_release.clear_cache()
    yield
    talon_release.clear_cache()


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def lookup(respond, calls=1):
    """``latest_release()`` ``calls`` times in one event loop, against a faked GHCR."""
    registry = Registry(respond)

    async def inner():
        with patch.object(ghcr_client, "_new_client", registry.new_client):
            return [await talon_release.latest_release() for _ in range(calls)]

    answers = asyncio.run(inner())
    return (answers[0] if calls == 1 else answers), registry


# ── parsing and comparing ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value, expected",
    [
        ("0.1.9", (0, 1, 9)),
        ("0.1.10", (0, 1, 10)),
        ("1.0.0", (1, 0, 0)),
        ("10.20.30", (10, 20, 30)),
        ("latest", None),
        ("sha-2d71450fe7c360cdcc3016e30a76703e0bab1fbb", None),
        ("v0.1.9", None),
        ("0.1", None),
        ("0.1.9.1", None),
        ("0.1.9-rc1", None),
        ("0.1.9+local", None),
        ("0.1.9.dev0", None),
        (" 0.1.9", None),
        ("0.1.9\n", None),
        ("０.１.９", None),  # full-width digits are not ASCII digits
        ("1234567890.0.0", None),  # past nine digits
        ("unknown", None),
        ("", None),
        (None, None),
        (19, None),
    ],
)
def test_parse_release(value, expected):
    assert talon_release.parse_release(value) == expected


def test_the_newest_release_is_the_highest_number_and_other_tags_are_ignored():
    tags = ["0.1.9", "latest", "sha-704778514fcded753cfbf24d07e04c0840511a69", "0.1.10", "0.1.11-rc1", "v0.2.0", "0.2", None, 3, "0.1.2"]
    assert talon_release.newest_release(tags) == "0.1.10"
    assert talon_release.newest_release(["0.9.9", "0.10.0", "0.2.0"]) == "0.10.0"
    assert talon_release.newest_release(["latest", "sha-abc"]) is None
    assert talon_release.newest_release([]) is None


@pytest.mark.parametrize(
    "latest, running, expected",
    [
        ("0.1.10", "0.1.9", True),
        ("0.2.0", "0.1.99", True),
        ("1.0.0", "0.9.9", True),
        ("0.1.9", "0.1.9", False),
        ("0.1.8", "0.1.9", False),
        (None, "0.1.9", False),
        ("0.1.9", None, False),
        ("0.1.9", "unknown", False),
        ("0.1.9", "0.1.8.dev3", False),
        ("latest", "0.1.8", False),
    ],
)
def test_is_newer(latest, running, expected):
    assert talon_release.is_newer(latest, running) is expected


# ── the switch ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value, enabled",
    [(None, True), ("", True), ("true", True), ("1", True), ("yes", True), ("On", True), ("TRUE", True)]
    + [(v, False) for v in ("false", "0", "no", "off", "False")],
)
def test_the_switch_is_on_unless_turned_off(monkeypatch, value, enabled):
    if value is not None:
        monkeypatch.setenv(talon_release.ENABLED_ENV, value)
    assert talon_release.release_check_enabled() is enabled


def test_switched_off_no_request_is_made(monkeypatch):
    monkeypatch.setenv(talon_release.ENABLED_ENV, "false")
    latest, registry = lookup(ghcr(), calls=3)
    assert latest == [None, None, None]
    assert registry.requests == []


# ── asking GHCR ───────────────────────────────────────────────────────────────


def test_the_newest_release_comes_from_ghcr_anonymously():
    latest, registry = lookup(ghcr(tags=["0.1.8", "latest", "0.1.9", "sha-abc", "0.1.10"]))
    assert latest == "0.1.10"
    assert registry.paths() == ["/token", TAGS_PATH]
    token_request, tags_request = registry.requests
    for request in registry.requests:
        assert (request.method, request.url.scheme, request.url.host, request.url.port) == ("GET", "https", "ghcr.io", None)
        assert request.content == b""
        # Nothing about this CoPilot: no cookie, no key, no CoPilot version.
        assert set(request.headers.keys()) <= {"host", "accept", "accept-encoding", "connection", "user-agent", "authorization"}
        assert "copilot" not in request.headers.get("user-agent", "").lower()
        assert request.headers["accept-encoding"] == "identity"
    assert token_request.url.params["scope"] == "repository:socfortress/talon-analyst-api:pull"
    assert "authorization" not in token_request.headers
    assert tags_request.headers["authorization"] == f"Bearer {TOKEN}"
    assert tags_request.url.params["n"] == str(ghcr_client.PAGE_SIZE)


def test_every_page_of_tags_is_read():
    # GHCR lists in push order: the newest release is on the last page.
    tags = ["0.1.0", "latest", "0.1.1", "sha-a", "0.1.2", "sha-b", "0.1.9", "0.1.10"]
    latest, registry = lookup(ghcr(tags=tags, page_size=3))
    assert latest == "0.1.10"
    assert registry.paths() == ["/token"] + [TAGS_PATH] * 3
    assert [r.url.params.get("last") for r in registry.requests[1:]] == [None, "0.1.1", "sha-b"]
    assert all(r.headers["authorization"] == f"Bearer {TOKEN}" for r in registry.requests[1:])


def test_an_image_with_no_tags_has_no_release():
    respond = ghcr(overrides={TAGS_PATH: httpx.Response(200, json={"name": "socfortress/talon-analyst-api", "tags": None})})
    assert lookup(respond)[0] is None


@pytest.mark.parametrize(
    "link",
    [
        '<https://elsewhere.invalid/v2/socfortress/talon-analyst-api/tags/list?last=x&n=1000>; rel="next"',
        '<//elsewhere.invalid/v2/socfortress/talon-analyst-api/tags/list?last=x>; rel="next"',
        '<http://ghcr.io/v2/socfortress/talon-analyst-api/tags/list?last=x>; rel="next"',
        '<https://ghcr.io:8443/v2/socfortress/talon-analyst-api/tags/list?last=x>; rel="next"',
        '<https://someone@ghcr.io/v2/socfortress/talon-analyst-api/tags/list?last=x>; rel="next"',
        '</v2/socfortress/another-image/tags/list?last=x>; rel="next"',
        '</token?scope=x>; rel="next"',
    ],
)
def test_a_next_page_off_ghcrs_tags_path_is_not_followed(link):
    with pytest.raises(ghcr_client.GhcrError):
        ghcr_client.next_page(link)
    respond = ghcr(overrides={TAGS_PATH: httpx.Response(200, json={"tags": ["0.1.99"]}, headers={"Link": link})})
    latest, registry = lookup(respond)
    assert latest is None
    assert registry.paths() == ["/token", TAGS_PATH]


def test_next_page_links():
    assert ghcr_client.next_page(None) is None
    assert ghcr_client.next_page('<https://ghcr.io/somewhere>; rel="prev"') is None
    relative = f'<{TAGS_PATH}?last=sha-abc&n=1000>; rel="next"'
    assert ghcr_client.next_page(relative) == f"https://ghcr.io{TAGS_PATH}?last=sha-abc&n=1000"
    absolute = f"<https://ghcr.io{TAGS_PATH}?last=0.1.3&n=1000>; rel=next"
    assert ghcr_client.next_page(absolute) == f"https://ghcr.io{TAGS_PATH}?last=0.1.3&n=1000"


def test_a_next_page_that_repeats_is_not_followed_forever():
    link = f'<{TAGS_PATH}?last=0.1.0&n=1000>; rel="next"'
    respond = ghcr(overrides={TAGS_PATH: lambda r: httpx.Response(200, json={"tags": ["0.1.0"]}, headers={"Link": link})})
    latest, registry = lookup(respond)
    assert latest is None
    assert len(registry.requests) == 3  # the token, the first page, the linked page; not its repeat


def test_more_pages_than_the_cap_is_a_failure(monkeypatch):
    monkeypatch.setattr(ghcr_client, "MAX_PAGES", 2)
    latest, registry = lookup(ghcr(tags=["0.1.0", "0.1.1", "0.1.2", "0.1.3"], page_size=1))
    assert latest is None
    assert registry.paths() == ["/token", TAGS_PATH, TAGS_PATH]


def _tags_answer(**kwargs):
    return {TAGS_PATH: httpx.Response(**kwargs)}


@pytest.mark.parametrize(
    "overrides",
    [
        {"/token": httpx.Response(401, json={"errors": []})},
        {"/token": httpx.Response(200, content=b"<html>")},
        {"/token": httpx.Response(200, json={"access_token": TOKEN})},
        {"/token": httpx.Response(200, json={"token": "abc\r\nX-Injected: 1"})},
        {"/token": httpx.Response(200, json={"token": "x" * 9000})},
        {"/token": httpx.Response(200, json=["token"])},
        _tags_answer(status_code=500, json={"errors": []}),
        _tags_answer(status_code=404, json={"errors": []}),
        _tags_answer(status_code=200, content=b"not json"),
        _tags_answer(status_code=200, json={"tags": "0.1.9"}),
        _tags_answer(status_code=200, json={"name": "socfortress/talon-analyst-api"}),
        _tags_answer(status_code=200, json=["0.1.9"]),
        _tags_answer(status_code=200, content=gzip.compress(b'{"tags": ["0.1.9"]}'), headers={"Content-Encoding": "gzip"}),
        _tags_answer(status_code=302, headers={"Location": "https://elsewhere.invalid/"}),
        {TAGS_PATH: httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known: ghcr.io")},
        {"/token": httpx.ReadTimeout("timed out")},
        {"/token": ssl.SSLCertVerificationError("certificate verify failed")},
    ],
)
def test_any_failure_is_none_never_an_exception(overrides):
    latest, registry = lookup(ghcr(overrides=overrides))
    assert latest is None
    assert all(r.url.host == "ghcr.io" for r in registry.requests)


def test_an_answer_over_the_cap_is_not_read(monkeypatch):
    monkeypatch.setattr(ghcr_client, "MAX_BODY_BYTES", 64)
    respond = ghcr(overrides=_tags_answer(status_code=200, json={"tags": ["0.1.9"] * 50}))
    assert lookup(respond)[0] is None


def test_a_failure_says_why_in_one_info_line_without_a_traceback():
    from loguru import logger

    lines = []
    sink = logger.add(lambda m: lines.append(m), level="DEBUG", format="{level} {message}")
    try:
        lookup(ghcr(overrides={TAGS_PATH: httpx.ConnectError("[Errno 61] Connection refused to ghcr.io:443")}))
    finally:
        logger.remove(sink)
    failures = [line for line in lines if line.startswith("INFO")]
    assert failures == ["INFO Talon release check: GHCR could not be reached (ConnectError)\n"]
    assert not any("Traceback" in line or "ghcr.io:443" in line for line in lines)


def test_a_slow_ghcr_is_cut_at_the_deadline(monkeypatch):
    monkeypatch.setattr(ghcr_client, "TIMEOUT_SECONDS", 0.2)

    async def slow(request):
        await asyncio.sleep(5)
        return httpx.Response(200, json={"token": TOKEN})

    started = time.perf_counter()
    latest, _ = lookup(ghcr(overrides={"/token": slow}))
    assert latest is None
    assert time.perf_counter() - started < 2


def test_the_client_settings():
    async def scenario():
        async with ghcr_client._new_client() as client:
            context = client._transport._pool._ssl_context
            return client.follow_redirects, context.verify_mode, context.check_hostname, client.timeout

    follow, verify_mode, check_hostname, timeout = asyncio.run(scenario())
    # GHCR is the public internet: TLS verified, no redirect anywhere else.
    assert follow is False
    assert verify_mode == ssl.CERT_REQUIRED and check_hostname is True
    assert timeout.read == ghcr_client.TIMEOUT_SECONDS == 3.0
    assert ghcr_client.TOKEN_URL.startswith("https://ghcr.io/token?")


# ── the cache ─────────────────────────────────────────────────────────────────


def _cached_run(respond, steps):
    """Run ``steps`` (advance seconds, then one lookup) in one loop; the request count after each."""
    clock = Clock()
    registry = Registry(respond)

    async def inner():
        counts = []
        with patch.object(ghcr_client, "_new_client", registry.new_client), patch.object(talon_release, "_clock", clock):
            for advance in steps:
                clock.now += advance
                answer = await talon_release.latest_release()
                counts.append((answer, len(registry.requests)))
        return counts

    return asyncio.run(inner())


def test_an_answer_is_kept_12_hours():
    twelve_hours = 12 * 60 * 60
    counts = _cached_run(ghcr(), [0, 60, twelve_hours - 61, 1])
    assert counts == [("0.1.3", 2), ("0.1.3", 2), ("0.1.3", 2), ("0.1.3", 4)]


def test_a_failure_is_kept_15_minutes():
    counts = _cached_run(ghcr(overrides={"/token": httpx.Response(503)}), [0, 30, 15 * 60 - 31, 1])
    assert counts == [(None, 1), (None, 1), (None, 1), (None, 2)]


def test_no_release_among_the_tags_is_kept_as_a_failure():
    counts = _cached_run(ghcr(tags=["latest", "sha-abc"]), [0, 15 * 60 - 1, 1])
    assert counts == [(None, 2), (None, 2), (None, 4)]


def test_concurrent_lookups_share_one():
    registry = Registry(ghcr())

    async def inner():
        with patch.object(ghcr_client, "_new_client", registry.new_client):
            return await asyncio.gather(*[talon_release.latest_release() for _ in range(5)])

    assert asyncio.run(inner()) == ["0.1.3"] * 5
    assert len(registry.requests) == 2
