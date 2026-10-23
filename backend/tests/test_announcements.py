"""SOCFortress announcements ("What's new"): the feed is validated, capped, cached and filtered.

No network: the feed is served by an ``httpx.MockTransport``.

Run with: cd backend && python -m pytest tests/test_announcements.py
"""

import asyncio
import inspect
import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.announcements.routes import announcements as announcements_routes  # noqa: E402
from app.announcements.services import announcements as service  # noqa: E402
from app.auth.models.users import RoleEnum  # noqa: E402

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def item(**overrides):
    base = {
        "id": "waf-launch",
        "category": "product",
        "title": "SOCFortress WAF is here",
        "summary": "Caddy + Coraza, managed from CoPilot.",
        "body_markdown": "**New**",
        "cta": {"label": "Learn more", "url": "https://github.com/socfortress/waf-platform-public"},
        "published_at": "2026-10-20T00:00:00Z",
    }
    base.update(overrides)
    return base


def feed(*items, version=1):
    return json.dumps({"version": version, "announcements": list(items)}).encode()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in (
        "ANNOUNCEMENTS_ENABLED",
        "ANNOUNCEMENTS_FEED_URL",
        "ANNOUNCEMENTS_HIDE_PROMOTIONS",
        "ANNOUNCEMENTS_CACHE_TTL_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    service.clear_cache()
    yield
    service.clear_cache()


def transport(body=b"", status=200, headers=None, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(request)
        return httpx.Response(status, content=body, headers=headers or {})

    return httpx.MockTransport(handler)


# --- parsing ---------------------------------------------------------------------------------


def test_a_valid_feed_parses():
    items = service.parse_feed(feed(item()))
    assert [i.id for i in items] == ["waf-launch"]
    assert items[0].audience == ["admin", "analyst", "responder"]


def test_one_bad_item_is_dropped_not_the_feed():
    items = service.parse_feed(feed(item(id="Bad Id"), item(id="ok")))
    assert [i.id for i in items] == ["ok"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"cta": {"label": "Go", "url": "http://example.com"}},
        {"cta": {"label": "Go", "url": "javascript:alert(1)"}},
        {"cta": {"label": "Go", "url": "https://user:pw@example.com/"}},
        {"cta": {"label": "Go", "url": "https://example.com/a b"}},
        {"image_url": "data:image/png;base64,AAAA"},
        {"image_url": "//example.com/x.png"},
        {"category": "spam"},
        {"title": ""},
        {"title": "x" * 121},
        {"audience": ["customer_user"]},
        {"audience": []},
        {"min_version": "not a version"},
        {"expires_at": "2026-10-19T00:00:00Z"},
        {"published_at": None},
    ],
)
def test_unsafe_or_malformed_items_are_dropped(overrides):
    assert service.parse_feed(feed(item(**overrides))) == []


def test_unknown_fields_are_ignored():
    assert len(service.parse_feed(feed(item(future_field={"x": 1})))) == 1


def test_a_duplicate_id_keeps_the_first():
    items = service.parse_feed(feed(item(title="first"), item(title="second")))
    assert [i.title for i in items] == ["first"]


def test_a_naive_time_is_utc():
    (parsed,) = service.parse_feed(feed(item(published_at="2026-10-20T00:00:00")))
    assert parsed.published_at == datetime(2026, 10, 20, tzinfo=timezone.utc)


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"announcements": {}}', feed(item(), version=2)])
def test_a_document_that_is_not_a_feed_is_refused(body):
    with pytest.raises(service.FeedError):
        service.parse_feed(body)


# --- fetching --------------------------------------------------------------------------------


def test_fetch_reads_the_feed():
    items = asyncio.run(service.fetch_feed("https://feed.test/feed.json", transport=transport(feed(item()))))
    assert [i.id for i in items] == ["waf-launch"]


def test_fetch_asks_for_an_uncompressed_body_and_names_copilot():
    calls = []
    asyncio.run(service.fetch_feed("https://feed.test/feed.json", transport=transport(feed(item()), calls=calls)))
    assert calls[0].headers["accept-encoding"] == "identity"
    assert calls[0].headers["user-agent"].startswith("SOCFortress-CoPilot/")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": 404},
        {"status": 500},
        {"headers": {"content-encoding": "gzip"}},
        {"body": b" " * (service.MAX_FEED_BYTES + 1)},
    ],
)
def test_fetch_refuses_what_is_not_a_usable_answer(kwargs):
    with pytest.raises(service.FeedError):
        asyncio.run(service.fetch_feed("https://feed.test/feed.json", transport=transport(**kwargs)))


def test_the_feed_is_cached(monkeypatch):
    calls = []
    t = transport(feed(item()), calls=calls)
    asyncio.run(service.get_feed_items(transport=t))
    asyncio.run(service.get_feed_items(transport=t))
    assert len(calls) == 1


def test_a_failed_fetch_is_an_empty_list_and_cached_briefly(monkeypatch):
    calls = []
    t = transport(status=503, calls=calls)
    assert asyncio.run(service.get_feed_items(transport=t)) == []
    assert asyncio.run(service.get_feed_items(transport=t)) == []
    assert len(calls) == 1
    stored_at, items, ok = service._cache[service.feed_url()]
    service._cache[service.feed_url()] = (stored_at - service.FAILURE_TTL_SECONDS - 1, items, ok)
    asyncio.run(service.get_feed_items(transport=t))
    assert len(calls) == 2


def test_an_unreachable_feed_is_an_empty_list():
    def handler(request):
        raise httpx.ConnectError("no route", request=request)

    assert asyncio.run(service.get_feed_items(transport=httpx.MockTransport(handler))) == []


def test_ttl_zero_disables_the_cache(monkeypatch):
    monkeypatch.setenv("ANNOUNCEMENTS_CACHE_TTL_SECONDS", "0")
    calls = []
    t = transport(feed(item()), calls=calls)
    asyncio.run(service.get_feed_items(transport=t))
    asyncio.run(service.get_feed_items(transport=t))
    assert len(calls) == 2


def test_the_feed_url_can_be_overridden(monkeypatch):
    assert service.feed_url() == service.DEFAULT_FEED_URL
    monkeypatch.setenv("ANNOUNCEMENTS_FEED_URL", "https://mirror.internal/feed.json")
    calls = []
    asyncio.run(service.get_feed_items(transport=transport(feed(item()), calls=calls)))
    assert str(calls[0].url) == "https://mirror.internal/feed.json"


# --- filtering -------------------------------------------------------------------------------


def visible(items, role=RoleEnum.analyst, version="0.1.99", **kwargs):
    parsed = service.parse_feed(feed(*items))
    return [a.id for a in service.visible_announcements(parsed, role, now=NOW, current_version=version, **kwargs)]


def test_scheduled_and_expired_items_are_hidden():
    items = [
        item(id="live"),
        item(id="scheduled", published_at="2026-10-24T00:00:00Z"),
        item(id="expired", expires_at="2026-10-22T00:00:00Z"),
        item(id="expiring", expires_at="2026-10-24T00:00:00Z"),
    ]
    assert sorted(visible(items)) == ["expiring", "live"]


def test_newest_first():
    items = [item(id="old", published_at="2026-01-01T00:00:00Z"), item(id="new", published_at="2026-10-01T00:00:00Z")]
    assert visible(items) == ["new", "old"]


def test_audience_by_role():
    items = [item(id="admins", audience=["admin"]), item(id="analysts", audience=["analyst"])]
    assert visible(items, role=RoleEnum.admin) == ["admins"]
    assert visible(items, role=RoleEnum.analyst) == ["analysts"]
    # A responder is an analyst who may also act: items for analysts reach them too.
    assert visible(items, role=RoleEnum.responder) == ["analysts"]
    assert visible(items, role=RoleEnum.customer_user) == []
    assert visible(items, role=RoleEnum.scheduler) == []


def test_version_range():
    items = [item(id="new-only", min_version="0.2.0"), item(id="old-only", max_version="0.1.50"), item(id="all")]
    assert visible(items, version="0.1.99") == ["all"]
    assert sorted(visible(items, version="0.2.1")) == ["all", "new-only"]


def test_promotions_can_be_hidden():
    items = [item(id="promo", category="promotion"), item(id="advisory", category="advisory")]
    assert sorted(visible(items)) == ["advisory", "promo"]
    assert visible(items, without_promotions=True) == ["advisory"]


def test_targeting_fields_are_not_sent():
    (out,) = service.visible_announcements(service.parse_feed(feed(item())), RoleEnum.admin, now=NOW)
    sent = out.model_dump()
    assert "audience" not in sent and "min_version" not in sent and "max_version" not in sent


# --- the route's answer ----------------------------------------------------------------------


def test_turned_off_makes_no_request(monkeypatch):
    monkeypatch.setenv("ANNOUNCEMENTS_ENABLED", "false")

    async def boom(*args, **kwargs):
        raise AssertionError("the feed must not be fetched")

    monkeypatch.setattr(service, "get_feed_items", boom)
    answer = asyncio.run(service.announcements_for(RoleEnum.admin))
    assert answer.enabled is False and answer.announcements == []


def test_the_answer_applies_hide_promotions(monkeypatch):
    monkeypatch.setenv("ANNOUNCEMENTS_HIDE_PROMOTIONS", "true")
    items = service.parse_feed(feed(item(id="promo", category="promotion"), item(id="product")))

    async def cached(*args, **kwargs):
        return items

    monkeypatch.setattr(service, "get_feed_items", cached)
    answer = asyncio.run(service.announcements_for(RoleEnum.analyst))
    assert answer.enabled is True
    assert [a.id for a in answer.announcements] == ["product"]


def test_the_route_admits_admins_and_analysts_only():
    (route,) = announcements_routes.announcements_router.routes
    (dependency,) = route.dependencies
    required = inspect.getclosurevars(dependency.dependency).nonlocals.get("required_scopes")
    assert route.methods == {"GET"}
    assert set(required) == {"admin", "analyst"}


def test_published_at_window_is_relative_to_now():
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    parsed = service.parse_feed(feed(item(id="future", published_at=future)))
    assert service.visible_announcements(parsed, RoleEnum.admin) == []
